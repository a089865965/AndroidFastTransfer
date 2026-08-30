# AndroidFastTransfer

A lightweight Windows GUI for fast bidirectional file transfer between Android and PC using ADB.

AndroidFastTransfer keeps the native `adb pull` / `adb push` transfer path while adding a practical desktop interface, multi-file transfer, real progress monitoring, elapsed time, speed and ETA.

## Features

- Android → Windows and Windows → Android transfer
- Copy semantics by default: source files are not deleted automatically
- Android file browser starting from `/sdcard`
- Multi-select files and folders
- Real transfer progress, elapsed time, speed and ETA
- Multi-file cumulative progress
- GUI stays responsive during transfer
- No extra console window when launched as `.pyw`
- Automatic detection of authorized ADB devices
- Automatic download of Google’s official Android Platform Tools when ADB is unavailable
- No third-party Python packages required

## Why this project exists

ADB is already fast and reliable, but raw command-line use is inconvenient for frequent large-file transfers. AndroidFastTransfer focuses on making the existing ADB transport usable as a daily GUI tool without replacing the transfer core.

One real-world test transferred about 2.3 GB in roughly 8 seconds. This is an example from one device/cable/PC setup, not a guaranteed speed; actual throughput depends on USB mode, cable, device storage and host hardware.

## Progress monitoring

Some Windows / ADB combinations do not flush `adb -p` progress output to Python in real time. Earlier builds could therefore keep transferring successfully while the GUI remained at 0%.

The current release keeps ADB as the transfer engine and adds independent progress monitoring. For pull operations it can observe the local destination size; for push operations it can query remote destination size at a low frequency. Elapsed time is updated independently from ADB stdout.

## Requirements

- Windows 10 or Windows 11
- Python 3 with Tkinter
- Android device with USB debugging enabled
- USB connection authorized for ADB

ADB / Platform Tools are handled by the application when needed.

## Usage

1. Enable Developer options and USB debugging on the Android device.
2. Connect the device by USB and approve the ADB authorization prompt.
3. Launch `src/AndroidFastTransfer.pyw`.
4. Choose transfer direction.
5. Select the source files or folders.
6. Choose the destination and start transfer.
7. Confirm progress, speed and completion status in the GUI.

## Repository layout

```text
AndroidFastTransfer/
├─ src/
│  └─ AndroidFastTransfer.pyw
├─ docs/
│  └─ PRIVACY.md
├─ scripts/
│  └─ privacy_scan.py
├─ screenshots/
│  └─ README.md
├─ README.md
├─ CHANGELOG.md
├─ SECURITY.md
├─ LICENSE
├─ requirements.txt
└─ .gitignore
```

## Privacy

The repository is intentionally content-clean: the source and documentation contain no developer-specific name, email address, phone number, device serial, personal absolute path, private cloud link, API key, access token, or real personal media filename.

Runtime values such as the connected ADB device serial, local paths and selected filenames are read from the user's own machine/device and are not embedded in the repository. Public screenshots and examples must use synthetic filenames only. See [`docs/PRIVACY.md`](docs/PRIVACY.md).

A repository privacy scanner is included:

```bash
python scripts/privacy_scan.py .
```

The scan is a safety net, not a guarantee. Always review changes before making a repository public.

## Security

This tool invokes ADB commands on a USB-debugging-authorized Android device. Only connect devices and computers you trust. See [`SECURITY.md`](SECURITY.md).

## Status

Public release candidate: **v1.0.0**

The public source is rebased on the tested stable transfer implementation; privacy cleanup is limited to repository content and does not add untested runtime behavior.

## License

MIT License. See [`LICENSE`](LICENSE).

---

## 中文簡介

AndroidFastTransfer 是一套 Windows ↔ Android 的 ADB 高速雙向傳檔 GUI。它保留 `adb pull / adb push` 的傳輸核心，補上檔案瀏覽、多檔傳輸、真實進度、已用時間、速度與 ETA。

公開版另外加入內容隱私保護整理：原始碼不硬編碼個人路徑、裝置序號、Email、電話、Token 或 API Key。執行時由 ADB 動態取得的裝置序號、使用者選取的路徑與檔名屬於本機執行資料，不會被寫入 repository；公開截圖、Log 或 Issue 前仍應再次去識別化。
