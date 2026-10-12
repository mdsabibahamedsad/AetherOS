from pathlib import Path


def test_windows_native_install_path_docs_match_installer() -> None:
    doc = Path("website/docs/user-guide/windows-native.md").read_text()
    install = Path("scripts/install.ps1").read_text()

    assert "%LOCALAPPDATA%\\aetheros\\aetheros\\venv\\Scripts" in doc
    assert "Get-Command aetheros        # should print C:\\Users\\<you>\\AppData\\Local\\aetheros\\aetheros\\venv\\Scripts\\hermes.exe" in doc
    assert '$hermesBin = "$InstallDir\\venv\\Scripts"' in install
