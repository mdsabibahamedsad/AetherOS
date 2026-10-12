"""CLI commands for Voice OS — aetheros voice *."""

from aetheros_voice.cli.commands import (
    voice_cmd, voice_start, voice_stop, voice_config,
    voice_test, microphone_cmd,
)

__all__ = ["voice_cmd", "voice_start", "voice_stop", "voice_config", "voice_test", "microphone_cmd"]
