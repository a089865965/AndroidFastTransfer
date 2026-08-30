# AndroidFastTransfer

A lightweight Windows GUI for fast bidirectional file transfer between Android devices and PCs using ADB.

AndroidFastTransfer keeps the native `adb pull` / `adb push` transfer path while adding file browsing, multi-file transfer, real progress, elapsed time, transfer speed and ETA.

## Features

- Android → Windows and Windows → Android transfer
- Copy semantics: source files are not deleted automatically
- Android file browser starting from `/sdcard`
- Multi-select files and folders
- Real transfer progress, elapsed time, speed and ETA
- Cumulative progress across multiple files
- Responsive GUI during transfer
- No extra console window when launched as `.pyw`
- Automatic detection of authorized ADB devices
- Automatic download of Google Android Platform Tools when ADB is unavailable
- No third-party Python packages required

## Requirements

- Windows 10 or Windows 11
- Python 3 with Tkinter
- Android device with USB debugging enabled
- USB connection authorized for ADB

## Usage

1. Enable Developer options and USB debugging on the Android device.
2. Connect the device by USB and approve the ADB authorization prompt.
3. Launch `src/AndroidFastTransfer.pyw`.
4. Choose the transfer direction.
5. Select the source files or folders.
6. Choose the destination.
7. Start the transfer.

If ADB is not available, AndroidFastTransfer can download Google Android Platform Tools automatically.

## How progress works

Some ADB builds do not continuously flush `adb -p` progress text when their output is redirected.

AndroidFastTransfer therefore keeps ADB as the transfer engine while independently monitoring transferred data. For Android → PC transfers it can observe the destination size on the PC. For PC → Android transfers it can query the destination size on the device at a low frequency. This allows the GUI to continue showing useful progress without replacing the ADB transfer core.

## Repository layout

```text
AndroidFastTransfer/
├─ src/
│  └─ AndroidFastTransfer.pyw
├─ README.md
├─ CHANGELOG.md
├─ SECURITY.md
├─ LICENSE
├─ CHECKSUMS.txt
├─ requirements.txt
└─ .gitignore
```

## Performance

Transfer speed depends on the phone, USB controller, cable and storage performance. A development test transferred about 2.3 GB in roughly 8 seconds, but this is not a guaranteed benchmark.

## Security

This tool executes ADB commands on an Android device authorized for USB debugging. Only connect devices and computers you trust. See [`SECURITY.md`](SECURITY.md).

## License

MIT License. See [`LICENSE`](LICENSE).

---

## 中文簡介

AndroidFastTransfer 是一套 Windows ↔ Android 的 ADB 高速雙向傳檔 GUI。

它保留原生 `adb pull / adb push` 傳輸核心，並提供手機檔案瀏覽、多檔案傳輸、真實進度、已用時間、速度與 ETA。傳輸採複製方式，不會自動刪除來源檔案。

### 使用方式

1. 在 Android 手機開啟「開發人員選項」與「USB 偵錯」。
2. 使用 USB 連接電腦並允許 ADB 授權。
3. 執行 `src/AndroidFastTransfer.pyw`。
4. 選擇「手機 → 電腦」或「電腦 → 手機」。
5. 選取檔案／資料夾與目的地後開始傳輸。

若電腦尚未安裝 ADB，程式可自動下載 Google Android Platform Tools。
