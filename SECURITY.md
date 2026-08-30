# Security Policy

## Scope

AndroidFastTransfer is a local Windows GUI around Android Debug Bridge (ADB) file transfer.

## Trust model

- USB debugging grants powerful access to an Android device.
- Only authorize ADB connections from computers you trust.
- Do not use this tool on devices you are not authorized to access.
- Android Platform Tools are downloaded from Google's official Android repository URL when ADB is not already available.

## Reporting a security issue

When reporting a problem, do **not** include:

- raw ADB device serial numbers
- personal filenames
- full local Windows paths
- account names or email addresses
- screenshots containing private notifications or file listings
- authentication tokens, API keys or credentials

Replace sensitive values with generic placeholders such as `DEVICE_SERIAL_REDACTED`, `LOCAL_PATH_REDACTED` and `demo_video.mp4`.

If a report requires sensitive diagnostic data, do not post it in a public GitHub issue.
