# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import shutil
import zipfile
import tempfile
import subprocess
import threading
import queue
import urllib.request
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "Android 高速雙向傳檔"
APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "AndroidFastPull")
TOOLS_DIR = os.path.join(APP_DIR, "platform-tools")
ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
PHONE_HOME = "/sdcard"

def no_console_flag():
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

def quote_sh(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"

def fmt_bytes(n):
    n = float(max(0, n))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024

def fmt_time(sec):
    if sec is None or sec < 0 or sec == float("inf"):
        return "--:--"
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x760")
        self.minsize(940, 640)

        self.q = queue.Queue()
        self.adb = self.find_adb()
        self.device_serial = None
        self.current_path = PHONE_HOME
        self.phone_items = {}
        self.local_sources = []
        self.transfer_running = False

        self.build_ui()
        self.after(100, self.process_queue)
        self.after(300, self.first_start)

    # ---------- UI ----------
    def build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="手機：").pack(side="left")
        self.device_combo = ttk.Combobox(top, state="readonly", width=42)
        self.device_combo.pack(side="left", padx=(6, 8))
        self.device_combo.bind("<<ComboboxSelected>>", lambda e: self.on_device_selected())
        ttk.Button(top, text="重新偵測", command=self.refresh_devices).pack(side="left")

        modebox = ttk.LabelFrame(self, text="傳輸方向", padding=(10, 6))
        modebox.pack(fill="x", padx=10, pady=(0, 8))
        self.mode = tk.StringVar(value="pull")
        ttk.Radiobutton(modebox, text="手機 → 電腦", value="pull", variable=self.mode, command=self.mode_changed).pack(side="left")
        ttk.Radiobutton(modebox, text="電腦 → 手機", value="push", variable=self.mode, command=self.mode_changed).pack(side="left", padx=(20, 0))
        self.mode_hint = ttk.Label(modebox, text="在下方手機清單選取要複製到電腦的檔案。")
        self.mode_hint.pack(side="left", padx=(24, 0))

        nav = ttk.Frame(self, padding=(10, 0, 10, 8))
        nav.pack(fill="x")
        ttk.Button(nav, text="↑ 上一層", command=self.go_up).pack(side="left")
        ttk.Button(nav, text="⌂ 手機內部儲存", command=lambda: self.load_path(PHONE_HOME)).pack(side="left", padx=6)
        ttk.Button(nav, text="↻ 重新整理", command=lambda: self.load_path(self.current_path)).pack(side="left")
        self.path_var = tk.StringVar(value=PHONE_HOME)
        self.path_entry = ttk.Entry(nav, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.path_entry.bind("<Return>", lambda e: self.load_path(self.path_var.get().strip()))

        main = ttk.Panedwindow(self, orient="vertical")
        main.pack(fill="both", expand=True, padx=10)

        phone_frame = ttk.LabelFrame(main, text="手機檔案")
        local_frame = ttk.LabelFrame(main, text="電腦來源（僅「電腦 → 手機」使用）")
        main.add(phone_frame, weight=4)
        main.add(local_frame, weight=1)

        self.tree = ttk.Treeview(
            phone_frame, columns=("kind", "name", "size"),
            show="headings", selectmode="extended"
        )
        self.tree.heading("kind", text="類型")
        self.tree.heading("name", text="名稱")
        self.tree.heading("size", text="大小")
        self.tree.column("kind", width=90, anchor="center", stretch=False)
        self.tree.column("name", width=760, anchor="w")
        self.tree.column("size", width=150, anchor="e", stretch=False)
        y = ttk.Scrollbar(phone_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        y.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.double_click)
        self.tree.bind("<<TreeviewSelect>>", self.selection_changed)

        local_left = ttk.Frame(local_frame, padding=6)
        local_left.pack(side="left", fill="y")
        ttk.Button(local_left, text="＋ 選擇檔案", command=self.add_local_files).pack(fill="x")
        ttk.Button(local_left, text="＋ 選擇資料夾", command=self.add_local_folder).pack(fill="x", pady=5)
        ttk.Button(local_left, text="移除選取", command=self.remove_local_selected).pack(fill="x")
        ttk.Button(local_left, text="清空", command=self.clear_local).pack(fill="x", pady=(5,0))

        self.local_list = tk.Listbox(local_frame, selectmode="extended", height=6)
        self.local_list.pack(side="left", fill="both", expand=True, padx=(0,6), pady=6)

        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")

        destrow = ttk.Frame(bottom)
        destrow.pack(fill="x")
        self.dest_label = ttk.Label(destrow, text="電腦儲存位置：")
        self.dest_label.pack(side="left")
        default_dest = os.path.join(os.path.expanduser("~"), "Desktop", "PhonePull")
        self.dest_var = tk.StringVar(value=default_dest)
        self.dest_entry = ttk.Entry(destrow, textvariable=self.dest_var)
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.dest_choose_btn = ttk.Button(destrow, text="選擇資料夾", command=self.choose_dest)
        self.dest_choose_btn.pack(side="left")
        self.open_dest_btn = ttk.Button(destrow, text="開啟資料夾", command=self.open_dest)
        self.open_dest_btn.pack(side="left", padx=(6,0))

        action = ttk.Frame(bottom)
        action.pack(fill="x", pady=(10, 0))
        self.transfer_btn = ttk.Button(action, text="開始傳輸", command=self.start_transfer)
        self.transfer_btn.pack(side="left")

        self.selected_var = tk.StringVar(value="尚未選取")
        ttk.Label(action, textvariable=self.selected_var).pack(side="left", padx=(10, 10))

        self.progress = ttk.Progressbar(action, maximum=100, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True)

        self.percent_var = tk.StringVar(value="0%")
        ttk.Label(action, textvariable=self.percent_var, width=7, anchor="e").pack(side="right", padx=(8, 0))

        stats = ttk.Frame(bottom)
        stats.pack(fill="x", pady=(6,0))
        self.current_var = tk.StringVar(value="目前：等待中")
        self.speed_var = tk.StringVar(value="速度：--")
        self.elapsed_var = tk.StringVar(value="已用：00:00")
        self.eta_var = tk.StringVar(value="剩餘：--:--")
        ttk.Label(stats, textvariable=self.current_var).pack(side="left")
        ttk.Label(stats, textvariable=self.speed_var).pack(side="right", padx=(12,0))
        ttk.Label(stats, textvariable=self.eta_var).pack(side="right", padx=(12,0))
        ttk.Label(stats, textvariable=self.elapsed_var).pack(side="right", padx=(12,0))

        self.status_var = tk.StringVar(value="正在啟動...")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=(8, 4)).pack(fill="x", side="bottom")

        self.mode_changed()

    def mode_changed(self):
        if self.mode.get() == "pull":
            self.mode_hint.config(text="在手機清單選取檔案/資料夾，複製到電腦。手機原檔保留。")
            self.dest_label.config(text="電腦儲存位置：")
            self.dest_entry.config(state="normal")
            self.dest_choose_btn.config(state="normal")
            self.open_dest_btn.config(state="normal")
            self.transfer_btn.config(text="開始：手機 → 電腦")
        else:
            self.mode_hint.config(text="先選電腦檔案/資料夾；目前手機路徑就是傳入目的地。")
            self.dest_label.config(text="手機目的地：")
            self.dest_var.set(self.current_path)
            self.dest_entry.config(state="disabled")
            self.dest_choose_btn.config(state="disabled")
            self.open_dest_btn.config(state="disabled")
            self.transfer_btn.config(text="開始：電腦 → 手機")
        self.selection_changed()

    # ---------- ADB setup ----------
    def find_adb(self):
        candidates = [
            shutil.which("adb"),
            os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "adb.exe"),
            os.path.join(TOOLS_DIR, "adb.exe"),
        ]
        for p in candidates:
            if p and os.path.exists(p):
                return os.path.abspath(p)
        return None

    def first_start(self):
        if self.adb:
            self.refresh_devices()
            return
        if messagebox.askyesno(APP_TITLE, "第一次使用需要 Google 官方 Android Platform Tools（ADB）。\n\n按「是」會自動下載並設定。"):
            self.install_adb()
        else:
            self.status_var.set("ADB 尚未就緒。")

    def install_adb(self):
        self.status_var.set("正在下載 Google 官方 ADB...")
        self.progress.config(mode="indeterminate")
        self.progress.start(10)

        def work():
            try:
                os.makedirs(APP_DIR, exist_ok=True)
                with tempfile.TemporaryDirectory() as td:
                    zpath = os.path.join(td, "platform-tools.zip")
                    urllib.request.urlretrieve(ADB_URL, zpath)
                    with zipfile.ZipFile(zpath, "r") as zf:
                        zf.extractall(APP_DIR)
                adb = os.path.join(TOOLS_DIR, "adb.exe")
                if not os.path.exists(adb):
                    raise RuntimeError("下載後找不到 adb.exe")
                self.q.put(("adb_installed", adb))
            except Exception as e:
                self.q.put(("error", f"ADB 自動安裝失敗：{e}"))
        threading.Thread(target=work, daemon=True).start()

    def adb_base(self):
        if not self.adb:
            raise RuntimeError("ADB 尚未就緒")
        cmd = [self.adb]
        if self.device_serial:
            cmd += ["-s", self.device_serial]
        return cmd

    def adb_run(self, args, timeout=90):
        return subprocess.run(
            self.adb_base() + args, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=no_console_flag()
        )

    def refresh_devices(self):
        if not self.adb or self.transfer_running:
            return
        self.status_var.set("正在偵測手機...")
        def work():
            try:
                subprocess.run([self.adb, "start-server"], capture_output=True, timeout=15, creationflags=no_console_flag())
                cp = subprocess.run([self.adb, "devices"], capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", timeout=15, creationflags=no_console_flag())
                good, unauth = [], []
                for line in cp.stdout.splitlines()[1:]:
                    p = line.strip().split()
                    if len(p) >= 2:
                        if p[1] == "device": good.append(p[0])
                        elif p[1] == "unauthorized": unauth.append(p[0])
                self.q.put(("devices", good, unauth))
            except Exception as e:
                self.q.put(("error", f"偵測手機失敗：{e}"))
        threading.Thread(target=work, daemon=True).start()

    # ---------- Phone browser ----------
    def on_device_selected(self):
        self.device_serial = self.device_combo.get().strip() or None
        if self.device_serial:
            self.load_path(PHONE_HOME)

    def load_path(self, path):
        if not self.device_serial or self.transfer_running:
            return
        path = (path or PHONE_HOME).strip()
        while path.startswith("/sdcard/sdcard/"):
            path = path[len("/sdcard"):]
        if path == "/sdcard/sdcard":
            path = "/sdcard"
        self.status_var.set(f"正在讀取：{path}")

        def work():
            try:
                shell_cmd = (
                    f"cd {quote_sh(path)} || exit 20; "
                    "for f in * .[^.]*; do "
                    "[ -e \"$f\" ] || continue; "
                    "if [ -d \"$f\" ]; then printf 'D\\t0\\t%s\\n' \"$f\"; "
                    "else s=$(stat -c %s \"$f\" 2>/dev/null); "
                    "printf 'F\\t%s\\t%s\\n' \"${s:-0}\" \"$f\"; fi; done"
                )
                cp = self.adb_run(["shell", shell_cmd], timeout=90)
                if cp.returncode != 0:
                    raise RuntimeError((cp.stderr or cp.stdout or "").strip() or f"無法進入 {path}")
                entries = []
                for line in cp.stdout.splitlines():
                    parts = line.split("\t", 2)
                    if len(parts) != 3: continue
                    typ, size, name = parts
                    name = name.strip("\r")
                    if not name or name in (".",".."): continue
                    try: size = int(size)
                    except: size = 0
                    entries.append((typ, size, name))
                entries.sort(key=lambda x: (x[0] != "D", x[2].lower()))
                self.q.put(("folder", path, entries))
            except Exception as e:
                self.q.put(("error", f"讀取手機資料夾失敗：{e}"))
        threading.Thread(target=work, daemon=True).start()

    def go_up(self):
        p = self.current_path.rstrip("/")
        if p in ("", "/", "/sdcard"):
            self.load_path("/sdcard")
            return
        parent = os.path.dirname(p) or "/sdcard"
        if not parent.startswith("/sdcard"):
            parent = "/sdcard"
        self.load_path(parent)

    @staticmethod
    def phone_join(base, name):
        return (base.rstrip("/") + "/" + name) if base != "/" else "/" + name

    def double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        info = self.phone_items.get(iid)
        if info and info["type"] == "D":
            self.load_path(self.phone_join(self.current_path, info["name"]))

    def selection_changed(self, _event=None):
        if self.mode.get() == "pull":
            n = len(self.tree.selection())
            if n == 0: self.selected_var.set("尚未選取")
            elif n == 1:
                info = self.phone_items.get(self.tree.selection()[0], {})
                self.selected_var.set(f"已選取：{info.get('name','')}")
            else: self.selected_var.set(f"已選取 {n} 個項目")
        else:
            n = len(self.local_sources)
            self.selected_var.set("尚未選取" if n == 0 else f"電腦來源：{n} 個項目")

    # ---------- Local selection ----------
    def add_local_files(self):
        paths = filedialog.askopenfilenames(title="選擇要傳入手機的檔案")
        for p in paths:
            if p not in self.local_sources:
                self.local_sources.append(p)
                self.local_list.insert("end", p)
        self.selection_changed()

    def add_local_folder(self):
        p = filedialog.askdirectory(title="選擇要傳入手機的資料夾")
        if p and p not in self.local_sources:
            self.local_sources.append(p)
            self.local_list.insert("end", p)
        self.selection_changed()

    def remove_local_selected(self):
        inds = list(self.local_list.curselection())
        for i in reversed(inds):
            del self.local_sources[i]
            self.local_list.delete(i)
        self.selection_changed()

    def clear_local(self):
        self.local_sources.clear()
        self.local_list.delete(0, "end")
        self.selection_changed()

    # ---------- Dest ----------
    def choose_dest(self):
        p = filedialog.askdirectory(initialdir=self.dest_var.get() or os.path.expanduser("~"))
        if p: self.dest_var.set(p)

    def open_dest(self):
        p = self.dest_var.get().strip()
        if not p: return
        os.makedirs(p, exist_ok=True)
        if os.name == "nt":
            os.startfile(p)

    # ---------- Size helpers ----------
    def local_size(self, path):
        if os.path.isfile(path):
            try: return os.path.getsize(path)
            except: return 0
        total = 0
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                try: total += os.path.getsize(fp)
                except: pass
        return total

    def remote_size(self, path, timeout=120):
        # du -sb is available on current Android/toybox builds; fallback to stat for files.
        # timeout is shorter during live progress polling so a status probe can never stall the transfer UI.
        cmd = f"if [ -d {quote_sh(path)} ]; then du -sb {quote_sh(path)} 2>/dev/null | cut -f1; else stat -c %s {quote_sh(path)} 2>/dev/null; fi"
        cp = self.adb_run(["shell", cmd], timeout=timeout)
        m = re.search(r"(\d+)", cp.stdout or "")
        return int(m.group(1)) if m else 0

    # ---------- Transfer ----------
    def start_transfer(self):
        if self.transfer_running:
            return
        if not self.device_serial:
            messagebox.showwarning(APP_TITLE, "目前沒有已授權的手機。")
            return

        mode = self.mode.get()
        if mode == "pull":
            selected = self.tree.selection()
            if not selected:
                messagebox.showinfo(APP_TITLE, "請先選取手機裡要複製到電腦的項目。")
                return
            dest = self.dest_var.get().strip()
            if not dest:
                messagebox.showwarning(APP_TITLE, "請先選擇電腦儲存位置。")
                return
            os.makedirs(dest, exist_ok=True)
            jobs = []
            for iid in selected:
                info = self.phone_items.get(iid)
                if info:
                    jobs.append((self.phone_join(self.current_path, info["name"]), dest, info["name"]))
        else:
            if not self.local_sources:
                messagebox.showinfo(APP_TITLE, "請先選擇要傳入手機的電腦檔案或資料夾。")
                return
            dest = self.current_path
            jobs = [(p, dest, os.path.basename(p.rstrip("\\/"))) for p in self.local_sources]

        self.transfer_running = True
        self.transfer_btn.config(state="disabled")
        self.progress["value"] = 0
        self.percent_var.set("0%")
        self.current_var.set("目前：準備中")
        self.speed_var.set("速度：--")
        self.elapsed_var.set("已用：00:00")
        self.eta_var.set("剩餘：--:--")

        def work():
            errors = []
            sizes = []
            try:
                self.q.put(("status", "正在計算檔案總大小..."))
                for src, _, _ in jobs:
                    sizes.append(self.remote_size(src) if mode == "pull" else self.local_size(src))
            except Exception:
                sizes = [0] * len(jobs)

            total_bytes = sum(sizes)
            completed_before = 0
            start_all = time.time()
            total_jobs = len(jobs)

            for idx, (src, dest, name) in enumerate(jobs):
                item_size = sizes[idx] if idx < len(sizes) else 0
                self.q.put(("current", name, idx + 1, total_jobs))
                cmd = self.adb_base() + (["pull", "-p", "-a", src, dest] if mode == "pull"
                                         else ["push", "-p", src, dest])

                # Destination-size polling is the reliable fallback when this ADB build does not
                # emit -p percentages through a redirected pipe. Pull can be sampled locally with
                # virtually no overhead; push samples the phone less often to preserve throughput.
                target_path = (os.path.join(dest, name) if mode == "pull"
                               else self.phone_join(dest, name))
                try:
                    if mode == "pull":
                        initial_target_size = self.local_size(target_path) if os.path.exists(target_path) else 0
                    else:
                        initial_target_size = self.remote_size(target_path, timeout=5)
                except Exception:
                    initial_target_size = 0

                target_has_changed = (initial_target_size == 0)
                observed_item_bytes = 0.0

                try:
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        bufsize=0, creationflags=no_console_flag()
                    )

                    # Drain ADB output on its own thread. The old implementation called
                    # stdout.read(1) in the transfer loop, so if ADB did not print progress the
                    # entire progress loop blocked. Here output parsing is only an optional signal.
                    adb_state = {"pct": 0, "tail": ""}
                    adb_lock = threading.Lock()

                    def drain_adb_output():
                        text_buf = ""
                        try:
                            while True:
                                chunk = proc.stdout.read(1024)
                                if not chunk:
                                    break
                                try:
                                    text = chunk.decode("utf-8", errors="replace")
                                except Exception:
                                    text = ""
                                if not text:
                                    continue
                                text_buf = (text_buf + text)[-1000:]
                                matches = re.findall(r"(\d{1,3})%", text_buf)
                                with adb_lock:
                                    adb_state["tail"] = text_buf[-800:]
                                    if matches:
                                        adb_state["pct"] = max(0, min(100, int(matches[-1])))
                        except Exception:
                            pass

                    reader = threading.Thread(target=drain_adb_output, daemon=True)
                    reader.start()

                    last_done = float(completed_before)
                    last_speed_time = start_all
                    display_speed = 0.0
                    next_size_probe = 0.0
                    probe_interval = 0.20 if mode == "pull" else 0.80

                    while proc.poll() is None:
                        now = time.time()
                        elapsed = max(0.001, now - start_all)

                        with adb_lock:
                            adb_pct = adb_state["pct"]

                        # Prefer ADB's own percentage when available. Otherwise measure the
                        # destination's real size. This makes the UI move on ADB versions that
                        # stay silent until the copy finishes.
                        if item_size > 0 and adb_pct > 0:
                            observed_item_bytes = max(observed_item_bytes, item_size * adb_pct / 100.0)
                        elif now >= next_size_probe:
                            next_size_probe = now + probe_interval
                            try:
                                current_target_size = (self.local_size(target_path) if mode == "pull"
                                                       else self.remote_size(target_path, timeout=5))
                                # If a same-name destination already existed, do not report it as
                                # already copied. Once its size changes we know ADB has started
                                # replacing/writing it and the live size becomes meaningful.
                                if not target_has_changed and current_target_size != initial_target_size:
                                    target_has_changed = True
                                if target_has_changed:
                                    observed_item_bytes = max(observed_item_bytes, float(current_target_size))
                            except Exception:
                                pass

                        if item_size > 0:
                            item_done = min(float(item_size), max(0.0, observed_item_bytes))
                            done = min(float(total_bytes), completed_before + item_done) if total_bytes > 0 else completed_before + item_done
                            overall_pct = (done / total_bytes * 100.0) if total_bytes > 0 else 0.0
                        else:
                            # Unknown size: retain ADB percentage/count based progress if available.
                            p = float(adb_pct) if adb_pct > 0 else 0.0
                            done = float(completed_before)
                            overall_pct = ((idx + p / 100.0) / total_jobs * 100.0) if total_jobs else 0.0

                        # Calculate a smoothed live speed from observed byte movement instead of
                        # only showing a final average. Do not drop it to zero between phone probes.
                        dt = now - last_speed_time
                        if dt >= 0.18:
                            delta = done - last_done
                            if delta > 0:
                                inst_speed = delta / dt
                                display_speed = inst_speed if display_speed <= 0 else (display_speed * 0.65 + inst_speed * 0.35)
                            last_done = done
                            last_speed_time = now

                        remaining = max(0.0, total_bytes - done) if total_bytes > 0 else 0.0
                        eta = remaining / display_speed if display_speed > 0 and total_bytes > 0 else None
                        self.q.put(("progress", overall_pct, elapsed, display_speed, eta))
                        time.sleep(0.20)

                    rc = proc.wait()
                    reader.join(timeout=0.5)
                    if rc != 0:
                        with adb_lock:
                            tail = adb_state.get("tail", "").strip()
                        errors.append(f"{name}: {tail[-300:] if tail else 'ADB 傳輸失敗'}")
                    else:
                        completed_before += item_size
                        elapsed = max(0.001, time.time() - start_all)
                        avg_so_far = completed_before / elapsed if completed_before else 0
                        overall_pct = (completed_before / total_bytes * 100.0) if total_bytes > 0 else ((idx + 1) / total_jobs * 100.0)
                        eta = ((total_bytes - completed_before) / avg_so_far) if avg_so_far > 0 and total_bytes > completed_before else 0
                        self.q.put(("progress", overall_pct, elapsed, avg_so_far, eta))
                except Exception as e:
                    errors.append(f"{name}: {e}")

            elapsed_total = time.time() - start_all
            transferred = completed_before
            avg_speed = transferred / elapsed_total if elapsed_total > 0 else 0
            self.q.put(("done", errors, elapsed_total, transferred, avg_speed, mode, dest))

        threading.Thread(target=work, daemon=True).start()

    # ---------- Queue ----------
    def process_queue(self):
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]

                if kind == "adb_installed":
                    self.progress.stop()
                    self.progress.config(mode="determinate")
                    self.progress["value"] = 0
                    self.adb = msg[1]
                    self.refresh_devices()

                elif kind == "devices":
                    good, unauth = msg[1], msg[2]
                    self.device_combo["values"] = good
                    if good:
                        if self.device_combo.get() not in good:
                            self.device_combo.current(0)
                        self.device_serial = self.device_combo.get()
                        self.status_var.set(f"已連線：{self.device_serial}")
                        self.load_path(PHONE_HOME)
                    elif unauth:
                        self.device_serial = None
                        self.status_var.set("手機已偵測，但尚未授權 USB 偵錯。")
                        messagebox.showinfo(APP_TITLE, "請解鎖手機並按「允許 USB 偵錯」，再按重新偵測。")
                    else:
                        self.device_serial = None
                        self.status_var.set("沒有偵測到手機。")

                elif kind == "folder":
                    path, entries = msg[1], msg[2]
                    self.current_path = path
                    self.path_var.set(path)
                    if self.mode.get() == "push":
                        self.dest_var.set(path)
                    for iid in self.tree.get_children():
                        self.tree.delete(iid)
                    self.phone_items.clear()
                    for i, (typ, size, name) in enumerate(entries):
                        iid = f"i{i}"
                        self.phone_items[iid] = {"type": typ, "size": size, "name": name}
                        self.tree.insert("", "end", iid=iid,
                                         values=("資料夾" if typ == "D" else "檔案", name,
                                                 "" if typ == "D" else fmt_bytes(size)))
                    self.selection_changed()
                    self.status_var.set(f"{path} — {len(entries)} 個項目")

                elif kind == "status":
                    self.status_var.set(msg[1])

                elif kind == "current":
                    if len(msg) >= 4:
                        self.current_var.set(f"目前：{msg[1]}  ({msg[2]}/{msg[3]})")
                    else:
                        self.current_var.set(f"目前：{msg[1]}")
                    self.status_var.set("正在高速傳輸...")

                elif kind == "progress":
                    pct, elapsed, speed, eta = msg[1], msg[2], msg[3], msg[4]
                    pct = max(0, min(100, pct))
                    self.progress["value"] = pct
                    self.percent_var.set(f"{pct:.1f}%")
                    self.elapsed_var.set(f"已用：{fmt_time(elapsed)}")
                    self.eta_var.set(f"剩餘：{fmt_time(eta)}")
                    self.speed_var.set(f"速度：{fmt_bytes(speed)}/s")

                elif kind == "done":
                    errors, elapsed, transferred, avg_speed, mode, dest = msg[1:]
                    self.transfer_running = False
                    self.transfer_btn.config(state="normal")
                    if not errors:
                        self.progress["value"] = 100
                        self.percent_var.set("100%")
                    self.elapsed_var.set(f"已用：{fmt_time(elapsed)}")
                    self.eta_var.set("剩餘：00:00")
                    self.speed_var.set(f"平均：{fmt_bytes(avg_speed)}/s")
                    self.current_var.set("目前：完成" if not errors else "目前：部分失敗")
                    direction = "手機 → 電腦" if mode == "pull" else "電腦 → 手機"
                    result = (
                        f"傳輸方向：{direction}\n"
                        f"完成時間：{fmt_time(elapsed)}\n"
                        f"成功傳輸：約 {fmt_bytes(transferred)}\n"
                        f"平均速度：約 {fmt_bytes(avg_speed)}/s"
                    )
                    if errors:
                        result += "\n\n失敗項目：\n" + "\n".join(errors[:10])
                        messagebox.showwarning(APP_TITLE, result)
                    else:
                        messagebox.showinfo(APP_TITLE, result)
                        if mode == "pull" and messagebox.askyesno(APP_TITLE, "要開啟電腦儲存資料夾嗎？"):
                            self.open_dest()
                        if mode == "push":
                            self.load_path(self.current_path)

                elif kind == "error":
                    self.status_var.set(msg[1])
                    messagebox.showerror(APP_TITLE, msg[1])

        except queue.Empty:
            pass
        self.after(100, self.process_queue)

if __name__ == "__main__":
    App().mainloop()
