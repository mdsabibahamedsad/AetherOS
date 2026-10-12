"""Developer CLI contracts: scaffolds are runnable projects (Master 62 §78)."""

import sys


def test_init_agent_scaffold_is_runnable(tmp_path, home, monkeypatch):
    import os
    repo_root = os.getcwd()
    from aetheros_platform.cli import main
    monkeypatch.chdir(tmp_path)
    assert main(["init", "agent", "demo-agent", "--dest", str(tmp_path)]) == 0
    proj = tmp_path / "demo-agent"
    for f in ("agent.py", "test_agent.py", "manifest.json", "policy.yaml",
              "README.md"):
        assert (proj / f).exists(), f
    # Generated test file passes offline (manifest validation part):
    import subprocess
    env = dict(os.environ, PYTHONPATH=repo_root, AETHEROS_HOME=str(home))
    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(proj / "test_agent.py"), "-q",
         "-p", "no:cacheprovider", "-o", "addopts=", "-k", "manifest_valid"],
        capture_output=True, text=True, timeout=120,
        cwd=str(tmp_path), env=env)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-500:]


def test_init_all_kinds(tmp_path, home, monkeypatch):
    from aetheros_platform.cli import main
    monkeypatch.chdir(tmp_path)
    for kind in ("agent", "tool", "skill", "mcp", "a2a", "extension"):
        assert main(["init", kind, f"demo-{kind}",
                     "--dest", str(tmp_path / "all")]) == 0, kind


def test_schema_and_api_list_commands(capsys):
    from aetheros_platform.cli import main
    assert main(["schema", "--name", "Agent"]) == 0
    assert main(["api", "list"]) == 0
    out = capsys.readouterr().out
    assert "/api/v1/agents" in out
