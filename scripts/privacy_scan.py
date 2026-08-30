#!/usr/bin/env python3
"""Conservative repository privacy/secrets preflight scanner.

This is a safety net, not a substitute for manual review.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "dist", "build", "platform-tools"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".zip", ".exe", ".dll", ".pyc"}

PATTERNS = {
    "email": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "windows_user_path": re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\\r\n]+"),
    "mac_linux_user_path": re.compile(r"/(?:Users|home)/[^/\s]+"),
    "ipv4": re.compile(r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b"),
    "github_token": re.compile(r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "google_drive_link": re.compile(r"https?://(?:drive|docs)\\.google\\.com/[^\\s]+", re.I),
    "common_phone_number": re.compile(r"(?<!\\d)(?:\\+?886[- ]?)?0?9\\d{8}(?!\\d)"),
    "dated_camera_filename": re.compile(r"\\b20\\d{6}[_-]\\d{6}(?:\\.[A-Za-z0-9]{2,5})?\\b"),
}

def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.name == Path(__file__).name:
            continue
        try:
            data = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        yield path, data

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    findings = []
    for path, data in iter_text_files(root):
        for name, regex in PATTERNS.items():
            for match in regex.finditer(data):
                line = data.count("\n", 0, match.start()) + 1
                findings.append((path.relative_to(root), line, name, match.group(0)))

    if findings:
        print("PRIVACY SCAN: FAIL")
        for path, line, kind, value in findings:
            shown = value if len(value) <= 100 else value[:97] + "..."
            print(f"{path}:{line}: {kind}: {shown}")
        print("\nReview and remove/redact all findings before public release.")
        return 1

    print("PRIVACY SCAN: PASS")
    print("No configured personal-data or secret patterns were found in text files.")
    print("Manual review is still required, especially for screenshots, examples and release archives.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
