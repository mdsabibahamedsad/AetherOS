"""Voice commands — registry, parser, built-in commands."""

from aetheros_voice.commands.registry import CommandRegistry
from aetheros_voice.commands.builtin import BuiltInCommands
from aetheros_voice.commands.parser import CommandParser

__all__ = ["CommandRegistry", "BuiltInCommands", "CommandParser"]
