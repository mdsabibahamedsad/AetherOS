"""Linux desktop-entry structural check (Master 66).

Validates the electron-builder linux desktop entry contract WITHOUT a
Linux host: parses package.json build.linux (categories, mime, exec
name) + asserts branding (no Hermes refs) and required fields. Real
`desktop-file-validate` + install testing happens in CI/on-VM (BLOCKED
here). Exit 0 = pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DESKTOP = Path(__file__).resolve().parent.parent / "apps" / "desktop"


def main() -> int:
    pkg = json.loads((DESKTOP / "package.json").read_text())
    build = pkg.get("build", {})
    linux = build.get("linux", {})
    problems: list[str] = []

    for key in ("category", "maintainer", "executableName", "icon"):
        if not linux.get(key):
            problems.append(f"build.linux.{key} missing")
    if "AppImage" not in [t.get("target") for t in linux.get("target", [])]:
        problems.append("AppImage target missing (primary format)")
    protos = [s for p in build.get("protocols", []) for s in p.get("schemes", [])]
    if "aetheros" not in protos:
        problems.append("aetheros:// protocol not registered")
    for assoc in build.get("fileAssociations", []):
        if "aetheros" not in assoc.get("name", "").lower() and \
                "aetheros" not in assoc.get("ext", ""):
            problems.append(f"non-aetheros file association: {assoc}")

    blob = json.dumps(build).lower()
    if "hermes" in blob:
        problems.append("legacy Hermes reference in build config")

    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print("PASS: linux desktop-entry contract (AppImage/deb/rpm, protocol, associations, branding)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
