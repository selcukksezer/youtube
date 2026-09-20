#!/usr/bin/env python3
"""Pre-commit / pre-push secret scanner. Aborts if likely API keys found in staged files."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files/paths always skipped
SKIP_PATHS = {
    ".env",
    ".env.vault",
    "scripts/env_vault.py",
    "scripts/scan_secrets.py",
    "ENV_TRANSFER.md",
}

# Patterns that indicate real secrets (not placeholders)
PATTERNS = [
    (re.compile(r"GEMINI_API_KEY\s*=\s*AQ\.[A-Za-z0-9_-]{20,}"), "Gemini API key"),
    (re.compile(r"OPENAI_API_KEY\s*=\s*sk-[A-Za-z0-9]{20,}"), "OpenAI API key"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI-style sk- key"),
    (re.compile(r"AIza[0-9A-Za-z_-]{30,}"), "Google AIza key"),
    (re.compile(r"PEXELS_API_KEY\s*=\s*[A-Za-z0-9]{30,}"), "Pexels API key"),
    (re.compile(r"PIXABAY_API_KEY\s*=\s*[0-9a-f]{8}-[0-9a-f]{4}-"), "Pixabay API key"),
    (re.compile(r"ELEVENLABS_API_KEY\s*=\s*[A-Za-z0-9]{20,}"), "ElevenLabs API key"),
    (re.compile(r"REDDIT_CLIENT_SECRET\s*=\s*[A-Za-z0-9_-]{10,}"), "Reddit client secret"),
]

PLACEHOLDER_MARKERS = {"", "your_key_here", "changeme", "xxx", "placeholder"}


def staged_files() -> list[str]:
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return []
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def scan_file(rel_path: str) -> list[str]:
    hits: list[str] = []
    if rel_path.replace("\\", "/") in SKIP_PATHS:
        return hits
    if rel_path.endswith(".vault"):
        return hits
    full = ROOT / rel_path
    if not full.is_file():
        return hits
    try:
        text = full.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for rx, label in PATTERNS:
            m = rx.search(line)
            if not m:
                continue
            val = m.group(0).split("=", 1)[-1].strip() if "=" in m.group(0) else m.group(0)
            if val.lower() in PLACEHOLDER_MARKERS:
                continue
            hits.append(f"{rel_path}:{line_no} — possible {label}")
    return hits


def main() -> int:
    files = staged_files()
    if not files:
        print("scan_secrets: no staged files")
        return 0
    all_hits: list[str] = []
    for f in files:
        all_hits.extend(scan_file(f))
    if all_hits:
        print("SECRET SCAN FAILED — aborting commit/push:\n", file=sys.stderr)
        for h in all_hits:
            print(f"  {h}", file=sys.stderr)
        print("\nRemove secrets from staged files. Use scripts/env_vault.py for .env transfer.", file=sys.stderr)
        return 1
    print(f"scan_secrets: OK ({len(files)} staged files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
