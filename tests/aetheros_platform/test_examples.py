"""Every shipped example must compile and run (Master 62 §53, §88).

Gateway-backed examples run against the live test gateway; offline examples
run in-process. Direct execution needs the repo root on sys.path
(`PYTHONPATH=.`), which pytest provides via rootdir insertion.
"""

import importlib


def test_tool_example_offline():
    mod = importlib.import_module("aetheros_platform.examples.tool_agent")
    assert mod.main()["shout"] == "HELLO TOOL SDK"


def test_skill_example_offline():
    mod = importlib.import_module("aetheros_platform.examples.custom_skill")
    resolved = mod.main()
    assert "summarize@1.0.0" in resolved["tools"]


def test_mcp_server_example_offline(tmp_path):
    mod = importlib.import_module("aetheros_platform.examples.mcp_server")
    data = mod.main(str(tmp_path / "mcp-ex"))
    assert "hello" in data["tools"]


def test_gateway_examples(live, keypair):
    cases = [
        ("aetheros_platform.examples.hello_agent", {}),
        ("aetheros_platform.examples.research_agent", {}),
        ("aetheros_platform.examples.memory_agent", {}),
        ("aetheros_platform.examples.automation_agent", {}),
        ("aetheros_platform.examples.a2a_agent", {}),
    ]
    for dotted, _ in cases:
        mod = importlib.import_module(dotted)
        out = mod.main(live, keypair["api_key"])
        assert isinstance(out, dict), dotted
