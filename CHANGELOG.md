# Changelog

All notable changes to AndroidFastTransfer will be documented in this file.

## [1.0.0]

### Added

- Windows GUI for Android ↔ PC file transfer over ADB.
- Android file browser with folder navigation and multi-selection.
- Bidirectional `adb pull` / `adb push` workflow.
- Real transfer percentage, elapsed time, speed and ETA.
- Cumulative progress across multiple files.
- Background transfer execution so the GUI remains responsive.
- Automatic ADB device detection.
- Automatic download of Google Android Platform Tools when needed.
- `.pyw` / no-console launch behavior on Windows.

### Fixed

- Progress could remain at 0% when ADB progress text was not flushed to Python in real time.
- Android → PC progress can fall back to local destination size monitoring.
- PC → Android progress can fall back to low-frequency remote destination size checks.
- Elapsed time no longer depends on ADB percentage output.

### Notes

- Transfers use copy semantics; source files are not automatically deleted.
- Transfer speed depends on the phone, USB controller, cable and host storage.
