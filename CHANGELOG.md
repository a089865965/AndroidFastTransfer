# Changelog

All notable public changes to AndroidFastTransfer will be documented in this file.

## [1.0.0] - Release candidate

### Added

- Windows GUI for Android ↔ PC file transfer over ADB.
- Android file browser with folder navigation and multi-selection.
- Bidirectional `adb pull` / `adb push` workflow.
- Real transfer percentage, elapsed time, speed and ETA.
- Cumulative progress across multiple files.
- Background transfer execution so the GUI remains responsive.
- Automatic ADB device detection.
- Automatic download of Google’s official Android Platform Tools when needed.
- `.pyw` / no-console launch behavior on Windows.
- Privacy scanner and publication guidance.

### Fixed

- Progress monitor could remain at 0% when ADB progress text was not flushed to Python in real time.
- Pull progress can fall back to local destination file size.
- Push progress can fall back to low-frequency remote destination size checks.
- Elapsed time no longer depends on ADB percentage output.

### Publication hygiene

- Repository content contains no developer-specific personal identifiers or real personal media filenames.
- Public screenshots are excluded unless they use synthetic data only.
- Added a repository privacy scanner and publication checklist.
- Public source is rebased on the tested stable transfer implementation; no privacy-only runtime behavior changes are introduced.


### Notes

- Transfer speed depends on the phone, USB controller, cable and host storage.
- A real-world 2.3 GB / ~8 s transfer was observed during development, but this is not a guaranteed benchmark.
