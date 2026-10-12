"""Regression test: `agent` and `agent-network` CLI parsers must coexist.

The Agent Network CLI once registered the top-level `agent` name, colliding
with the agent ecosystem parser (`agents/cli.py`) and crashing EVERY CLI
invocation (argparse raises on duplicate subparser names). The network CLI
now owns `agent-network`. This test pins that contract.
"""

import argparse


def _root():
    parser = argparse.ArgumentParser(prog="aetheros")
    return parser, parser.add_subparsers(dest="command")


def test_both_agent_parsers_register_without_conflict():
    from agents.cli import build_agent_subparser
    from aetheros_cli.agent_network_cmd import build_parser

    parser, sub = _root()
    build_parser(sub)
    build_agent_subparser(sub)  # must not raise: conflicting subparser: agent

    ns = parser.parse_args(["agent-network", "list"])
    assert ns.command == "agent-network"
    assert ns.agent_verb == "list"

    ns2 = parser.parse_args(["agent", "dashboard"])
    assert ns2.command == "agent"


def test_network_parser_name_is_agent_network():
    from aetheros_cli.agent_network_cmd import build_parser

    parser, sub = _root()
    p = build_parser(sub)
    assert p.prog.endswith("agent-network")
