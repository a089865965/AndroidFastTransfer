# Privacy and Publication Checklist

This repository is prepared under a **content-clean** publication rule.

The GitHub account/profile identity is outside this checklist. The requirement here is that the files uploaded to the repository — source code, documentation, examples, screenshots and release assets — do not contain personal information or real personal test filenames.

## Repository content must not contain

- personal names
- personal email addresses
- phone numbers
- developer-specific absolute home-directory paths
- hardcoded ADB device serial numbers
- private-environment IP addresses
- API keys, access tokens, passwords or private keys
- private cloud-storage links, folder IDs or document IDs
- real personal media filenames
- real test-data filenames that can be tied back to the developer

## Runtime data is different

AndroidFastTransfer reads local information at runtime, including the connected ADB device serial, file paths and filenames. That is expected application behavior.

The publication rule is that none of those runtime values are **hardcoded, copied into documentation, committed as logs, or captured in public screenshots**.

## Screenshots and examples

Only synthetic data may be used in repository screenshots or examples.

Safe examples include:

- `demo_video_01.mp4`
- `demo_video_02.mp4`
- `sample_folder`
- `/sdcard/Download/demo/`

Do not upload screenshots made from real personal files, even if the screenshot seems harmless. Inspect the full frame for filenames, folder names, device IDs, notifications, browser tabs and account information.

## Pre-publication gate

1. Start from the tested stable source, not from a private working directory with Git history.
2. Run `python scripts/privacy_scan.py .`.
3. Review every file that will be committed.
4. Confirm there is no imported `.git` history from a private project.
5. Confirm screenshots/examples contain synthetic data only.
6. Confirm release archives contain only the intended repository files.
7. Create the GitHub repository as private first if an additional web-side review is desired.
8. Publish only after the repository contents match this checklist.

## Current candidate

The v1.0.0 release candidate has been scanned for common personal-data and secret patterns. The source file is rebased on the tested stable transfer implementation. No real-world test filenames are included in the repository candidate.
