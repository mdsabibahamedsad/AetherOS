from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from aetheros_voice.models.models import VoiceMode, STTProvider, TTSProvider, Personality


_voice_os = None


def _get_os():
    global _voice_os
    if _voice_os is None:
        from aetheros_voice import VoiceOS
        _voice_os = VoiceOS()
    return _voice_os


def voice_cmd(args: list[str] | None = None):
    if not args:
        return voice_help()
    sub = args[0]
    subcommands = {
        "start": voice_start,
        "stop": voice_stop,
        "config": voice_config,
        "test": voice_test,
        "help": voice_help,
    }
    handler = subcommands.get(sub)
    if handler:
        return handler(args[1:])
    return f"Unknown voice command: {sub}. Try: start, stop, config, test, help"


def voice_start(args: list[str] | None = None):
    mode = args[0] if args else "conversation"
    voice_os = _get_os()
    try:
        voice_mode = VoiceMode(mode)
    except ValueError:
        return f"Invalid mode: {mode}. Valid: conversation, command, dictation, assistant, continuous, push_to_talk"
    asyncio.run(voice_os.start(mode=voice_mode))
    return f"Voice OS started in {mode} mode. Say the wake word or press the trigger key."


def voice_stop(args: list[str] | None = None):
    voice_os = _get_os()
    asyncio.run(voice_os.stop())
    return "Voice OS stopped"


def voice_config(args: list[str] | None = None):
    voice_os = _get_os()
    if not args:
        cfg = voice_os.config_mgr.export_config()
        return json.dumps(cfg, indent=2)
    if len(args) >= 2:
        key, val = args[0], " ".join(args[1:])
        voice_os.config_mgr.set(key, val)
        return f"Set {key} = {val}"
    return voice_config.__doc__


def voice_test(args: list[str] | None = None):
    voice_os = _get_os()
    import asyncio
    devices = voice_os.capture.list_devices()
    result = {"microphones": devices, "status": "ok"}
    return json.dumps(result, indent=2)


def microphone_cmd(args: list[str] | None = None):
    voice_os = _get_os()
    if args and args[0] == "list":
        devices = voice_os.capture.list_devices()
        return json.dumps(devices, indent=2)
    if args and args[0] == "calibrate":
        return "Microphone calibration not implemented in CLI"
    return "Usage: aetheros microphone list | calibrate"


def voice_help(args: list[str] | None = None):
    return """Aether Voice OS — Commands:
  aetheros voice start [mode]    Start voice in mode (conversation|command|dictation|assistant|continuous|push_to_talk)
  aetheros voice stop            Stop voice
  aetheros voice config [key] [value]  View/set config
  aetheros voice test            Test microphone
  aetheros microphone list       List microphones
  aetheros voice help            Show this help"""
