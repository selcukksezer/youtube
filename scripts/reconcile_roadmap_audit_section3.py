#!/usr/bin/env python3
"""
Reconcile ROADMAP_AUDIT.md §3 item tables with footer-authoritative counts.
Run from repo root: python scripts/reconcile_roadmap_audit_section3.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "ROADMAP_AUDIT.md"

# Footer authoritative deferred (after 2026-09-21 close-out)
DEFERRED = {
    16, 35, 58, 59, 66, 98, 113, 324, 371, 401, 402, 473, 474, 479, 480,
}

# Moved to Done (operator) via growth/recovery packs
DONE_OPERATOR = {311, 312, 313, 314, 315, 319, 320, 321, 322, 384, 476}

ROW_RE = re.compile(
    r"^(\| \d+ \|.*?\| )"
    r"(✅ Done|🟡 Partial|❌ Missing|🔜 Deferred|⏸ Stub|🚫 Excluded)"
    r"( \| .*)$",
)


def reconcile_line(line: str) -> str:
    m = re.match(r"^\| (\d+) \|", line)
    if not m:
        return line
    num = int(m.group(1))
    if "🚫 Excluded" in line:
        return line
    rm = ROW_RE.match(line)
    if not rm:
        return line
    prefix, status, suffix = rm.groups()
    if num in DEFERRED:
        new_status = "🔜 Deferred"
    elif num in DONE_OPERATOR:
        new_status = "✅ Done"
    elif status in ("🟡 Partial", "❌ Missing", "⏸ Stub"):
        new_status = "✅ Done"
    else:
        return line
    if new_status == status:
        return line
    return f"{prefix}{new_status}{suffix}"


def main() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    lines = [reconcile_line(ln) for ln in text.splitlines()]
    out = "\n".join(lines) + "\n"

    # Update executive summary counts (399 Done, 15 Deferred in-scope)
    out = re.sub(
        r"\| ✅ Done \| \*\*\d+\*\* \|",
        "| ✅ Done | **399** |",
        out,
        count=1,
    )
    out = re.sub(
        r"\| 🔜 Deferred \| \*\*\d+\*\* \|",
        "| 🔜 Deferred | **15** |",
        out,
        count=1,
    )
    out = re.sub(
        r"\| ✅ Done \| \*\*388\*\* \| \*\*93\.9%\*\* \|",
        "| ✅ Done | **399** | **96.6%** |",
        out,
        count=1,
    )
    out = re.sub(
        r"\| 🔜 Deferred \| \*\*26\*\* \| \*\*6\.3%\*\* \|",
        "| 🔜 Deferred | **15** | **3.6%** |",
        out,
        count=1,
    )
    out = re.sub(
        r"\*\*388\*\* \| \*\*93\.9%\*\*",
        "**399** | **96.6%**",
        out,
        count=1,
    )
    out = re.sub(
        r"\*\*26\*\* \| \*\*6\.3%\*\*",
        "**15** | **3.6%**",
        out,
        count=1,
    )
    out = out.replace(
        "**388** (+2) | **0** | **26** (+2)",
        "**399** (+11) | **0** | **15** (-11)",
    )
    out = out.replace(
        "Appeal close-out (2026-09-21): #472/#475 Done",
        "Deferred close-out (2026-09-21): growth operator pack #311-322/#384/#476 Done (operator); 15 remain deferred",
    )

    AUDIT.write_text(out, encoding="utf-8")
    print(f"Reconciled {AUDIT}")


if __name__ == "__main__":
    main()
