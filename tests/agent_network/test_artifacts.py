"""Artifacts: integrity, quarantine, traversal/bomb defense (sections 38-41, 108)."""

import hashlib
import zipfile

from aetheros_network.artifacts import (
    examine_artifact,
    release_path,
    safe_filename,
    sha256_file,
)


def test_safe_filename_strips_traversal():
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("..\\..\\win\\sys") == "sys"
    assert "/" not in safe_filename("a/b/c.txt")


def test_hash_matches_sha256(tmp_path):
    p = tmp_path / "doc.txt"
    p.write_bytes(b"hello artifact")
    assert sha256_file(p) == hashlib.sha256(b"hello artifact").hexdigest()


def test_clean_file_passes(tmp_path):
    p = tmp_path / "report.md"
    p.write_bytes(b"# quarterly report")
    verdict = examine_artifact(p)
    assert verdict["ok"] is True
    assert verdict["sha256"] == sha256_file(p)


def test_executable_blocked(tmp_path):
    p = tmp_path / "tool.exe"
    p.write_bytes(b"MZ fake")
    verdict = examine_artifact(p, filename="tool.exe")
    assert verdict["ok"] is False
    assert any("executable" in r for r in verdict["reasons"])


def test_macro_document_blocked(tmp_path):
    p = tmp_path / "sheet.xlsm"
    p.write_bytes(b"fake")
    verdict = examine_artifact(p, filename="sheet.xlsm")
    assert verdict["ok"] is False


def test_oversize_blocked(tmp_path, monkeypatch):
    import aetheros_network.artifacts as art

    monkeypatch.setattr(art, "MAX_ARTIFACT_BYTES", 10)
    p = tmp_path / "big.bin"
    p.write_bytes(b"x" * 64)
    verdict = examine_artifact(p)
    assert verdict["ok"] is False
    assert any("exceeds" in r for r in verdict["reasons"])


def test_zip_traversal_blocked(tmp_path):
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../../pwned.txt", b"x")
    verdict = examine_artifact(z)
    assert verdict["ok"] is False
    assert any("traversal" in r for r in verdict["reasons"])


def test_zip_member_cap(tmp_path, monkeypatch):
    import aetheros_network.artifacts as art

    monkeypatch.setattr(art, "MAX_ARCHIVE_MEMBERS", 2)
    z = tmp_path / "many.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for i in range(4):
            zf.writestr(f"f{i}.txt", b"x")
    verdict = examine_artifact(z)
    assert verdict["ok"] is False


def test_release_path_confined(tmp_path):
    dest = release_path(tmp_path / "q", "../../evil.txt")
    assert dest.parent == tmp_path / "q"
    assert dest.name == "evil.txt"
