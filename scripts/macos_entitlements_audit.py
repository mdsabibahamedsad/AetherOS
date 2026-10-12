"""macOS entitlements audit (Master 65).

Parses electron/entitlements.mac.plist + .inherit.plist and enforces
production rules. Executable on ANY platform (pure plist XML):
`python scripts/macos_entitlements_audit.py`. Exit 0 = pass.
"""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

DESKTOP = Path(__file__).resolve().parent.parent / "apps" / "desktop"
MAIN_PLIST = DESKTOP / "electron" / "entitlements.mac.plist"
INHERIT_PLIST = DESKTOP / "electron" / "entitlements.mac.inherit.plist"

DEV_ONLY = {
    "com.apple.security.get-task-allow": "must be false/absent in production",
}

ELECTRON_JUSTIFIED = {
    "com.apple.security.cs.allow-jit": "Chromium JIT",
    "com.apple.security.cs.allow-unsigned-executable-memory": "Chromium JIT",
    "com.apple.security.cs.disable-library-validation": "Electron native modules",
    "com.apple.security.device.audio-input": "voice conversations (usage strings in build config)",
}


def audit_file(path: Path) -> list[str]:
    problems: list[str] = []
    if not path.exists():
        return [f"missing {path}"]
    with open(path, "rb") as fh:
        data = plistlib.load(fh)
    for key, why in DEV_ONLY.items():
        if data.get(key) is True:
            problems.append(f"{path.name}: {key} is TRUE in production — {why}")
    for key in data:
        if key.startswith("com.apple.security.") and key not in ELECTRON_JUSTIFIED and key not in DEV_ONLY:
            problems.append(f"{path.name}: unjustified entitlement {key}")
    return problems


def main() -> int:
    problems = audit_file(MAIN_PLIST) + audit_file(INHERIT_PLIST)
    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print(f"PASS: {MAIN_PLIST.name} + {INHERIT_PLIST.name} conform to production rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
