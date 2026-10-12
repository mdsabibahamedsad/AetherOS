"""Slash-command handlers for the interactive CLI (god-file decomposition Phase 4).

This module hosts the ``_handle_*_command`` slash-command handlers lifted out of
``cli.py``'s ``AetherosCLI`` class. ``AetherosCLI`` inherits ``CLICommandsMixin`` so
every ``self.<handler>`` call resolves unchanged via the MRO — behavior-neutral.

Import discipline (mirrors gateway/slash_commands.py, PR #41886):
  * Neutral, non-cyclic deps are imported at module top-level below.
  * cli.py-internal symbols (the ``_cprint``/``_ACCENT``/``save_config_value``…
    module-level helpers and constants) are imported LAZILY inside each handler
    via ``from cli import ...`` — that resolves at call time when ``cli`` is fully
    loaded, so the mixin module never imports ``cli`` at top level (no cycle).
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from rich import box as rich_box
from rich.markup import escape as _escape
from rich.panel import Panel

from aetheros_constants import display_aetheros_home, is_termux as _is_termux_environment
from aetheros_cli.browser_connect import (
    DEFAULT_BROWSER_CDP_URL,
    is_browser_debug_ready,
    manual_chrome_debug_command,
)


class CLICommandsMixin:
    """Mixin holding the interactive-CLI slash-command handlers.

    All methods use only ``self`` state plus the imports above and per-method
    lazy ``from cli import ...`` lines, so they compose cleanly onto
    ``AetherosCLI`` via the MRO.
    """

    def _handle_rollback_command(self, command: str):
        """Handle /rollback — list, diff, or restore filesystem checkpoints.

        Syntax:
            /rollback                 — list checkpoints
            /rollback <N>             — restore checkpoint N (also undoes last chat turn)
            /rollback diff <N>        — preview changes since checkpoint N
            /rollback <N> <file>      — restore a single file from checkpoint N
        """
        from tools.checkpoint_manager import format_checkpoint_list

        if not hasattr(self, 'agent') or not self.agent:
            print("  No active agent session.")
            return

        mgr = self.agent._checkpoint_mgr
        if not mgr.enabled:
            print("  Checkpoints are not enabled.")
            print("  Enable with: aetheros --checkpoints")
            print("  Or in config.yaml: checkpoints: { enabled: true }")
            return

        cwd = os.getenv("TERMINAL_CWD", os.getcwd())
        parts = command.split()
        args = parts[1:] if len(parts) > 1 else []

        if not args:
            # List checkpoints
            checkpoints = mgr.list_checkpoints(cwd)
            print(format_checkpoint_list(checkpoints, cwd))
            return

        # Handle /rollback diff <N>
        if args[0].lower() == "diff":
            if len(args) < 2:
                print("  Usage: /rollback diff <N>")
                return
            checkpoints = mgr.list_checkpoints(cwd)
            if not checkpoints:
                print(f"  No checkpoints found for {cwd}")
                return
            target_hash = self._resolve_checkpoint_ref(args[1], checkpoints)
            if not target_hash:
                return
            result = mgr.diff(cwd, target_hash)
            if result["success"]:
                stat = result.get("stat", "")
                diff = result.get("diff", "")
                if not stat and not diff:
                    print("  No changes since this checkpoint.")
                else:
                    if stat:
                        print(f"\n{stat}")
                    if diff:
                        # Limit diff output to avoid terminal flood
                        diff_lines = diff.splitlines()
                        if len(diff_lines) > 80:
                            print("\n".join(diff_lines[:80]))
                            print(f"\n  ... ({len(diff_lines) - 80} more lines, showing first 80)")
                        else:
                            print(f"\n{diff}")
            else:
                print(f"  ❌ {result['error']}")
            return

        # Resolve checkpoint reference (number or hash)
        checkpoints = mgr.list_checkpoints(cwd)
        if not checkpoints:
            print(f"  No checkpoints found for {cwd}")
            return

        target_hash = self._resolve_checkpoint_ref(args[0], checkpoints)
        if not target_hash:
            return

        # Check for file-level restore: /rollback <N> <file>
        file_path = args[1] if len(args) > 1 else None

        result = mgr.restore(cwd, target_hash, file_path=file_path)
        if result["success"]:
            if file_path:
                print(f"  ✅ Restored {file_path} from checkpoint {result['restored_to']}: {result['reason']}")
            else:
                print(f"  ✅ Restored to checkpoint {result['restored_to']}: {result['reason']}")
            print("  A pre-rollback snapshot was saved automatically.")

            # Also undo the last conversation turn so the agent's context
            # matches the restored filesystem state
            if self.conversation_history:
                self.undo_last(prefill=False)
                print("  Chat turn undone to match restored file state.")
        else:
            print(f"  ❌ {result['error']}")

    def _handle_snapshot_command(self, command: str):
        """Handle /snapshot — lightweight state snapshots for Aetheros config/state.

        Syntax:
            /snapshot                  — list recent snapshots
            /snapshot create [label]   — create a snapshot
            /snapshot restore <id>     — restore state from snapshot
            /snapshot prune [N]        — prune to N snapshots (default 20)
        """
        from aetheros_cli.backup import (
            create_quick_snapshot, list_quick_snapshots,
            restore_quick_snapshot, prune_quick_snapshots,
        )
        from aetheros_constants import display_aetheros_home

        parts = command.split()
        subcmd = parts[1].lower() if len(parts) > 1 else "list"

        if subcmd in {"list", "ls"}:
            snaps = list_quick_snapshots()
            if not snaps:
                print("  No state snapshots yet.")
                print("  Create one: /snapshot create [label]")
                return
            print(f"  State snapshots ({display_aetheros_home()}/state-snapshots/):\n")
            print(f"  {'#':>3}  {'ID':<35} {'Files':>5} {'Size':>10} {'Label'}")
            print(f"  {'─'*3}  {'─'*35} {'─'*5} {'─'*10} {'─'*20}")
            for i, s in enumerate(snaps, 1):
                size = s.get("total_size", 0)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.0f} KB"
                else:
                    size_str = f"{size / 1024 / 1024:.1f} MB"
                label = s.get("label") or ""
                print(f"  {i:3}  {s['id']:<35} {s.get('file_count', 0):>5} {size_str:>10} {label}")

        elif subcmd == "create":
            label = " ".join(parts[2:]) if len(parts) > 2 else None
            snap_id = create_quick_snapshot(label=label)
            if snap_id:
                print(f"  Snapshot created: {snap_id}")
            else:
                print("  No state files found to snapshot.")

        elif subcmd in {"restore", "rewind"}:
            if len(parts) < 3:
                print("  Usage: /snapshot restore <snapshot-id>")
                # Show hint with most recent snapshot
                snaps = list_quick_snapshots(limit=1)
                if snaps:
                    print(f"  Most recent: {snaps[0]['id']}")
                return
            snap_id = parts[2]
            # Allow restore by number (1-indexed)
            try:
                idx = int(snap_id)
                snaps = list_quick_snapshots()
                if 1 <= idx <= len(snaps):
                    snap_id = snaps[idx - 1]["id"]
                else:
                    print(f"  Invalid snapshot number. Use 1-{len(snaps)}.")
                    return
            except ValueError:
                pass
            if restore_quick_snapshot(snap_id):
                print(f"  Restored state from: {snap_id}")
                print("  Restart recommended for state.db changes to take effect.")
            else:
                print(f"  Snapshot not found: {snap_id}")

        elif subcmd == "prune":
            keep = 20
            if len(parts) > 2:
                try:
                    keep = int(parts[2])
                except ValueError:
                    print("  Usage: /snapshot prune [keep-count]")
                    return
            deleted = prune_quick_snapshots(keep=keep)
            print(f"  Pruned {deleted} old snapshot(s) (keeping {keep}).")

        else:
            print(f"  Unknown subcommand: {subcmd}")
            print("  Usage: /snapshot [list|create [label]|restore <id>|prune [N]]")

    def _handle_stop_command(self):
        """Handle /stop — kill all running background processes.

        Inspired by OpenAI Codex's separation of interrupt (stop current turn)
        from /stop (clean up background processes). See openai/codex#14602.
        """
        from tools.process_registry import process_registry

        processes = process_registry.list_sessions()
        running = [p for p in processes if p.get("status") == "running"]

        if not running:
            print("  No running background processes.")
            return

        print(f"  Stopping {len(running)} background process(es)...")
        killed = process_registry.kill_all()
        print(f"  ✅ Stopped {killed} process(es).")

    def _handle_agents_command(self):
        """Handle /agents — show background processes and all registered AI agents."""
        from cli import _cprint
        from tools.process_registry import format_uptime_short, process_registry

        processes = process_registry.list_sessions()
        running = [p for p in processes if p.get("status") == "running"]
        finished = [p for p in processes if p.get("status") != "running"]

        _cprint(f"  Running processes: {len(running)}")
        for p in running:
            cmd = p.get("command", "")[:80]
            up = format_uptime_short(p.get("uptime_seconds", 0))
            _cprint(f"    {p.get('session_id', '?')} · {up} · {cmd}")

        if finished:
            _cprint(f"  Recently finished: {len(finished)}")

        agent_running = getattr(self, "_agent_running", False)
        _cprint(f"  Main agent: {'running' if agent_running else 'idle'}")

        # Show registered multi-agents from the agent system
        try:
            from agents import list_all_agents
            registered = list_all_agents()
            if registered:
                _cprint(f"  Registered agents: {len(registered)}")
                for a in registered:
                    status_icon = "●" if a.status == "running" else "○"
                    _cprint(f"    {a.avatar.icon} {status_icon} {a.name} ({a.role.replace('_', ' ').title()})")
        except Exception:
            pass

    def _handle_workflow_command(self, cmd_original):
        """Handle /workflow — run workflow CLI commands."""
        from cli import _cprint
        from workflows.cli import build_workflow_subparser, handle_workflow_command, show_workflow_help
        import argparse, shlex
        parser = argparse.ArgumentParser(prog="workflow", add_help=False)
        subs = parser.add_subparsers(dest="workflow_command")
        build_workflow_subparser(subs)
        parts = shlex.split(cmd_original, posix=False)
        if parts and parts[0].startswith("/"):
            parts[0] = "workflow"
        try:
            args = parser.parse_args(parts[1:] if len(parts) > 1 else [])
            if args.workflow_command:
                handle_workflow_command(args)
            else:
                show_workflow_help()
        except SystemExit:
            pass

    def _handle_hub_command(self, cmd_original):
        from hub.cli import handle_hub_command, show_hub_help
        import argparse, shlex
        from hub.cli import build_hub_parser
        parser = argparse.ArgumentParser(prog="hub", add_help=False)
        subs = parser.add_subparsers(dest="hub_command")
        build_hub_parser(subs)
        parts = shlex.split(cmd_original, posix=False)
        if parts and parts[0].startswith("/"):
            parts[0] = "hub"
        try:
            args = parser.parse_args(parts[1:] if len(parts) > 1 else [])
            if args.hub_command:
                handle_hub_command(args)
            else:
                show_hub_help()
        except SystemExit:
            pass

    def _handle_plugin_command(self, cmd_original):
        from hub.cli import build_hub_plugin_parser as build_plugin_parser, handle_plugin_command
        import argparse, shlex
        parser = argparse.ArgumentParser(prog="plugin", add_help=False)
        subs = parser.add_subparsers(dest="plugin_command")
        build_plugin_parser(subs)
        parts = shlex.split(cmd_original, posix=False)
        if parts and parts[0].startswith("/"):
            parts[0] = "plugin"
        try:
            args = parser.parse_args(parts[1:] if len(parts) > 1 else [])
            if args.plugin_command:
                handle_plugin_command(args)
        except SystemExit:
            pass

    def _handle_mcp_command(self, cmd_original):
        from hub.cli import build_hub_mcp_parser as build_mcp_parser, handle_mcp_command
        import argparse, shlex
        parser = argparse.ArgumentParser(prog="mcp", add_help=False)
        subs = parser.add_subparsers(dest="mcp_command")
        build_mcp_parser(subs)
        parts = shlex.split(cmd_original, posix=False)
        if parts and parts[0].startswith("/"):
            parts[0] = "mcp"
        try:
            args = parser.parse_args(parts[1:] if len(parts) > 1 else [])
            if args.mcp_command:
                handle_mcp_command(args)
        except SystemExit:
            pass

    def _handle_skill_command(self, cmd_original):
        from hub.cli import build_hub_skill_parser as build_skill_parser, handle_skill_command
        import argparse, shlex
        parser = argparse.ArgumentParser(prog="skill", add_help=False)
        subs = parser.add_subparsers(dest="skill_command")
        build_skill_parser(subs)
        parts = shlex.split(cmd_original, posix=False)
        if parts and parts[0].startswith("/"):
            parts[0] = "skill"
        try:
            args = parser.parse_args(parts[1:] if len(parts) > 1 else [])
            if args.skill_command:
                handle_skill_command(args)
        except SystemExit:
            pass

    def _handle_theme_command(self, cmd_original):
        from hub.cli import build_hub_theme_parser as build_theme_parser, handle_theme_command
        import argparse, shlex
        parser = argparse.ArgumentParser(prog="theme", add_help=False)
        subs = parser.add_subparsers(dest="theme_command")
        build_theme_parser(subs)
        parts = shlex.split(cmd_original, posix=False)
        if parts and parts[0].startswith("/"):
            parts[0] = "theme"
        try:
            args = parser.parse_args(parts[1:] if len(parts) > 1 else [])
            if args.theme_command:
                handle_theme_command(args)
        except SystemExit:
            pass

    def _handle_sdk_command(self, cmd_original):
        from hub.cli import build_hub_sdk_parser as build_sdk_parser, handle_sdk_command
        import argparse, shlex
        parser = argparse.ArgumentParser(prog="sdk", add_help=False)
        subs = parser.add_subparsers(dest="sdk_command")
        build_sdk_parser(subs)
        parts = shlex.split(cmd_original, posix=False)
        if parts and parts[0].startswith("/"):
            parts[0] = "sdk"
        try:
            args = parser.parse_args(parts[1:] if len(parts) > 1 else [])
            if args.sdk_command:
                handle_sdk_command(args)
        except SystemExit:
            pass

    def _handle_paste_command(self):
        """Handle /paste — explicitly check clipboard for an image.

        This is the reliable fallback for terminals where BracketedPaste
        doesn't fire for image-only clipboard content (e.g., VSCode terminal,
        Windows Terminal with WSL2).
        """
        from cli import _DIM, _RST, _cprint, _termux_example_image_path
        if _is_termux_environment():
            _cprint(
                f"  {_DIM}Clipboard image paste is not available on Termux — "
                f"use /image <path> or paste a local image path like "
                f"{_termux_example_image_path()}{_RST}"
            )
            return

        from aetheros_cli.clipboard import has_clipboard_image
        if has_clipboard_image():
            if self._try_attach_clipboard_image():
                n = len(self._attached_images)
                _cprint(f"  📎 Image #{n} attached from clipboard")
            else:
                _cprint(f"  {_DIM}(>_<) Clipboard has an image but extraction failed{_RST}")
        else:
            _cprint(f"  {_DIM}(._.) No image found in clipboard{_RST}")

    def _handle_copy_command(self, cmd_original: str) -> None:
        """Handle /copy [number] — copy assistant output to clipboard."""
        from cli import _assistant_copy_text, _cprint
        parts = cmd_original.split(maxsplit=1)
        arg = parts[1].strip() if len(parts) > 1 else ""

        assistant = [m for m in self.conversation_history if m.get("role") == "assistant"]
        if not assistant:
            _cprint("  Nothing to copy yet.")
            return

        if arg:
            try:
                idx = int(arg) - 1
            except ValueError:
                _cprint("  Usage: /copy [number]")
                return
            if idx < 0 or idx >= len(assistant):
                _cprint(f"  Invalid response number. Use 1-{len(assistant)}.")
                return
        else:
            idx = len(assistant) - 1
            while idx >= 0 and not _assistant_copy_text(assistant[idx].get("content")):
                idx -= 1
            if idx < 0:
                _cprint("  Nothing to copy in assistant responses yet.")
                return

        text = _assistant_copy_text(assistant[idx].get("content"))
        if not text:
            _cprint("  Nothing to copy in that assistant response.")
            return

        try:
            self._write_osc52_clipboard(text)
            _cprint(f"  Copied assistant response #{idx + 1} to clipboard")
        except Exception as e:
            _cprint(f"  Clipboard copy failed: {e}")

    def _handle_image_command(self, cmd_original: str):
        """Handle /image <path> — attach a local image file for the next prompt."""
        from cli import _DIM, _IMAGE_EXTENSIONS, _RST, _cprint, _resolve_attachment_path, _split_path_input, _termux_example_image_path
        raw_args = (cmd_original.split(None, 1)[1].strip() if " " in cmd_original else "")
        if not raw_args:
            hint = _termux_example_image_path() if _is_termux_environment() else "/path/to/image.png"
            _cprint(f"  {_DIM}Usage: /image <path>  e.g. /image {hint}{_RST}")
            return

        path_token, _remainder = _split_path_input(raw_args)
        image_path = _resolve_attachment_path(path_token)
        if image_path is None:
            _cprint(f"  {_DIM}(>_<) File not found: {path_token}{_RST}")
            return
        if image_path.suffix.lower() not in _IMAGE_EXTENSIONS:
            _cprint(f"  {_DIM}(._.) Not a supported image file: {image_path.name}{_RST}")
            return

        self._attached_images.append(image_path)
        _cprint(f"  📎 Attached image: {image_path.name}")
        if _remainder:
            _cprint(f"  {_DIM}Now type your prompt (or use --image in single-query mode): {_remainder}{_RST}")
        elif _is_termux_environment():
            _cprint(f"  {_DIM}Tip: type your next message, or run aetheros chat -q --image {_termux_example_image_path(image_path.name)} \"What do you see?\"{_RST}")

    # --- Multimodal Media Commands (Phase 92) ---

    def _handle_media_command(self, cmd_original: str):
        """Handle /media <subcommand> [args...] — multimodal media operations."""
        from cli import _ACCENT, _DIM, _RST, _cprint
        import shlex

        try:
            parts = shlex.split(cmd_original)
        except ValueError:
            parts = cmd_original.split()

        if len(parts) < 2:
            _cprint(f"  {_DIM}Usage: /media <subcommand> [args...]{_RST}")
            _cprint(f"  Subcommands: inspect, analyze, transcribe, ocr, search, info, ingest, convert, export")
            return

        subcommand = parts[1].lower()
        args = parts[2:]

        try:
            from agent.multimodal.api import (
                media_ingest, media_inspect, media_analyze, media_ocr,
                media_transcribe, media_search, media_convert, media_export,
                new_trackers,
            )
            from agent.multimodal.media_abstraction import MediaObject, SensitivityLevel
        except ImportError as e:
            _cprint(f"  {_DIM}Multimodal module not available: {e}{_RST}")
            return

        trackers = new_trackers()

        if subcommand == "ingest":
            if not args:
                _cprint(f"  {_DIM}Usage: /media ingest <path|url> [sensitivity] [metadata_json]{_RST}")
                return
            path = args[0]
            sens = SensitivityLevel(args[1]) if len(args) > 1 else SensitivityLevel.PRIVATE
            metadata = {}
            if len(args) > 2:
                import json
                try:
                    metadata = json.loads(args[2])
                except json.JSONDecodeError:
                    _cprint(f"  {_DIM}Invalid metadata JSON{_RST}")
                    return
            result = media_ingest(path, sensitivity=sens.value, metadata=metadata)
            if result.get("success"):
                _cprint(f"  {_ACCENT}Ingested:{_RST} {result['media']['media_id']} ({result['media']['type']})")
            else:
                _cprint(f"  {_DIM}Ingest failed: {result.get('error')}{_RST}")

        elif subcommand == "inspect":
            if not args:
                _cprint(f"  {_DIM}Usage: /media inspect <path|url> [sensitivity]{_RST}")
                return
            path = args[0]
            sens = SensitivityLevel(args[1]) if len(args) > 1 else SensitivityLevel.PRIVATE
            media = media_ingest(path, sensitivity=sens.value)
            if media.get("success"):
                result = media_inspect(media["media"])
                if result.get("success"):
                    m = result
                    _cprint(f"  {_ACCENT}Media Info:{_RST}")
                    _cprint(f"    ID: {m.get('media_id')}")
                    _cprint(f"    Type: {m.get('type')}")
                    _cprint(f"    MIME: {m.get('mime_type')}")
                    _cprint(f"    Size: {m.get('size')} bytes")
                    _cprint(f"    Dimensions: {m.get('dimensions')}")
                    _cprint(f"    Duration: {m.get('duration')}s")
                    _cprint(f"    Sensitivity: {m.get('sensitivity')}")
                    _cprint(f"    Processing Target: {m.get('processing_target')}")
                    _cprint(f"    Privacy Reason: {m.get('privacy_reason')}")
                else:
                    _cprint(f"  {_DIM}Inspect failed: {result.get('error')}{_RST}")
            else:
                _cprint(f"  {_DIM}Ingest failed: {media.get('error')}{_RST}")

        elif subcommand == "analyze":
            if len(args) < 2:
                _cprint(f"  {_DIM}Usage: /media analyze <path|url> <question> [sensitivity]{_RST}")
                return
            path = args[0]
            question = " ".join(args[1:-1]) if len(args) > 2 else args[1]
            sens = SensitivityLevel(args[-1]) if len(args) > 2 else SensitivityLevel.PRIVATE
            media = media_ingest(path, sensitivity=sens.value)
            if media.get("success"):
                result = media_analyze(media["media"], question, trackers)
                if result.get("success"):
                    _cprint(f"  {_ACCENT}Analysis:{_RST}")
                    _cprint(f"    {result.get('analysis', 'No analysis')}")
                    _cprint(f"    {_DIM}Confidence: {result.get('confidence', 0):.2f}{_RST}")
                else:
                    _cprint(f"  {_DIM}Analyze failed: {result.get('error')}{_RST}")
            else:
                _cprint(f"  {_DIM}Ingest failed: {media.get('error')}{_RST}")

        elif subcommand == "ocr":
            if not args:
                _cprint(f"  {_DIM}Usage: /media ocr <path|url> [language]{_RST}")
                return
            path = args[0]
            lang = args[1] if len(args) > 1 else None
            media = media_ingest(path)
            if media.get("success"):
                result = media_ocr(media["media"], language=lang, trackers=trackers)
                if result.get("success"):
                    _cprint(f"  {_ACCENT}OCR Result:{_RST}")
                    _cprint(f"    Text: {result.get('text', '')[:500]}")
                    _cprint(f"    {_DIM}Confidence: {result.get('confidence', 0):.2f}{_RST}")
                    _cprint(f"    Provider: {result.get('provider', 'unknown')}")
                else:
                    _cprint(f"  {_DIM}OCR failed: {result.get('error')}{_RST}")
            else:
                _cprint(f"  {_DIM}Ingest failed: {media.get('error')}{_RST}")

        elif subcommand == "transcribe":
            if not args:
                _cprint(f"  {_DIM}Usage: /media transcribe <path|url> [model]{_RST}")
                return
            path = args[0]
            media = media_ingest(path)
            if media.get("success"):
                result = media_transcribe(media["media"], trackers=trackers)
                if result.get("success"):
                    _cprint(f"  {_ACCENT}Transcript:{_RST}")
                    _cprint(f"    {result.get('transcript', '')}")
                    _cprint(f"    {_DIM}Provider: {result.get('provider', 'unknown')}")
                    _cprint(f"    {_DIM}Confidence: {result.get('confidence', 0):.2f}{_RST}")
                else:
                    _cprint(f"  {_DIM}Transcribe failed: {result.get('error')}{_RST}")
            else:
                _cprint(f"  {_DIM}Ingest failed: {media.get('error')}{_RST}")

        elif subcommand == "search":
            if not args:
                _cprint(f"  {_DIM}Usage: /media search <query> [limit] [kinds_json]{_RST}")
                return
            query = args[0]
            limit = int(args[1]) if len(args) > 1 else 10
            kinds = None
            if len(args) > 2:
                import json
                try:
                    kinds = json.loads(args[2])
                except json.JSONDecodeError:
                    _cprint(f"  {_DIM}Invalid kinds JSON{_RST}")
                    return
            result = media_search(query, limit=limit, kinds=kinds)
            if result.get("success"):
                _cprint(f"  {_ACCENT}Search Results ({result.get('count', 0)}):{_RST}")
                for r in result.get("results", [])[:5]:
                    _cprint(f"    - {r.get('kind')}: {r.get('content', '')[:80]}")
            else:
                _cprint(f"  {_DIM}Search failed: {result.get('error')}{_RST}")

        elif subcommand == "info":
            if not args:
                _cprint(f"  {_DIM}Usage: /media info <media_id>{_RST}")
                return
            media_id = args[0]
            # This would require a media store lookup - placeholder
            _cprint(f"  {_DIM}Media info lookup not yet implemented for ID: {media_id}{_RST}")

        elif subcommand == "convert":
            if len(args) < 2:
                _cprint(f"  {_DIM}Usage: /media convert <path> <format> [output_path]{_RST}")
                return
            path = args[0]
            fmt = args[1]
            out = args[2] if len(args) > 2 else None
            media = media_ingest(path)
            if media.get("success"):
                result = media_convert(media["media"], fmt, out)
                if result.get("success"):
                    _cprint(f"  {_ACCENT}Converted:{_RST} {result.get('output_path')}")
                else:
                    _cprint(f"  {_DIM}Convert failed: {result.get('error')}{_RST}")
            else:
                _cprint(f"  {_DIM}Ingest failed: {media.get('error')}{_RST}")

        elif subcommand == "export":
            if len(args) < 2:
                _cprint(f"  {_DIM}Usage: /media export <path> <format> [output_path]{_RST}")
                return
            path = args[0]
            fmt = args[1]
            out = args[2] if len(args) > 2 else None
            media = media_ingest(path)
            if media.get("success"):
                result = media_export(media["media"], out or f"{path}.{fmt}", fmt)
                if result.get("success"):
                    _cprint(f"  {_ACCENT}Exported:{_RST} {result.get('output_path')}")
                else:
                    _cprint(f"  {_DIM}Export failed: {result.get('error')}{_RST}")
            else:
                _cprint(f"  {_DIM}Ingest failed: {media.get('error')}{_RST}")

        else:
            _cprint(f"  {_DIM}Unknown media subcommand: {subcommand}{_RST}")
            _cprint(f"  Available: inspect, analyze, transcribe, ocr, search, info, ingest, convert, export")

    def _handle_audio_command(self, cmd_original: str):
        """Handle /audio <subcommand> [args...] — audio operations."""
        from cli import _ACCENT, _DIM, _RST, _cprint
        import shlex

        try:
            parts = shlex.split(cmd_original)
        except ValueError:
            parts = cmd_original.split()

        if len(parts) < 2:
            _cprint(f"  {_DIM}Usage: /audio <subcommand> [args...]{_RST}")
            _cprint(f"  Subcommands: record, play, transcribe, synthesize, devices")
            return

        subcommand = parts[1].lower()
        args = parts[2:]

        if subcommand == "record":
            duration = int(args[0]) if args else 5
            _cprint(f"  {_DIM}Audio recording for {duration}s... (not yet implemented){_RST}")
        elif subcommand == "play":
            if not args:
                _cprint(f"  {_DIM}Usage: /audio play <path>{_RST}")
                return
            _cprint(f"  {_DIM}Playing {args[0]}... (not yet implemented){_RST}")
        elif subcommand == "transcribe":
            if not args:
                _cprint(f"  {_DIM}Usage: /audio transcribe <path> [model]{_RST}")
                return
            _cprint(f"  {_DIM}Use /media transcribe for transcription{_RST}")
        elif subcommand == "synthesize":
            if not args:
                _cprint(f"  {_DIM}Usage: /audio synthesize <text> [voice] [output]{_RST}")
                return
            _cprint(f"  {_DIM}TTS synthesis... (not yet implemented){_RST}")
        elif subcommand == "devices":
            _cprint(f"  {_DIM}Audio devices: (not yet implemented){_RST}")
        else:
            _cprint(f"  {_DIM}Unknown audio subcommand: {subcommand}{_RST}")

    def _handle_video_command(self, cmd_original: str):
        """Handle /video <subcommand> [args...] — video operations."""
        from cli import _ACCENT, _DIM, _RST, _cprint
        import shlex

        try:
            parts = shlex.split(cmd_original)
        except ValueError:
            parts = cmd_original.split()

        if len(parts) < 2:
            _cprint(f"  {_DIM}Usage: /video <subcommand> [args...]{_RST}")
            _cprint(f"  Subcommands: capture, analyze, frames, stream")
            return

        subcommand = parts[1].lower()
        args = parts[2:]

        if subcommand == "capture":
            _cprint(f"  {_DIM}Video capture... (not yet implemented){_RST}")
        elif subcommand == "analyze":
            if not args:
                _cprint(f"  {_DIM}Usage: /video analyze <path> <question>{_RST}")
                return
            _cprint(f"  {_DIM}Use /media analyze for video analysis{_RST}")
        elif subcommand == "frames":
            if not args:
                _cprint(f"  {_DIM}Usage: /video frames <path> [max_frames] [mode]{_RST}")
                return
            _cprint(f"  {_DIM}Frame extraction... (not yet implemented){_RST}")
        elif subcommand == "stream":
            _cprint(f"  {_DIM}Video streaming... (not yet implemented){_RST}")
        else:
            _cprint(f"  {_DIM}Unknown video subcommand: {subcommand}{_RST}")

    def _handle_screen_command(self, cmd_original: str):
        """Handle /screen <subcommand> [args...] — screen operations."""
        from cli import _ACCENT, _DIM, _RST, _cprint
        import shlex

        try:
            parts = shlex.split(cmd_original)
        except ValueError:
            parts = cmd_original.split()

        if len(parts) < 2:
            _cprint(f"  {_DIM}Usage: /screen <subcommand> [args...]{_RST}")
            _cprint(f"  Subcommands: capture, understand, record, monitor")
            return

        subcommand = parts[1].lower()
        args = parts[2:]

        if subcommand == "capture":
            mode = args[0] if args else "full_screen"
            _cprint(f"  {_DIM}Screen capture ({mode})... (not yet implemented){_RST}")
        elif subcommand == "understand":
            if not args:
                _cprint(f"  {_DIM}Usage: /screen understand <path> [question]{_RST}")
                return
            _cprint(f"  {_DIM}Use /media analyze for screen understanding{_RST}")
        elif subcommand == "record":
            _cprint(f"  {_DIM}Screen recording... (not yet implemented){_RST}")
        elif subcommand == "monitor":
            _cprint(f"  {_DIM}Screen monitoring... (not yet implemented){_RST}")
        else:
            _cprint(f"  {_DIM}Unknown screen subcommand: {subcommand}{_RST}")

    def _handle_camera_command(self, cmd_original: str):
        """Handle /camera <subcommand> [args...] — camera operations."""
        from cli import _ACCENT, _DIM, _RST, _cprint
        import shlex

        try:
            parts = shlex.split(cmd_original)
        except ValueError:
            parts = cmd_original.split()

        if len(parts) < 2:
            _cprint(f"  {_DIM}Usage: /camera <subcommand> [args...]{_RST}")
            _cprint(f"  Subcommands: capture, understand, stream")
            return

        subcommand = parts[1].lower()
        args = parts[2:]

        if subcommand == "capture":
            mode = args[0] if args else "still"
            _cprint(f"  {_DIM}Camera capture ({mode})... (not yet implemented){_RST}")
        elif subcommand == "understand":
            if not args:
                _cprint(f"  {_DIM}Usage: /camera understand <path> [question]{_RST}")
                return
            _cprint(f"  {_DIM}Use /media analyze for camera understanding{_RST}")
        elif subcommand == "stream":
            _cprint(f"  {_DIM}Camera streaming... (not yet implemented){_RST}")
        else:
            _cprint(f"  {_DIM}Unknown camera subcommand: {subcommand}{_RST}")

    def _handle_document_command(self, cmd_original: str):
        """Handle /document <subcommand> [args...] — document operations."""
        from cli import _ACCENT, _DIM, _RST, _cprint
        import shlex

        try:
            parts = shlex.split(cmd_original)
        except ValueError:
            parts = cmd_original.split()

        if len(parts) < 2:
            _cprint(f"  {_DIM}Usage: /document <subcommand> [args...]{_RST}")
            _cprint(f"  Subcommands: extract, ocr, analyze")
            return

        subcommand = parts[1].lower()
        args = parts[2:]

        if subcommand == "extract":
            if not args:
                _cprint(f"  {_DIM}Usage: /document extract <path>{_RST}")
                return
            _cprint(f"  {_DIM}Use /media analyze for document extraction{_RST}")
        elif subcommand == "ocr":
            if not args:
                _cprint(f"  {_DIM}Usage: /document ocr <path> [language]{_RST}")
                return
            _cprint(f"  {_DIM}Use /media ocr for document OCR{_RST}")
        elif subcommand == "analyze":
            if len(args) < 2:
                _cprint(f"  {_DIM}Usage: /document analyze <path> <question>{_RST}")
                return
            _cprint(f"  {_DIM}Use /media analyze for document analysis{_RST}")
        else:
            _cprint(f"  {_DIM}Unknown document subcommand: {subcommand}{_RST}")

    def _handle_ocr_command(self, cmd_original: str):
        """Handle /ocr <path> [language] — extract text from image/document."""
        from cli import _ACCENT, _DIM, _RST, _cprint, _resolve_attachment_path
        import shlex

        try:
            parts = shlex.split(cmd_original)
        except ValueError:
            parts = cmd_original.split()

        if len(parts) < 2:
            _cprint(f"  {_DIM}Usage: /ocr <path> [language]{_RST}")
            return

        path = parts[1]
        lang = parts[2] if len(parts) > 2 else None

        _cprint(f"  {_DIM}Use /media ocr for OCR{_RST}")

    def _handle_describe_command(self, cmd_original: str):
        """Handle /describe <path> [question] — describe image/screen/document."""
        from cli import _ACCENT, _DIM, _RST, _cprint
        import shlex

        try:
            parts = shlex.split(cmd_original)
        except ValueError:
            parts = cmd_original.split()

        if len(parts) < 2:
            _cprint(f"  {_DIM}Usage: /describe <path> [question]{_RST}")
            return

        path = parts[1]
        question = " ".join(parts[2:]) if len(parts) > 2 else "Describe this in detail."

        _cprint(f"  {_DIM}Use /media analyze for description{_RST}")
        """Handle /tools [list|disable|enable] slash commands.

        /tools (no args) shows the tool list.
        /tools list shows enabled/disabled status per toolset.
        /tools disable/enable saves the change to config and resets
        the session so the new tool set takes effect cleanly (no
        prompt-cache breakage mid-conversation).
        """
        from cli import _ACCENT, _DIM, _RST, _cprint
        import shlex
        from argparse import Namespace
        from contextlib import redirect_stdout
        from io import StringIO
        from aetheros_cli.tools_config import tools_disable_enable_command

        def _run_capture(ns: Namespace) -> None:
            """Run tools_disable_enable_command, routing its ANSI-colored
            print() output through _cprint when inside the interactive TUI
            so escapes aren't mangled by patch_stdout's StdoutProxy into
            garbled '?[32m...?[0m' text.

            Outside the TUI (standalone mode, tests), call straight through
            so real stdout / pytest capture works as expected.
            """
            # Standalone/tests, run as usual
            if getattr(self, "_app", None) is None:
                tools_disable_enable_command(ns)
                return

            # Buffer reports isatty()=True so color() in aetheros_cli/colors.py
            # still emits ANSI escapes. StringIO.isatty() is False, which
            # would otherwise strip all colors before we re-render them.
            class _TTYBuf(StringIO):
                def isatty(self) -> bool:
                    return True

            buf = _TTYBuf()
            with redirect_stdout(buf):
                tools_disable_enable_command(ns)
            for line in buf.getvalue().splitlines():
                _cprint(line)

        try:
            parts = shlex.split(cmd)
        except ValueError:
            parts = cmd.split()

        subcommand = parts[1] if len(parts) > 1 else ""
        if subcommand not in {"list", "disable", "enable"}:
            self.show_tools()
            return

        if subcommand == "list":
            _run_capture(Namespace(tools_action="list", platform="cli"))
            return

        names = parts[2:]
        if not names:
            print(f"(._.) Usage: /tools {subcommand} <name> [name ...]")
            print(f"  Built-in toolset:  /tools {subcommand} web")
            print(f"  MCP tool:          /tools {subcommand} github:create_issue")
            return

        # Apply the change directly — the user typing the command is implicit
        # consent.  Do NOT use input() here; it hangs inside prompt_toolkit's
        # TUI event loop (known pitfall).
        verb = "Disabling" if subcommand == "disable" else "Enabling"
        label = ", ".join(names)
        _cprint(f"{_ACCENT}{verb} {label}...{_RST}")

        _run_capture(Namespace(tools_action=subcommand, names=names, platform="cli"))

        # Reset session so the new tool config is picked up from a clean state
        from aetheros_cli.tools_config import _get_platform_tools
        from aetheros_cli.config import load_config
        self.enabled_toolsets = _get_platform_tools(load_config(), "cli")
        self.new_session()
        _cprint(f"{_DIM}Session reset. New tool configuration is active.{_RST}")

    def _handle_profile_command(self):
        """Display active profile name and home directory."""
        from aetheros_constants import display_aetheros_home
        from aetheros_cli.profiles import get_active_profile_name

        display = display_aetheros_home()
        profile_name = get_active_profile_name()

        print()
        print(f"  Profile: {profile_name}")
        print(f"  Home:    {display}")
        print()

    def _handle_handoff_command(self, cmd_original: str) -> bool:
        """Handle ``/handoff <platform>`` — transfer this CLI session to a gateway platform.

        Flow:
          1. Validate platform name + the gateway has a home channel for it.
          2. Reject if the agent is currently running (the in-flight turn
             would race with the gateway's switch_session).
          3. Write ``handoff_state='pending'`` on this session row.
          4. Block-poll ``state.db`` for terminal state (timeout 60s).
          5. On ``completed`` → print resume hint and signal CLI exit by
             returning False (the caller honors that like ``/quit``).
          6. On ``failed`` / timeout → print error and return True so the
             user keeps their CLI session.

        Returns:
            False to signal CLI exit, True to keep going.
        """
        from cli import _cprint
        from aetheros_state import format_session_db_unavailable

        parts = cmd_original.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            _cprint("  Usage: /handoff <platform>")
            _cprint("  Hands the current session off to that platform's home channel.")
            _cprint("  The CLI session ends here; resume it later with /resume.")
            return True

        platform_name = parts[1].strip().lower()

        # Validate platform name + home channel via the live gateway config.
        try:
            from gateway.config import load_gateway_config, Platform
        except Exception as exc:  # pragma: no cover — gateway pkg always shipped
            _cprint(f"  Could not load gateway config: {exc}")
            return True

        try:
            platform = Platform(platform_name)
        except (ValueError, KeyError):
            _cprint(f"  Unknown platform '{platform_name}'.")
            return True

        try:
            gw_config = load_gateway_config()
        except Exception as exc:
            _cprint(f"  Could not load gateway config: {exc}")
            return True

        pcfg = gw_config.platforms.get(platform)
        if not pcfg or not pcfg.enabled:
            _cprint(f"  Platform '{platform_name}' is not configured/enabled in the gateway.")
            return True

        home = gw_config.get_home_channel(platform)
        if not home or not home.chat_id:
            _cprint(f"  No home channel configured for {platform_name}.")
            _cprint(f"  Set one with /sethome on the destination chat first.")
            return True

        # Refuse mid-turn: an in-flight agent run would race with the
        # gateway's switch_session and the synthetic turn dispatch.
        if getattr(self, "_agent_running", False):
            _cprint("  Agent is busy. Wait for the current turn to finish, then retry /handoff.")
            return True

        # Make sure we have a SessionDB handle.
        if not self._session_db:
            try:
                from aetheros_state import SessionDB
                self._session_db = SessionDB()
            except Exception:
                pass
        if not self._session_db:
            _cprint(f"  {format_session_db_unavailable()}")
            return True

        # Make sure the session row exists in state.db. Most CLI sessions
        # are written via _flush_messages_to_session_db on the first turn
        # already, but if the user tries to hand off an empty session we
        # still want a row to mark.
        try:
            row = self._session_db.get_session(self.session_id)
            if not row:
                # Nothing has flushed yet. Create a stub so the gateway has
                # something to switch_session onto. Inserting via title-set
                # is the simplest path because set_session_title's INSERT OR
                # IGNORE creates the row.
                placeholder_title = f"handoff-{self.session_id[:8]}"
                self._session_db.set_session_title(self.session_id, placeholder_title)
        except Exception as exc:
            _cprint(f"  Could not ensure session row in state.db: {exc}")
            return True

        # Display title for messaging.
        session_title = ""
        try:
            row = self._session_db.get_session(self.session_id)
            if row:
                session_title = row.get("title") or ""
        except Exception:
            pass
        if not session_title:
            session_title = self.session_id[:8]

        # Mark pending — gateway watcher will pick this up.
        ok = self._session_db.request_handoff(self.session_id, platform_name)
        if not ok:
            _cprint("  Session is already in flight for handoff. Wait for it to settle, then retry.")
            return True

        _cprint(f"  Queued handoff of '{session_title}' → {platform_name} (home: {home.name}).")
        _cprint(f"  Waiting for the gateway to pick it up...")

        # Poll-block on terminal state. Tick every 0.5s; bail at ~60s.
        import time as _time
        deadline = _time.time() + 60.0
        last_state = "pending"
        while _time.time() < deadline:
            try:
                state_row = self._session_db.get_handoff_state(self.session_id)
            except Exception:
                state_row = None
            current = (state_row or {}).get("state") or "pending"
            if current != last_state:
                if current == "running":
                    _cprint("  Gateway picked it up; transferring...")
                last_state = current
            if current == "completed":
                _cprint("")
                _cprint(f"  ↻ Handoff complete. The session is now active on {platform_name}.")
                _cprint(f"  Resume it on this CLI later with: /resume {session_title}")
                _cprint("")
                # End the CLI cleanly — same exit semantics as /quit.
                self._should_exit = True
                return False
            if current == "failed":
                err = (state_row or {}).get("error") or "unknown error"
                _cprint(f"  Handoff failed: {err}")
                _cprint("  Your CLI session is intact. Try /handoff again, or /resume on the platform manually.")
                return True
            _time.sleep(0.5)

        # Timed out. Clear the pending flag so the user can retry.
        try:
            self._session_db.fail_handoff(self.session_id, "timed out waiting for gateway")
        except Exception:
            pass
        _cprint("  Timed out waiting for the gateway. Is `aetheros gateway` running?")
        _cprint("  Your CLI session is intact.")
        return True

    def _handle_resume_command(self, cmd_original: str) -> None:
        """Handle /resume <session_id_or_title> — switch to a previous session mid-conversation."""
        from cli import _cprint, _sync_process_session_id
        parts = cmd_original.split(None, 1)
        target = parts[1].strip() if len(parts) > 1 else ""

        # Strip common outer brackets/quotes users may type literally from the
        # usage hint (e.g. ``/resume <abc123>`` or ``/resume [abc123]``).  The
        # `/resume` help text shows angle brackets as a placeholder and a few
        # users copy them through verbatim.  Stripping them keeps the lookup
        # working without changing the help string.
        if len(target) >= 2 and (
            (target[0] == "<" and target[-1] == ">")
            or (target[0] == "[" and target[-1] == "]")
            or (target[0] == '"' and target[-1] == '"')
            or (target[0] == "'" and target[-1] == "'")
        ):
            target = target[1:-1].strip()

        if not target:
            _cprint("  Usage: /resume <number|session_id_or_title>")
            if self._show_recent_sessions(reason="resume"):
                # Arm a one-shot pending-resume selection so the user can type
                # just the number (`3`) on the next line instead of having to
                # retype `/resume 3`. The list here must match the one shown by
                # _show_recent_sessions and used for index resolution below —
                # all three go through _list_recent_sessions(limit=10). See
                # #34584.
                self._pending_resume_sessions = self._list_recent_sessions(limit=10)
                return
            _cprint("  Tip:   Use /history or `aetheros sessions list` to find sessions.")
            return

        # Any explicit /resume <target> supersedes a previously-armed bare
        # numbered prompt.
        self._pending_resume_sessions = None

        if not self._session_db:
            from aetheros_state import format_session_db_unavailable
            _cprint(f"  {format_session_db_unavailable()}")
            return

        # Resolve numbered selection, title, or ID
        if target.isdigit():
            sessions = self._list_recent_sessions(limit=10)
            index = int(target)
            if index < 1 or index > len(sessions):
                _cprint(f"  Resume index {index} is out of range.")
                _cprint("  Use /resume with no arguments to see available sessions.")
                return
            selected = sessions[index - 1]
            target_id = selected["id"]
        else:
            from aetheros_cli.main import _resolve_session_by_name_or_id
            resolved = _resolve_session_by_name_or_id(target)
            target_id = resolved or target

        session_meta = self._session_db.get_session(target_id)
        if not session_meta:
            _cprint(f"  Session not found: {target}")
            _cprint("  Use /history or `aetheros sessions list` to see available sessions.")
            return

        # If the target is the empty head of a compression chain, redirect to
        # the descendant that actually holds the transcript. See #15000.
        try:
            resolved_id = self._session_db.resolve_resume_session_id(target_id)
        except Exception:
            resolved_id = target_id
        if resolved_id and resolved_id != target_id:
            _cprint(
                f"  Session {target_id} was compressed into {resolved_id}; "
                f"resuming the descendant with your transcript."
            )
            target_id = resolved_id
            resolved_meta = self._session_db.get_session(target_id)
            if resolved_meta:
                session_meta = resolved_meta

        if target_id == self.session_id:
            _cprint("  Already on that session.")
            return

        old_session_id = self.session_id
        # End current session
        try:
            self._session_db.end_session(self.session_id, "resumed_other")
        except Exception:
            pass

        # Switch to the target session
        self.session_id = target_id
        self._resumed = True
        self._pending_title = None
        _sync_process_session_id(target_id)

        # Load conversation history (strip transcript-only metadata entries)
        restored = self._session_db.get_messages_as_conversation(target_id)
        restored = [m for m in (restored or []) if m.get("role") != "session_meta"]
        self.conversation_history = restored

        # Re-open the target session so it's not marked as ended
        try:
            self._session_db.reopen_session(target_id)
        except Exception:
            pass

        # Sync the agent if already initialised
        if self.agent:
            self.agent.session_id = target_id
            self.agent.reset_session_state()
            if hasattr(self.agent, "_last_flushed_db_idx"):
                self.agent._last_flushed_db_idx = len(self.conversation_history)
            if hasattr(self.agent, "_todo_store"):
                try:
                    from tools.todo_tool import TodoStore
                    self.agent._todo_store = TodoStore()
                except Exception:
                    pass
            if hasattr(self.agent, "_invalidate_system_prompt"):
                self.agent._invalidate_system_prompt()

            # Notify memory providers that session_id rotated to a resumed
            # session. reset=False — the provider's accumulated state is
            # still valid; it just needs to target the new session_id for
            # subsequent writes. See #6672.
            try:
                _mm = getattr(self.agent, "_memory_manager", None)
                if _mm is not None:
                    _mm.on_session_switch(
                        target_id,
                        parent_session_id=old_session_id or "",
                        reset=False,
                        reason="resume",
                    )
            except Exception:
                pass

        title_part = f" \"{session_meta['title']}\"" if session_meta.get("title") else ""
        msg_count = len([m for m in self.conversation_history if m.get("role") == "user"])
        if self.conversation_history:
            _cprint(
                f"  ↻ Resumed session {target_id}{title_part}"
                f" ({msg_count} user message{'s' if msg_count != 1 else ''},"
                f" {len(self.conversation_history)} total)"
            )
            self._display_resumed_history()
        else:
            _cprint(f"  ↻ Resumed session {target_id}{title_part} — no messages, starting fresh.")

    def _handle_sessions_command(self, cmd_original: str) -> None:
        """Handle /sessions [list|<id_or_title>] — browse or resume previous sessions.

        Without arguments, prints the same recent-sessions table that /resume
        shows when called without a target, and tells the user how to resume.
        With an explicit subcommand or target, delegates to the resume flow so
        ``/sessions <id>`` and ``/resume <id>`` behave identically.

        The TUI ships an interactive picker overlay for this command; the
        classic CLI prints an inline list because there is no equivalent
        overlay primitive here. Without this handler the canonical name
        ``sessions`` falls through ``process_command``'s elif chain and
        prints ``Unknown command: sessions`` even though the command is
        registered in the central COMMAND_REGISTRY.
        """
        from cli import _cprint
        parts = cmd_original.split(None, 1)
        arg = parts[1].strip() if len(parts) > 1 else ""
        sub = arg.lower()

        # Bare /sessions or /sessions list — show recent sessions inline.
        if not arg or sub in {"list", "ls", "browse"}:
            if not self._session_db:
                from aetheros_state import format_session_db_unavailable
                _cprint(f"  {format_session_db_unavailable()}")
                return
            if not self._show_recent_sessions(reason="sessions"):
                _cprint("  (._.) No previous sessions yet.")
            return

        # /sessions <id_or_title> behaves the same as /resume <id_or_title>.
        self._handle_resume_command(f"/resume {arg}")

    def _handle_branch_command(self, cmd_original: str) -> None:
        """Handle /branch [name] — fork the current session into a new independent copy.

        Copies the full conversation history to a new session so the user can
        explore a different approach without losing the original session state.
        Inspired by Claude Code's /branch command.
        """
        from cli import _cprint, _sync_process_session_id
        if not self.conversation_history:
            _cprint("  No conversation to branch — send a message first.")
            return

        if not self._session_db:
            from aetheros_state import format_session_db_unavailable
            _cprint(f"  {format_session_db_unavailable()}")
            return

        parts = cmd_original.split(None, 1)
        branch_name = parts[1].strip() if len(parts) > 1 else ""

        # Generate the new session ID
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        short_uuid = uuid.uuid4().hex[:6]
        new_session_id = f"{timestamp_str}_{short_uuid}"

        # Determine branch title
        if branch_name:
            branch_title = branch_name
        else:
            # Auto-generate from the current session title
            current_title = None
            if self._session_db:
                current_title = self._session_db.get_session_title(self.session_id)
            base = current_title or "branch"
            branch_title = self._session_db.get_next_title_in_lineage(base)

        # Save the current session's state before branching
        parent_session_id = self.session_id

        # End the old session
        try:
            self._session_db.end_session(self.session_id, "branched")
        except Exception:
            pass

        # Create the new session with parent link.
        # Persist a stable ``_branched_from`` marker in model_config so
        # list_sessions_rich() can keep the branch visible in /resume and
        # /sessions even after the parent is reopened and re-ended with a
        # different end_reason (e.g. tui_shutdown overwriting 'branched').
        try:
            self._session_db.create_session(
                session_id=new_session_id,
                source=os.environ.get("AETHEROS_SESSION_SOURCE", "cli"),
                model=self.model,
                model_config={
                    "max_iterations": self.max_turns,
                    "reasoning_config": self.reasoning_config,
                    "_branched_from": parent_session_id,
                },
                parent_session_id=parent_session_id,
            )
        except Exception as e:
            _cprint(f"  Failed to create branch session: {e}")
            return

        # Copy conversation history to the new session
        for msg in self.conversation_history:
            try:
                self._session_db.append_message(
                    session_id=new_session_id,
                    role=msg.get("role", "user"),
                    content=msg.get("content"),
                    tool_name=msg.get("tool_name") or msg.get("name"),
                    tool_calls=msg.get("tool_calls"),
                    tool_call_id=msg.get("tool_call_id"),
                    reasoning=msg.get("reasoning"),
                )
            except Exception:
                pass  # Best-effort copy

        # Set title on the branch
        try:
            self._session_db.set_session_title(new_session_id, branch_title)
        except Exception:
            pass

        # Switch to the new session
        self._transfer_session_yolo(self.session_id, new_session_id)
        self.session_id = new_session_id
        self.session_start = now
        self._pending_title = None
        self._resumed = True  # Prevents auto-title generation
        _sync_process_session_id(new_session_id)

        # Sync the agent
        if self.agent:
            self.agent.session_id = new_session_id
            self.agent.session_start = now
            self.agent.reset_session_state()
            if hasattr(self.agent, "_last_flushed_db_idx"):
                self.agent._last_flushed_db_idx = len(self.conversation_history)
            if hasattr(self.agent, "_todo_store"):
                try:
                    from tools.todo_tool import TodoStore
                    self.agent._todo_store = TodoStore()
                except Exception:
                    pass
            if hasattr(self.agent, "_invalidate_system_prompt"):
                self.agent._invalidate_system_prompt()

            # Notify memory providers that session_id forked to a new branch.
            # reset=False — the branched session carries the transcript
            # forward, so provider state tracks the lineage. parent_session_id
            # links the branch back to the original. See #6672.
            try:
                _mm = getattr(self.agent, "_memory_manager", None)
                if _mm is not None:
                    _mm.on_session_switch(
                        new_session_id,
                        parent_session_id=parent_session_id or "",
                        reset=False,
                        reason="branch",
                    )
            except Exception:
                pass

        msg_count = len([m for m in self.conversation_history if m.get("role") == "user"])
        _cprint(
            f"  ⑂ Branched session \"{branch_title}\""
            f" ({msg_count} user message{'s' if msg_count != 1 else ''})"
        )
        _cprint(f"  Original session: {parent_session_id}")
        _cprint(f"  Branch session:   {new_session_id}")

    def _handle_folder_command(self, cmd_original: str) -> None:
        """Handle /folder [list|<session> <folder>|clear] — organize sessions into folders.

        - ``/folder list`` — show all folders with per-folder session counts.
        - ``/folder <folder>`` — assign the current session to a folder.
        - ``/folder <session> <folder>`` — assign another session.
        - ``/folder clear [<session>]`` — remove the folder from a session.
        """
        from cli import _cprint
        if not self._session_db:
            from aetheros_state import format_session_db_unavailable
            _cprint(f"  {format_session_db_unavailable()}")
            return

        parts = cmd_original.split()
        sub = parts[1].lower() if len(parts) > 1 else ""

        # /folder list → show all folders.
        if sub in {"list", "ls"} or (sub in {"", "show"}):
            folders = self._session_db.list_folders()
            if not folders:
                _cprint("  No folders yet. Use /folder <name> to organize the current session.")
                return
            _cprint(f"  Folders ({len(folders)}):")
            for f in folders:
                _cprint(f"    {f['folder']}  ({f['session_count']} session{'s' if f['session_count'] != 1 else ''})")
            _cprint("  Use /folder <session> <folder> to assign, /folder <folder> for the current session.")
            return

        # /folder clear [<session>]
        if sub in {"clear", "remove", "rm", "none", "-"}:
            target = parts[2] if len(parts) > 2 else self.session_id
            if self._session_db.set_session_folder(target, None):
                _cprint(f"  Folder removed from session {target}.")
            else:
                _cprint(f"  Session not found: {target}")
            return

        # /folder <session> <folder> — two args: target session + folder name.
        if len(parts) >= 3:
            target, folder = parts[1], parts[2]
            if not self._session_db.get_session(target):
                _cprint(f"  Session not found: {target}")
                return
            try:
                if self._session_db.set_session_folder(target, folder):
                    _cprint(f"  Session {target} moved to folder \"{folder}\".")
                else:
                    _cprint(f"  Session not found: {target}")
            except ValueError as e:
                _cprint(f"  {e}")
            return

        # /folder <folder> — single arg assigns the current session.
        folder = parts[1]
        try:
            if self._session_db.set_session_folder(self.session_id, folder):
                _cprint(f"  Current session moved to folder \"{folder}\".")
            else:
                _cprint(f"  Session not found: {self.session_id}")
        except ValueError as e:
            _cprint(f"  {e}")

    def _handle_pin_command(self, cmd_original: str) -> None:
        """Handle /pin [on|off|<session> [on|off]] — pin/unpin a session.

        Pinned sessions float to the top of /resume and session listings.
        Defaults to the current session; ``on``/``off`` (or ``true``/``false``)
        controls the state, defaulting to on when omitted.
        """
        from cli import _cprint
        if not self._session_db:
            from aetheros_state import format_session_db_unavailable
            _cprint(f"  {format_session_db_unavailable()}")
            return

        parts = cmd_original.split()
        tokens = parts[1:] if len(parts) > 1 else []

        def _parse_state(token: str) -> Optional[bool]:
            t = token.lower()
            if t in {"on", "true", "1", "yes", "pin"}:
                return True
            if t in {"off", "false", "0", "no", "unpin"}:
                return False
            return None

        # /pin → show current state of the active session.
        if not tokens:
            state = self._session_db.is_session_pinned(self.session_id)
            _cprint(f"  Session {self.session_id} is {'pinned' if state else 'not pinned'}.")
            _cprint("  Use /pin on|off to change it, or /pin <session> [on|off] for another session.")
            return

        target = self.session_id
        state = _parse_state(tokens[0])
        if state is None:
            # First token is a session id/title, not a state word.
            target = tokens[0]
            state = _parse_state(tokens[1]) if len(tokens) > 1 else True
            if state is None:
                _cprint(f"  Unknown pin state: {tokens[1]}. Use on or off.")
                return
            session_meta = self._session_db.get_session(target)
            if not session_meta:
                session_meta = self._session_db.get_session_by_title(target)
            if not session_meta:
                _cprint(f"  Session not found: {target}")
                return
            target = session_meta["id"]

        if self._session_db.set_session_pinned(target, state):
            _cprint(f"  Session {target} {'pinned' if state else 'unpinned'}.")
        else:
            _cprint(f"  Session not found: {target}")

    def _handle_import_command(self, cmd_original: str) -> None:
        """Handle /import <file> [--folder name] — import a session from an exported JSON file.

        Accepts a single-session export (from ``/export`` or the web dashboard)
        or a JSONL list of exports. Sessions are imported as copies with fresh
        ids, so existing sessions are never overwritten. ``--folder`` assigns
        the imported session to a folder.
        """
        from cli import _cprint
        if not self._session_db:
            from aetheros_state import format_session_db_unavailable
            _cprint(f"  {format_session_db_unavailable()}")
            return

        parts = cmd_original.split()
        tokens = parts[1:] if len(parts) > 1 else []
        folder = None
        file_args = []
        i = 0
        while i < len(tokens):
            if tokens[i] == "--folder" and i + 1 < len(tokens):
                folder = tokens[i + 1]
                i += 2
            else:
                file_args.append(tokens[i])
                i += 1

        if not file_args:
            _cprint("  Usage: /import <file.json|file.jsonl> [--folder <name>]")
            return

        path = Path(file_args[0])
        if not path.is_file():
            _cprint(f"  File not found: {file_args[0]}")
            return

        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as e:
            _cprint(f"  Could not read {path}: {e}")
            return

        import json as _json
        try:
            if file_args[0].lower().endswith(".jsonl"):
                data = [_json.loads(line) for line in raw.splitlines() if line.strip()]
            else:
                parsed = _json.loads(raw)
                data = parsed if isinstance(parsed, list) else [parsed]
        except _json.JSONDecodeError as e:
            _cprint(f"  Invalid JSON in {path}: {e}")
            return

        imported_ids = []
        for entry in data:
            try:
                new_id = self._session_db.import_session(
                    entry,
                    new_id=True,
                    folder=folder,
                )
            except ValueError as e:
                _cprint(f"  Import failed for one entry: {e}")
                continue
            if new_id:
                imported_ids.append(new_id)

        if not imported_ids:
            _cprint("  Nothing imported — no usable sessions found in the file.")
            return

        if len(imported_ids) == 1:
            _cprint(f"  Imported session {imported_ids[0]}.")
            if folder:
                _cprint(f"  Folder: {folder}")
            _cprint("  Use /resume " + imported_ids[0] + " to open it.")
        else:
            _cprint(f"  Imported {len(imported_ids)} sessions:")
            for sid in imported_ids:
                _cprint(f"    {sid}")

    def _handle_gquota_command(self, cmd_original: str) -> None:
        """Show Google Gemini Code Assist quota usage for the current OAuth account."""
        try:
            from agent.google_oauth import get_valid_access_token, GoogleOAuthError, load_credentials
            from agent.google_code_assist import retrieve_user_quota, CodeAssistError
        except ImportError as exc:
            self._console_print(f"  [red]Gemini modules unavailable: {exc}[/]")
            return

        try:
            access_token = get_valid_access_token()
        except GoogleOAuthError as exc:
            self._console_print(f"  [yellow]{exc}[/]")
            self._console_print("  Run [bold]/model[/] and pick 'Google Gemini (OAuth)' to sign in.")
            return

        creds = load_credentials()
        project_id = (creds.project_id if creds else "") or ""

        try:
            buckets = retrieve_user_quota(access_token, project_id=project_id)
        except CodeAssistError as exc:
            self._console_print(f"  [red]Quota lookup failed:[/] {exc}")
            return

        if not buckets:
            self._console_print("  [dim]No quota buckets reported (account may be on legacy/unmetered tier).[/]")
            return

        # Sort for stable display, group by model
        buckets.sort(key=lambda b: (b.model_id, b.token_type))
        self._console_print()
        self._console_print(f"  [bold]Gemini Code Assist quota[/]  (project: {project_id or '(auto / free-tier)'})")
        self._console_print()
        for b in buckets:
            pct = max(0.0, min(1.0, b.remaining_fraction))
            width = 20
            filled = int(round(pct * width))
            bar = "▓" * filled + "░" * (width - filled)
            pct_str = f"{int(pct * 100):3d}%"
            header = b.model_id
            if b.token_type:
                header += f" [{b.token_type}]"
            self._console_print(f"    {header:40s}  {bar}  {pct_str}")
        self._console_print()

    def _handle_personality_command(self, cmd: str):
        """Handle the /personality command to set predefined personalities."""
        from cli import save_config_value
        parts = cmd.split(maxsplit=1)
        
        if len(parts) > 1:
            # Set personality
            personality_name = parts[1].strip().lower()
            
            if personality_name in {"none", "default", "neutral"}:
                self.system_prompt = ""
                self.agent = None  # Force re-init
                if save_config_value("agent.system_prompt", ""):
                    print("(^_^)b Personality cleared (saved to config)")
                else:
                    print("(^_^) Personality cleared (session only)")
                print("  No personality overlay — using base agent behavior.")
            elif personality_name in self.personalities:
                self.system_prompt = self._resolve_personality_prompt(self.personalities[personality_name])
                self.agent = None  # Force re-init
                if save_config_value("agent.system_prompt", self.system_prompt):
                    print(f"(^_^)b Personality set to '{personality_name}' (saved to config)")
                else:
                    print(f"(^_^) Personality set to '{personality_name}' (session only)")
                print(f"  \"{self.system_prompt[:60]}{'...' if len(self.system_prompt) > 60 else ''}\"")
            else:
                print(f"(._.) Unknown personality: {personality_name}")
                print(f"  Available: none, {', '.join(self.personalities.keys())}")
        else:
            # Show available personalities
            print()
            print("+" + "-" * 50 + "+")
            print("|" + " " * 12 + "(^o^)/ Personalities" + " " * 15 + "|")
            print("+" + "-" * 50 + "+")
            print()
            print(f"  {'none':<12} - (no personality overlay)")
            for name, prompt in self.personalities.items():
                if isinstance(prompt, dict):
                    preview = prompt.get("description") or prompt.get("system_prompt", "")[:50]
                else:
                    preview = str(prompt)[:50]
                print(f"  {name:<12} - {preview}")
            print()
            print("  Usage: /personality <name>")
            print()

    def _handle_cron_command(self, cmd: str):
        """Handle the /cron command to manage scheduled tasks."""
        from cli import get_job
        import shlex
        from tools.cronjob_tools import cronjob as cronjob_tool

        def _cron_api(**kwargs):
            return json.loads(cronjob_tool(**kwargs))

        def _normalize_skills(values):
            normalized = []
            for value in values:
                text = str(value or "").strip()
                if text and text not in normalized:
                    normalized.append(text)
            return normalized

        def _parse_flags(tokens):
            opts = {
                "name": None,
                "deliver": None,
                "repeat": None,
                "skills": [],
                "add_skills": [],
                "remove_skills": [],
                "clear_skills": False,
                "all": False,
                "prompt": None,
                "schedule": None,
                "positionals": [],
            }
            i = 0
            while i < len(tokens):
                token = tokens[i]
                if token == "--name" and i + 1 < len(tokens):
                    opts["name"] = tokens[i + 1]
                    i += 2
                elif token == "--deliver" and i + 1 < len(tokens):
                    opts["deliver"] = tokens[i + 1]
                    i += 2
                elif token == "--repeat" and i + 1 < len(tokens):
                    try:
                        opts["repeat"] = int(tokens[i + 1])
                    except ValueError:
                        print("(._.) --repeat must be an integer")
                        return None
                    i += 2
                elif token == "--skill" and i + 1 < len(tokens):
                    opts["skills"].append(tokens[i + 1])
                    i += 2
                elif token == "--add-skill" and i + 1 < len(tokens):
                    opts["add_skills"].append(tokens[i + 1])
                    i += 2
                elif token == "--remove-skill" and i + 1 < len(tokens):
                    opts["remove_skills"].append(tokens[i + 1])
                    i += 2
                elif token == "--clear-skills":
                    opts["clear_skills"] = True
                    i += 1
                elif token == "--all":
                    opts["all"] = True
                    i += 1
                elif token == "--prompt" and i + 1 < len(tokens):
                    opts["prompt"] = tokens[i + 1]
                    i += 2
                elif token == "--schedule" and i + 1 < len(tokens):
                    opts["schedule"] = tokens[i + 1]
                    i += 2
                else:
                    opts["positionals"].append(token)
                    i += 1
            return opts

        tokens = shlex.split(cmd)

        if len(tokens) == 1:
            print()
            print("+" + "-" * 68 + "+")
            print("|" + " " * 22 + "(^_^) Scheduled Tasks" + " " * 23 + "|")
            print("+" + "-" * 68 + "+")
            print()
            print("  Commands:")
            print("    /cron list")
            print('    /cron add "every 2h" "Check server status" [--skill blogwatcher]')
            print('    /cron edit <job_id> --schedule "every 4h" --prompt "New task"')
            print("    /cron edit <job_id> --skill blogwatcher --skill maps")
            print("    /cron edit <job_id> --remove-skill blogwatcher")
            print("    /cron edit <job_id> --clear-skills")
            print("    /cron pause <job_id>")
            print("    /cron resume <job_id>")
            print("    /cron run <job_id>")
            print("    /cron remove <job_id>")
            print()
            result = _cron_api(action="list")
            jobs = result.get("jobs", []) if result.get("success") else []
            if jobs:
                print("  Current Jobs:")
                print("  " + "-" * 63)
                for job in jobs:
                    repeat_str = job.get("repeat", "?")
                    print(f"    {job['job_id'][:12]:<12} | {job['schedule']:<15} | {repeat_str:<8}")
                    if job.get("skills"):
                        print(f"      Skills: {', '.join(job['skills'])}")
                    print(f"      {job.get('prompt_preview', '')}")
                    if job.get("next_run_at"):
                        print(f"      Next: {job['next_run_at']}")
                    print()
            else:
                print("  No scheduled jobs. Use '/cron add' to create one.")
            print()
            return

        subcommand = tokens[1].lower()
        opts = _parse_flags(tokens[2:])
        if opts is None:
            return

        if subcommand == "list":
            result = _cron_api(action="list", include_disabled=opts["all"])
            jobs = result.get("jobs", []) if result.get("success") else []
            if not jobs:
                print("(._.) No scheduled jobs.")
                return

            print()
            print("Scheduled Jobs:")
            print("-" * 80)
            for job in jobs:
                print(f"  ID: {job['job_id']}")
                print(f"  Name: {job['name']}")
                print(f"  State: {job.get('state', '?')}")
                print(f"  Schedule: {job['schedule']} ({job.get('repeat', '?')})")
                print(f"  Next run: {job.get('next_run_at', 'N/A')}")
                if job.get("skills"):
                    print(f"  Skills: {', '.join(job['skills'])}")
                print(f"  Prompt: {job.get('prompt_preview', '')}")
                if job.get("last_run_at"):
                    print(f"  Last run: {job['last_run_at']} ({job.get('last_status', '?')})")
                print()
            return

        if subcommand in {"add", "create"}:
            positionals = opts["positionals"]
            if not positionals:
                print("(._.) Usage: /cron add <schedule> <prompt>")
                return
            schedule = opts["schedule"] or positionals[0]
            prompt = opts["prompt"] or " ".join(positionals[1:])
            skills = _normalize_skills(opts["skills"])
            if not prompt and not skills:
                print("(._.) Please provide a prompt or at least one skill")
                return
            result = _cron_api(
                action="create",
                schedule=schedule,
                prompt=prompt or None,
                name=opts["name"],
                deliver=opts["deliver"],
                repeat=opts["repeat"],
                skills=skills or None,
            )
            if result.get("success"):
                print(f"(^_^)b Created job: {result['job_id']}")
                print(f"  Schedule: {result['schedule']}")
                if result.get("skills"):
                    print(f"  Skills: {', '.join(result['skills'])}")
                print(f"  Next run: {result['next_run_at']}")
            else:
                print(f"(x_x) Failed to create job: {result.get('error')}")
            return

        if subcommand == "edit":
            positionals = opts["positionals"]
            if not positionals:
                print("(._.) Usage: /cron edit <job_id> [--schedule ...] [--prompt ...] [--skill ...]")
                return
            job_id = positionals[0]
            existing = get_job(job_id)
            if not existing:
                print(f"(._.) Job not found: {job_id}")
                return

            final_skills = None
            replacement_skills = _normalize_skills(opts["skills"])
            add_skills = _normalize_skills(opts["add_skills"])
            remove_skills = set(_normalize_skills(opts["remove_skills"]))
            existing_skills = list(existing.get("skills") or ([] if not existing.get("skill") else [existing.get("skill")]))
            if opts["clear_skills"]:
                final_skills = []
            elif replacement_skills:
                final_skills = replacement_skills
            elif add_skills or remove_skills:
                final_skills = [skill for skill in existing_skills if skill not in remove_skills]
                for skill in add_skills:
                    if skill not in final_skills:
                        final_skills.append(skill)

            result = _cron_api(
                action="update",
                job_id=job_id,
                schedule=opts["schedule"],
                prompt=opts["prompt"],
                name=opts["name"],
                deliver=opts["deliver"],
                repeat=opts["repeat"],
                skills=final_skills,
            )
            if result.get("success"):
                job = result["job"]
                print(f"(^_^)b Updated job: {job['job_id']}")
                print(f"  Schedule: {job['schedule']}")
                if job.get("skills"):
                    print(f"  Skills: {', '.join(job['skills'])}")
                else:
                    print("  Skills: none")
            else:
                print(f"(x_x) Failed to update job: {result.get('error')}")
            return

        if subcommand in {"pause", "resume", "run", "remove", "rm", "delete"}:
            positionals = opts["positionals"]
            if not positionals:
                print(f"(._.) Usage: /cron {subcommand} <job_id>")
                return
            job_id = positionals[0]
            action = "remove" if subcommand in {"remove", "rm", "delete"} else subcommand
            result = _cron_api(action=action, job_id=job_id, reason="paused from /cron" if action == "pause" else None)
            if not result.get("success"):
                print(f"(x_x) Failed to {action} job: {result.get('error')}")
                return
            if action == "pause":
                print(f"(^_^)b Paused job: {result['job']['name']} ({job_id})")
            elif action == "resume":
                print(f"(^_^)b Resumed job: {result['job']['name']} ({job_id})")
                print(f"  Next run: {result['job'].get('next_run_at')}")
            elif action == "run":
                print(f"(^_^)b Triggered job: {result['job']['name']} ({job_id})")
                print("  It will run on the next scheduler tick.")
            else:
                removed = result.get("removed_job", {})
                print(f"(^_^)b Removed job: {removed.get('name', job_id)} ({job_id})")
            return

        print(f"(._.) Unknown cron command: {subcommand}")
        print("  Available: list, add, edit, pause, resume, run, remove")

    def _handle_suggestions_command(self, cmd: str):
        """Handle /suggestions — review/accept/dismiss suggested automations.

        Delegates to the shared handler so CLI and gateway never drift. CLI
        origin is the local platform so an accepted job's "origin" delivery
        resolves to a configured home channel.
        """
        import shlex

        try:
            tokens = shlex.split(cmd)[1:] if cmd else []
        except ValueError:
            tokens = (cmd or "").split()[1:]
        args = " ".join(tokens)
        try:
            from aetheros_cli.suggestions_cmd import handle_suggestions_command
            output = handle_suggestions_command(args)
        except Exception as e:
            output = f"Suggestions command failed: {e}"
        self._console_print(output)

    def _handle_blueprint_command(self, cmd: str):
        """Handle /blueprint — set up an automation from a blueprint template.

        Delegates to the shared handler. A bare ``/blueprint`` lists the
        catalog; ``/blueprint <name>`` name-matches a blueprint and seeds the
        agent to ask the user for each value conversationally (the result's
        ``agent_seed``); ``/blueprint <name> slot=val …`` creates the job
        directly. When a seed is returned it is stashed as a one-shot pending
        message the interactive loop runs as the next agent turn.
        """
        import shlex

        try:
            tokens = shlex.split(cmd)[1:] if cmd else []
        except ValueError:
            tokens = (cmd or "").split()[1:]
        args = " ".join(shlex.quote(t) for t in tokens)
        try:
            from aetheros_cli.blueprint_cmd import handle_blueprint_command
            result = handle_blueprint_command(args)
        except Exception as e:
            self._console_print(f"Cron blueprint command failed: {e}")
            return
        self._console_print(result.text)
        seed = getattr(result, "agent_seed", None)
        if seed:
            # One-shot: the interactive loop picks this up right after the
            # slash command returns and runs it as a normal agent turn.
            self._pending_agent_seed = seed

    def _handle_curator_command(self, cmd: str):
        """Handle /curator slash command.

        Delegates to aetheros_cli.curator so the CLI and the `aetheros curator`
        subcommand share the same handler set.
        """
        import shlex

        tokens = shlex.split(cmd)[1:] if cmd else []
        if not tokens:
            tokens = ["status"]

        try:
            from aetheros_cli.curator import cli_main
            cli_main(tokens)
        except SystemExit:
            # argparse calls sys.exit() on --help or errors; swallow so we
            # don't kill the interactive session.
            pass
        except Exception as exc:
            print(f"(._.) curator: {exc}")

    def _handle_kanban_command(self, cmd: str):
        """Handle the /kanban command — delegate to the shared kanban CLI.

        The string form passed here is the user's full ``/kanban ...``
        including the leading slash; we strip it and hand the remainder
        to ``kanban.run_slash`` which returns a single formatted string.
        """
        from aetheros_cli.kanban import run_slash

        rest = cmd.strip()
        if rest.startswith("/"):
            rest = rest.lstrip("/")
        if rest.startswith("kanban"):
            rest = rest[len("kanban"):].lstrip()
        try:
            output = run_slash(rest)
        except Exception as exc:  # pragma: no cover - defensive
            output = f"(._.) kanban error: {exc}"
        if output:
            print(output)

    def _handle_mission_command(self, cmd: str):
        """Handle the /mission command — delegate to the shared mission CLI.

        Mirrors ``_handle_kanban_command``: strips the leading slash and
        hands the remainder to ``missions.run_slash``.
        """
        from aetheros_cli.missions import run_slash

        rest = cmd.strip()
        if rest.startswith("/"):
            rest = rest.lstrip("/")
        if rest.startswith("mission"):
            rest = rest[len("mission"):].lstrip()
        try:
            output = run_slash(rest)
        except Exception as exc:  # pragma: no cover - defensive
            output = f"(._.) mission error: {exc}"
        if output:
            print(output)

    def _handle_skills_command(self, cmd: str):
        """Handle /skills slash command — delegates to aetheros_cli.skills_hub."""
        from cli import ChatConsole
        # Intercept write-approval review subcommands first (pending/approve/
        # reject/diff/mode); everything else goes to the skills hub.
        parts = cmd.strip().split()
        args = parts[1:] if len(parts) > 1 else []
        if args and args[0].lower() in {"pending", "approve", "apply", "reject",
                                        "deny", "drop", "diff", "approval", "mode"}:
            from aetheros_cli.write_approval_commands import handle_pending_subcommand
            from tools import write_approval as wa
            out = handle_pending_subcommand(
                wa.SKILLS, args,
                set_mode_fn=lambda enabled: self._save_write_approval("skills", enabled),
            )
            if out is not None:
                print(out)
                return
        from aetheros_cli.skills_hub import handle_skills_slash
        handle_skills_slash(cmd, ChatConsole())

    def _handle_memory_command(self, cmd: str):
        """Handle /memory slash command — pending review + approval-gate toggle."""
        from aetheros_cli.write_approval_commands import handle_pending_subcommand
        from tools import write_approval as wa
        parts = cmd.strip().split()
        args = parts[1:] if len(parts) > 1 else []
        store = getattr(self.agent, "_memory_store", None) if getattr(self, "agent", None) else None
        out = handle_pending_subcommand(
            wa.MEMORY, args,
            memory_store=store,
            set_mode_fn=lambda enabled: self._save_write_approval("memory", enabled),
        )
        if out is None:
            out = ("Unknown /memory subcommand. "
                   "Use: pending, approve <id>, reject <id>, approval <on|off>.")
        print(out)

    def _save_write_approval(self, subsystem: str, enabled: bool):
        """Persist <subsystem>.write_approval to config (for /memory|/skills approval)."""
        from cli import save_config_value
        save_config_value(f"{subsystem}.write_approval", bool(enabled))

    def _handle_background_command(self, cmd: str):
        """Handle /background <prompt> — run a prompt in a separate background session.

        Spawns a new AIAgent in a background thread with its own session.
        When it completes, prints the result to the CLI without modifying
        the active session's conversation history.
        """
        from cli import AIAgent, ChatConsole, _accent_hex, _cprint, _maybe_remap_for_light_mode, _render_final_assistant_content, set_approval_callback, set_secret_capture_callback, set_sudo_password_callback
        parts = cmd.strip().split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            _cprint("  Usage: /background <prompt>")
            _cprint("  Example: /background Summarize the top HN stories today")
            _cprint("  The task runs in a separate session and results display here when done.")
            return

        prompt = parts[1].strip()
        self._background_task_counter += 1
        task_num = self._background_task_counter
        task_id = f"bg_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # Make sure we have valid credentials
        if not self._ensure_runtime_credentials():
            _cprint("  (>_<) Cannot start background task: no valid credentials.")
            return

        _cprint(f"  🔄 Background task #{task_num} started: \"{prompt[:60]}{'...' if len(prompt) > 60 else ''}\"")
        _cprint(f"  Task ID: {task_id}")
        _cprint("  You can continue chatting — results will appear when done.\n")

        turn_route = self._resolve_turn_agent_config(prompt)

        def run_background():
            set_sudo_password_callback(self._sudo_password_callback)
            set_approval_callback(self._approval_callback)
            try:
                set_secret_capture_callback(self._secret_capture_callback)
            except Exception:
                pass
            try:
                bg_agent = AIAgent(
                    model=turn_route["model"],
                    api_key=turn_route["runtime"].get("api_key"),
                    base_url=turn_route["runtime"].get("base_url"),
                    provider=turn_route["runtime"].get("provider"),
                    api_mode=turn_route["runtime"].get("api_mode"),
                    acp_command=turn_route["runtime"].get("command"),
                    acp_args=turn_route["runtime"].get("args"),
                    max_tokens=turn_route["runtime"].get("max_tokens"),
                    max_iterations=self.max_turns,
                    enabled_toolsets=self.enabled_toolsets,
                    quiet_mode=True,
                    verbose_logging=False,
                    session_id=task_id,
                    platform="cli",
                    session_db=self._session_db,
                    reasoning_config=self.reasoning_config,
                    service_tier=self.service_tier,
                    request_overrides=turn_route.get("request_overrides"),
                    providers_allowed=self._providers_only,
                    providers_ignored=self._providers_ignore,
                    providers_order=self._providers_order,
                    provider_sort=self._provider_sort,
                    provider_require_parameters=self._provider_require_params,
                    provider_data_collection=self._provider_data_collection,
                    openrouter_min_coding_score=self._openrouter_min_coding_score,
                    fallback_model=self._fallback_model,
                )
                # Silence raw spinner; route thinking through TUI widget when no foreground agent is active.
                bg_agent._print_fn = lambda *_a, **_kw: None

                def _bg_thinking(text: str) -> None:
                    # Concurrent bg tasks may race on _spinner_text; acceptable for best-effort UI.
                    if not self._agent_running:
                        self._spinner_text = text
                        if self._app:
                            self._app.invalidate()

                bg_agent.thinking_callback = _bg_thinking

                result = bg_agent.run_conversation(
                    user_message=prompt,
                    task_id=task_id,
                )

                response = result.get("final_response", "") if result else ""
                if not response and result and result.get("error"):
                    response = f"Error: {result['error']}"

                # Display result in the CLI (thread-safe via patch_stdout).
                # Force a TUI refresh first so spinner/status bar don't overlap
                # with the output (fixes #2718).
                if self._app:
                    self._app.invalidate()
                    time.sleep(0.05)  # brief pause for refresh
                print()
                ChatConsole().print(f"[{_accent_hex()}]{'─' * 40}[/]")
                _cprint(f"  ✅ Background task #{task_num} complete")
                _cprint(f"  Prompt: \"{prompt[:60]}{'...' if len(prompt) > 60 else ''}\"")
                ChatConsole().print(f"[{_accent_hex()}]{'─' * 40}[/]")
                if response:
                    try:
                        from aetheros_cli.skin_engine import get_active_skin
                        _skin = get_active_skin()
                        label = _skin.get_branding("response_label", "◇ Aetheros")
                        _resp_color = _maybe_remap_for_light_mode(_skin.get_color("response_border", "#CD7F32"))
                        _resp_text = _maybe_remap_for_light_mode(_skin.get_color("banner_text", "#FFF8DC"))
                    except Exception:
                        label = "◇ Aetheros"
                        _resp_color = "#CD7F32"
                        _resp_text = "#FFF8DC"

                    _chat_console = ChatConsole()
                    _chat_console.print(Panel(
                        _render_final_assistant_content(response, mode=self.final_response_markdown),
                        title=f"[{_resp_color} bold]{label} (background #{task_num})[/]",
                        title_align="left",
                        border_style=_resp_color,
                        style=_resp_text,
                        box=rich_box.HORIZONTALS,
                        padding=(1, 4),
                        width=self._scrollback_box_width(),
                    ))
                else:
                    _cprint("  (No response generated)")

                # Play bell if enabled
                if self.bell_on_complete:
                    sys.stdout.write("\a")
                    sys.stdout.flush()

            except Exception as e:
                # Same TUI refresh pattern as success path (#2718)
                if self._app:
                    self._app.invalidate()
                    time.sleep(0.05)
                print()
                _cprint(f"  ❌ Background task #{task_num} failed: {e}")
            finally:
                try:
                    set_sudo_password_callback(None)
                    set_approval_callback(None)
                    set_secret_capture_callback(None)
                except Exception:
                    pass
                self._background_tasks.pop(task_id, None)
                # Clear spinner only if no foreground agent owns it
                if not self._agent_running:
                    self._spinner_text = ""
                if self._app:
                    self._invalidate(min_interval=0)

        thread = threading.Thread(target=run_background, daemon=True, name=f"bg-task-{task_id}")
        self._background_tasks[task_id] = thread
        thread.start()

    def _handle_bundles_command(self, cmd: str) -> None:
        """In-session ``/bundles`` — show installed skill bundles.

        Mirrors ``aetheros bundles list`` but renders inside the running
        CLI so users can discover what's available without dropping out
        of their session. Bundles are loaded via ``/<bundle-name>``.
        """
        from cli import ChatConsole, _BOLD, _DIM, _RST, _accent_hex, _cprint
        try:
            from agent.skill_bundles import list_bundles, _bundles_dir
        except Exception as exc:
            _cprint(f"\033[1;31mBundle subsystem unavailable: {exc}{_RST}")
            return

        bundles = list_bundles()
        if not bundles:
            _cprint("  No skill bundles installed.")
            _cprint(
                f"  {_DIM}Create one with: aetheros bundles create "
                f"<name> --skill <s1> --skill <s2>{_RST}"
            )
            _cprint(f"  {_DIM}Directory: {_bundles_dir()}{_RST}")
            return

        _cprint(f"\n  ▣ {_BOLD}Skill Bundles{_RST} ({len(bundles)} installed):")
        for info in bundles:
            skill_count = len(info.get("skills", []))
            desc = info.get("description") or f"Load {skill_count} skills"
            ChatConsole().print(
                f"    [bold {_accent_hex()}]/{info['slug']:<20}[/] "
                f"[dim]-[/] {_escape(desc)} [dim]({skill_count} skills)[/]"
            )
            for s in info.get("skills", []):
                ChatConsole().print(f"        [dim]· {_escape(s)}[/]")
        _cprint(
            f"\n  {_DIM}Invoke a bundle with /<slug>. "
            f"Manage with `aetheros bundles`.{_RST}"
        )

    def _handle_browser_command(self, cmd: str):
        """Handle /browser connect|disconnect|status — manage live Chromium-family CDP connection."""
        import platform as _plat

        parts = cmd.strip().split(None, 1)
        sub = parts[1].lower().strip() if len(parts) > 1 else "status"

        _DEFAULT_CDP = DEFAULT_BROWSER_CDP_URL
        current = os.environ.get("BROWSER_CDP_URL", "").strip()

        if sub.startswith("connect"):
            # Optionally accept a custom CDP URL: /browser connect ws://host:port
            connect_parts = cmd.strip().split(None, 2)  # ["/browser", "connect", "ws://..."]
            cdp_url = connect_parts[2].strip() if len(connect_parts) > 2 else _DEFAULT_CDP
            parsed_cdp = urlparse(cdp_url if "://" in cdp_url else f"http://{cdp_url}")
            if parsed_cdp.scheme not in {"http", "https", "ws", "wss"}:
                print()
                print(
                    f"   ⚠ Unsupported browser url scheme: {parsed_cdp.scheme or '(missing)'} "
                    "(expected one of: http, https, ws, wss)"
                )
                print()
                return
            try:
                _port = parsed_cdp.port or (443 if parsed_cdp.scheme in {"https", "wss"} else 80)
            except ValueError:
                print()
                print(f"   ⚠ Invalid port in browser url: {cdp_url}")
                print()
                return
            if not parsed_cdp.hostname:
                print()
                print(f"   ⚠ Missing host in browser url: {cdp_url}")
                print()
                return
            _host = parsed_cdp.hostname
            if parsed_cdp.path.startswith("/devtools/browser/"):
                cdp_url = parsed_cdp.geturl()
            else:
                cdp_url = parsed_cdp._replace(
                    path="",
                    params="",
                    query="",
                    fragment="",
                ).geturl()

            # Clear any existing browser sessions so the next tool call uses the new backend
            try:
                from tools.browser_tool import cleanup_all_browsers
                cleanup_all_browsers()
            except Exception:
                pass

            print()

            # Check if a Chromium-family browser is already serving CDP on the debug port
            _already_open = is_browser_debug_ready(cdp_url, timeout=1.0)

            if _already_open:
                print(f"   ✓ Chromium-family browser is already listening on port {_port}")
            elif cdp_url == _DEFAULT_CDP:
                # Try to auto-launch a Chromium-family browser with remote debugging
                print("   Chromium-family browser isn't running with remote debugging — attempting to launch...")
                _launched = self._try_launch_chrome_debug(_port, _plat.system())
                if _launched:
                    # Wait for the DevTools discovery endpoint to come up
                    for _wait in range(10):
                        if is_browser_debug_ready(cdp_url, timeout=1.0):
                            _already_open = True
                            break
                        time.sleep(0.5)
                    if _already_open:
                        print(f"   ✓ Chromium-family browser launched and listening on port {_port}")
                    else:
                        print(f"   ⚠ Browser launched but port {_port} isn't responding yet")
                        print("     Try again in a few seconds — the debug instance may still be starting")
                else:
                    print("   ⚠ Could not auto-launch a Chromium-family browser")
                    sys_name = _plat.system()
                    chrome_cmd = manual_chrome_debug_command(_port, sys_name)
                    if chrome_cmd:
                        print(f"     Launch a Chromium-family browser manually:")
                        print(f"     {chrome_cmd}")
                    else:
                        print("     No supported Chromium-family browser executable found in this environment")
            else:
                print(f"   ⚠ Port {_port} is not reachable at {cdp_url}")

            if not _already_open:
                print()
                print("Browser not connected — start a Chromium-family browser with remote debugging and retry /browser connect")
                print()
                return

            os.environ["BROWSER_CDP_URL"] = cdp_url
            # Eagerly start the CDP supervisor so pending_dialogs + frame_tree
            # show up in the next browser_snapshot.  No-op if already started.
            try:
                from tools.browser_tool import _ensure_cdp_supervisor  # type: ignore[import-not-found]
                _ensure_cdp_supervisor("default")
            except Exception:
                pass
            print()
            print("🌐 Browser connected to live Chromium-family browser via CDP")
            print(f"   Endpoint: {cdp_url}")
            print()

            # Inject context message so the model knows this slash command
            # intentionally makes the dev/debug CDP browser available for use.
            if hasattr(self, '_pending_input'):
                self._pending_input.put(
                    "[System note: The user invoked /browser connect and connected your browser tools to "
                    "a Chromium-family dev/debug browser via Chrome DevTools Protocol. "
                    "Your browser_navigate, browser_snapshot, browser_click, and other browser tools now "
                    "control that CDP browser. The command itself is a signal that using browser tools for "
                    "their current browser-related request is expected; do not wait for separate permission "
                    "just because CDP is connected. This is typically a Aetheros-managed isolated debug "
                    "profile, not the user's main everyday browser. It is still user-visible and may contain "
                    "pages, logged-in sessions, or cookies in that debug profile, so avoid destructive actions, "
                    "closing tabs, or navigating away unless the user's task calls for it.]"
                )

        elif sub == "disconnect":
            if current:
                os.environ.pop("BROWSER_CDP_URL", None)
                try:
                    from tools.browser_tool import cleanup_all_browsers, _stop_cdp_supervisor
                    _stop_cdp_supervisor("default")
                    cleanup_all_browsers()
                except Exception:
                    pass
                print()
                print("🌐 Browser disconnected from live Chromium-family browser")
                print("   Browser tools reverted to default mode (local headless or cloud provider)")
                print()

                if hasattr(self, '_pending_input'):
                    self._pending_input.put(
                        "[System note: The user has disconnected the browser tools from their live Chromium-family browser. "
                        "Browser tools are back to default mode (headless local browser or cloud provider).]"
                    )
            else:
                print()
                print("Browser is not connected to a live Chromium-family browser (already using default mode)")
                print()

        elif sub == "status":
            print()
            if current:
                print("🌐 Browser: connected to live Chromium-family browser via CDP")
                print(f"   Endpoint: {current}")

                _port = 9222
                try:
                    _port = int(current.rsplit(":", 1)[-1].split("/")[0])
                except (ValueError, IndexError):
                    pass
                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    s.connect(("127.0.0.1", _port))
                    s.close()
                    print("   Status: ✓ reachable")
                except (OSError, Exception):
                    print("   Status: ⚠ not reachable (browser may not be running)")
            else:
                try:
                    from tools.browser_tool import _get_cloud_provider
                    provider = _get_cloud_provider()
                except Exception:
                    provider = None

                if provider is not None:
                    print(f"🌐 Browser: {provider.provider_name()} (cloud)")
                else:
                    # Show engine info for local mode
                    try:
                        from tools.browser_tool import _get_browser_engine
                        engine = _get_browser_engine()
                    except Exception:
                        engine = "auto"
                    if engine == "lightpanda":
                        print("🌐 Browser: local Lightpanda (agent-browser --engine lightpanda)")
                        print("   ⚡ Lightpanda: faster navigation, no screenshot support")
                        print("   Automatic Chromium fallback for screenshots and failed commands")
                    elif engine == "chrome":
                        print("🌐 Browser: local headless Chromium (agent-browser --engine chrome)")
                    else:
                        print("🌐 Browser: local headless Chromium (agent-browser)")
            print()
            print("   /browser connect      — connect to your live Chromium-family browser")
            print("   /browser disconnect   — revert to default")
            print()

        else:
            print()
            print("Usage: /browser connect|disconnect|status")
            print()
            print("   connect      Connect browser tools to your live Chromium-family browser session")
            print("   disconnect   Revert to default browser backend")
            print("   status       Show current browser mode")
            print()

    def _handle_goal_command(self, cmd: str) -> None:
        """Dispatch /goal subcommands: set / status / pause / resume / clear."""
        from cli import _DIM, _RST, _cprint
        parts = (cmd or "").strip().split(None, 1)
        arg = parts[1].strip() if len(parts) > 1 else ""

        mgr = self._get_goal_manager()
        if mgr is None:
            _cprint(f"  {_DIM}Goals unavailable (no active session).{_RST}")
            return

        lower = arg.lower()

        # Bare /goal or /goal status → show current state
        if not arg or lower == "status":
            _cprint(f"  {mgr.status_line()}")
            return

        if lower == "pause":
            state = mgr.pause(reason="user-paused")
            if state is None:
                _cprint(f"  {_DIM}No goal set.{_RST}")
            else:
                _cprint(f"  ⏸ Goal paused: {state.goal}")
            return

        if lower == "resume":
            state = mgr.resume()
            if state is None:
                _cprint(f"  {_DIM}No goal to resume.{_RST}")
            else:
                _cprint(f"  ▶ Goal resumed: {state.goal}")
                _cprint(
                    f"  {_DIM}Send any message (or press Enter on an empty prompt "
                    f"is a no-op; type 'continue' to kick it off).{_RST}"
                )
            return

        if lower in {"clear", "stop", "done"}:
            had = mgr.has_goal()
            mgr.clear()
            if had:
                _cprint("  ✓ Goal cleared.")
            else:
                _cprint(f"  {_DIM}No active goal.{_RST}")
            return

        # Otherwise treat the arg as the goal text.
        try:
            state = mgr.set(arg)
        except ValueError as exc:
            _cprint(f"  Invalid goal: {exc}")
            return

        _cprint(f"  ⊙ Goal set ({state.max_turns}-turn budget): {state.goal}")
        _cprint(
            f"  {_DIM}After each turn, a judge model will check if the goal is done. "
            f"Aetheros keeps working until it is, you pause/clear it, or the budget is "
            f"exhausted. Use /goal status, /goal pause, /goal resume, /goal clear.{_RST}"
        )
        # Kick the loop off immediately so the user doesn't have to send a
        # separate message after setting the goal.
        try:
            self._pending_input.put(state.goal)
        except Exception:
            pass

    def _handle_subgoal_command(self, cmd: str) -> None:
        """Dispatch /subgoal subcommands.

        Forms:
          /subgoal                              show current subgoals
          /subgoal <text>                       append a criterion
          /subgoal remove <n>                   drop subgoal n (1-based)
          /subgoal clear                        wipe all subgoals

        Subgoals are extra criteria the user adds mid-loop. They get
        appended to both the judge prompt (verdict must consider them)
        and the continuation prompt (agent sees them) on the next turn
        boundary. No special kick — the running turn finishes, the next
        judge call includes them.
        """
        from cli import _DIM, _RST, _cprint
        parts = (cmd or "").strip().split(None, 2)
        arg = " ".join(parts[1:]).strip() if len(parts) > 1 else ""

        mgr = self._get_goal_manager()
        if mgr is None:
            _cprint(f"  {_DIM}Goals unavailable (no active session).{_RST}")
            return

        if not mgr.has_goal():
            _cprint(f"  {_DIM}No active goal. Set one with /goal <text>.{_RST}")
            return

        # No args → list current subgoals.
        if not arg:
            _cprint(f"  {mgr.status_line()}")
            _cprint(f"  {mgr.render_subgoals()}")
            return

        tokens = arg.split(None, 1)
        verb = tokens[0].lower()
        rest = tokens[1].strip() if len(tokens) > 1 else ""

        if verb == "remove":
            if not rest:
                _cprint("  Usage: /subgoal remove <n>")
                return
            try:
                idx = int(rest.split()[0])
            except ValueError:
                _cprint("  /subgoal remove: <n> must be an integer (1-based index).")
                return
            try:
                removed = mgr.remove_subgoal(idx)
            except (IndexError, RuntimeError) as exc:
                _cprint(f"  /subgoal remove: {exc}")
                return
            _cprint(f"  ✓ Removed subgoal {idx}: {removed}")
            return

        if verb == "clear":
            try:
                prev = mgr.clear_subgoals()
            except RuntimeError as exc:
                _cprint(f"  /subgoal clear: {exc}")
                return
            if prev:
                _cprint(f"  ✓ Cleared {prev} subgoal{'s' if prev != 1 else ''}.")
            else:
                _cprint(f"  {_DIM}No subgoals to clear.{_RST}")
            return

        # Otherwise — append the whole arg as a new subgoal.
        try:
            text = mgr.add_subgoal(arg)
        except (ValueError, RuntimeError) as exc:
            _cprint(f"  /subgoal: {exc}")
            return
        idx = len(mgr.state.subgoals) if mgr.state else 0
        _cprint(f"  ✓ Added subgoal {idx}: {text}")

    def _handle_skin_command(self, cmd: str):
        """Handle /skin [name] — show or change the display skin."""
        from cli import _ACCENT, save_config_value
        try:
            from aetheros_cli.skin_engine import list_skins, set_active_skin, get_active_skin_name
        except ImportError:
            print("Skin engine not available.")
            return

        parts = cmd.strip().split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            # Show current skin and list available
            current = get_active_skin_name()
            skins = list_skins()
            print(f"\n  Current skin: {current}")
            print("  Available skins:")
            for s in skins:
                marker = " ●" if s["name"] == current else "  "
                source = f" ({s['source']})" if s["source"] == "user" else ""
                print(f"   {marker} {s['name']}{source} — {s['description']}")
            print("\n  Usage: /skin <name>")
            print(f"  Custom skins: drop a YAML file in {display_aetheros_home()}/skins/\n")
            return

        new_skin = parts[1].strip().lower()
        available = {s["name"] for s in list_skins()}
        if new_skin not in available:
            print(f"  Unknown skin: {new_skin}")
            print(f"  Available: {', '.join(sorted(available))}")
            return

        set_active_skin(new_skin)
        _ACCENT.reset()  # Re-resolve ANSI color for the new skin
        # _DIM is now a fixed dim+italic ANSI escape (terminal-default fg)
        # so it doesn't need re-resolving on skin switch.
        if save_config_value("display.skin", new_skin):
            print(f"  Skin set to: {new_skin} (saved)")
        else:
            print(f"  Skin set to: {new_skin}")
        print("  Note: banner colors will update on next session start.")
        if self._apply_tui_skin_style():
            print("  Prompt + TUI colors updated.")

    def _handle_footer_command(self, cmd_original: str) -> None:
        """Toggle or inspect ``display.runtime_footer.enabled`` from the CLI.

        Usage:
            /footer           → toggle
            /footer on|off    → explicit
            /footer status    → show current state
        """
        from cli import _cprint, save_config_value
        from aetheros_cli.config import load_config
        from aetheros_cli.colors import Colors as _Colors

        # Parse arg
        arg = ""
        try:
            parts = (cmd_original or "").strip().split(None, 1)
            if len(parts) > 1:
                arg = parts[1].strip().lower()
        except Exception:
            arg = ""

        cfg = load_config() or {}
        footer_cfg = ((cfg.get("display") or {}).get("runtime_footer") or {})
        current = bool(footer_cfg.get("enabled", False))
        fields = footer_cfg.get("fields") or ["model", "context_pct", "cwd"]

        if arg in {"status", "?"}:
            state = "ON" if current else "OFF"
            _cprint(
                f"  {_Colors.BOLD}Runtime footer:{_Colors.RESET} {state}\n"
                f"  Fields: {', '.join(fields)}"
            )
            return

        if arg in {"on", "enable", "true", "1"}:
            new_state = True
        elif arg in {"off", "disable", "false", "0"}:
            new_state = False
        elif arg == "":
            new_state = not current
        else:
            _cprint("  Usage: /footer [on|off|status]")
            return

        if save_config_value("display.runtime_footer.enabled", new_state):
            state = (
                f"{_Colors.GREEN}ON{_Colors.RESET}" if new_state
                else f"{_Colors.DIM}OFF{_Colors.RESET}"
            )
            _cprint(f"  Runtime footer: {state}")
        else:
            _cprint("  Failed to save runtime_footer setting to config.yaml")

    def _handle_reasoning_command(self, cmd: str):
        """Handle /reasoning — manage effort level and display toggle.

        Usage:
            /reasoning              Show current effort level and display state
            /reasoning <level>      Set reasoning effort (none, minimal, low, medium, high, xhigh)
            /reasoning show|on      Show model thinking/reasoning in output
            /reasoning hide|off     Hide model thinking/reasoning from output
        """
        from cli import _ACCENT, _DIM, _RST, _cprint, _parse_reasoning_config, save_config_value
        parts = cmd.strip().split(maxsplit=1)

        if len(parts) < 2:
            # Show current state
            rc = self.reasoning_config
            if rc is None:
                level = "medium (default)"
            elif rc.get("enabled") is False:
                level = "none (disabled)"
            else:
                level = rc.get("effort", "medium")
            display_state = "on ✓" if self.show_reasoning else "off"
            _cprint(f"  {_ACCENT}Reasoning effort:  {level}{_RST}")
            _cprint(f"  {_ACCENT}Reasoning display: {display_state}{_RST}")
            _cprint(f"  {_DIM}Usage: /reasoning <none|minimal|low|medium|high|xhigh|show|hide>{_RST}")
            return

        arg = parts[1].strip().lower()

        # Display toggle
        if arg in {"show", "on"}:
            self.show_reasoning = True
            if self.agent:
                self.agent.reasoning_callback = self._current_reasoning_callback()
            save_config_value("display.show_reasoning", True)
            _cprint(f"  {_ACCENT}✓ Reasoning display: ON (saved){_RST}")
            _cprint(f"  {_DIM}  Model thinking will be shown during and after each response.{_RST}")
            return
        if arg in {"hide", "off"}:
            self.show_reasoning = False
            if self.agent:
                self.agent.reasoning_callback = self._current_reasoning_callback()
            save_config_value("display.show_reasoning", False)
            _cprint(f"  {_ACCENT}✓ Reasoning display: OFF (saved){_RST}")
            return

        # Effort level change
        parsed = _parse_reasoning_config(arg)
        if parsed is None:
            _cprint(f"  {_DIM}(._.) Unknown argument: {arg}{_RST}")
            _cprint(f"  {_DIM}Valid levels: none, minimal, low, medium, high, xhigh{_RST}")
            _cprint(f"  {_DIM}Display:      show, hide{_RST}")
            return

        self.reasoning_config = parsed
        self.agent = None  # Force agent re-init with new reasoning config

        if save_config_value("agent.reasoning_effort", arg):
            _cprint(f"  {_ACCENT}✓ Reasoning effort set to '{arg}' (saved to config){_RST}")
        else:
            _cprint(f"  {_ACCENT}✓ Reasoning effort set to '{arg}' (session only){_RST}")

    def _handle_busy_command(self, cmd: str):
        """Handle /busy — control what Enter does while Aetheros is working.

        Usage:
            /busy               Show current busy input mode
            /busy status        Show current busy input mode
            /busy queue         Queue input for the next turn instead of interrupting
            /busy steer         Inject Enter mid-run via /steer (after next tool call)
            /busy interrupt     Interrupt the current run on Enter (default)
        """
        from cli import _ACCENT, _DIM, _RST, _cprint, save_config_value
        parts = cmd.strip().split(maxsplit=1)
        if len(parts) < 2 or parts[1].strip().lower() == "status":
            _cprint(f"  {_ACCENT}Busy input mode: {self.busy_input_mode}{_RST}")
            if self.busy_input_mode == "queue":
                _behavior = "queues for next turn"
            elif self.busy_input_mode == "steer":
                _behavior = "steers into current run (after next tool call)"
            else:
                _behavior = "interrupts current run"
            _cprint(f"  {_DIM}Enter while busy: {_behavior}{_RST}")
            _cprint(f"  {_DIM}Usage: /busy [queue|steer|interrupt|status]{_RST}")
            return

        arg = parts[1].strip().lower()
        if arg not in {"queue", "interrupt", "steer"}:
            _cprint(f"  {_DIM}(._.) Unknown argument: {arg}{_RST}")
            _cprint(f"  {_DIM}Usage: /busy [queue|steer|interrupt|status]{_RST}")
            return

        self.busy_input_mode = arg
        if save_config_value("display.busy_input_mode", arg):
            if arg == "queue":
                behavior = "Enter will queue follow-up input while Aetheros is busy."
            elif arg == "steer":
                behavior = "Enter will steer your message into the current run (after the next tool call)."
            else:
                behavior = "Enter will interrupt the current run while Aetheros is busy."
            _cprint(f"  {_ACCENT}✓ Busy input mode set to '{arg}' (saved to config){_RST}")
            _cprint(f"  {_DIM}{behavior}{_RST}")
        else:
            _cprint(f"  {_ACCENT}✓ Busy input mode set to '{arg}' (session only){_RST}")

    def _handle_fast_command(self, cmd: str):
        """Handle /fast — toggle fast mode (OpenAI Priority Processing / Anthropic Fast Mode)."""
        from cli import _ACCENT, _DIM, _RST, _cprint, save_config_value
        if not self._fast_command_available():
            _cprint("  (._.) /fast is only available for models that support fast mode (OpenAI Priority Processing or Anthropic Fast Mode).")
            return

        # Determine the branding for the current model
        try:
            from aetheros_cli.models import _is_anthropic_fast_model
            agent = getattr(self, "agent", None)
            model = getattr(agent, "model", None) or getattr(self, "model", None)
            feature_name = "Anthropic Fast Mode" if _is_anthropic_fast_model(model) else "Priority Processing"
        except Exception:
            feature_name = "Fast mode"

        parts = cmd.strip().split(maxsplit=1)
        if len(parts) < 2 or parts[1].strip().lower() == "status":
            status = "fast" if self.service_tier == "priority" else "normal"
            _cprint(f"  {_ACCENT}{feature_name}: {status}{_RST}")
            _cprint(f"  {_DIM}Usage: /fast [normal|fast|status]{_RST}")
            return

        arg = parts[1].strip().lower()

        if arg in {"fast", "on"}:
            self.service_tier = "priority"
            saved_value = "fast"
            label = "FAST"
        elif arg in {"normal", "off"}:
            self.service_tier = None
            saved_value = "normal"
            label = "NORMAL"
        else:
            _cprint(f"  {_DIM}(._.) Unknown argument: {arg}{_RST}")
            _cprint(f"  {_DIM}Usage: /fast [normal|fast|status]{_RST}")
            return

        self.agent = None  # Force agent re-init with new service-tier config
        if save_config_value("agent.service_tier", saved_value):
            _cprint(f"  {_ACCENT}✓ {feature_name} set to {label} (saved to config){_RST}")
        else:
            _cprint(f"  {_ACCENT}✓ {feature_name} set to {label} (session only){_RST}")

    def _handle_debug_command(self):
        """Handle /debug — upload debug report + logs and print paste URLs."""
        from aetheros_cli.debug import run_debug_share
        from types import SimpleNamespace

        args = SimpleNamespace(lines=200, expire=7, local=False)
        run_debug_share(args)

    def _handle_update_command(self) -> bool:
        """Handle /update — update Aetheros to the latest version.

        In the classic CLI this exits the session and relaunches as
        ``aetheros update`` so the user sees update output directly and gets
        the new version on next launch.

        Returns ``True`` when the update was confirmed (caller should trigger
        app exit so the relaunch is deferred to the main thread after
        prompt_toolkit cleans up terminal modes).  Returns ``False`` / falsy
        when cancelled.
        """
        from aetheros_cli.config import is_managed, format_managed_message

        if is_managed():
            print(f"  ✗ {format_managed_message('update Aetheros')}")
            return False

        # Use the prompt_toolkit-native modal so the confirmation panel
        # renders properly above the composer and avoids raw input() races
        # with the prompt_toolkit event loop (same pattern as
        # _confirm_destructive_slash).
        choices = [
            ("once", "Update Now", "exit the current session and update Aetheros"),
            ("cancel", "Cancel", "keep the current session"),
        ]
        raw = self._prompt_text_input_modal(
            title="◇  Update Aetheros",
            detail="This will exit the current session and run `aetheros update`.",
            choices=choices,
        )
        if raw is None:
            print("  🟡 /update cancelled.")
            return False
        choice = self._normalize_slash_confirm_choice(raw, choices)
        if choice != "once":
            print("  🟡 /update cancelled.")
            return False

        print()
        print("  ◇ Launching update...")
        print()

        # Store the relaunch args so run() can exec them from the main thread
        # after prompt_toolkit exits and restores terminal modes.  Calling
        # relaunch() directly here (from the process_loop daemon thread) would
        # skip terminal cleanup on POSIX (execvp replaces the process mid-TUI)
        # and only exit the worker thread on Windows (subprocess.run +
        # sys.exit inside a non-main thread does not exit the process).
        self._pending_relaunch = ["update"]
        return True

    def _handle_voice_command(self, command: str):
        """Handle /voice [on|off|tts|status] command."""
        from cli import _cprint
        parts = command.strip().split(maxsplit=1)
        subcommand = parts[1].lower().strip() if len(parts) > 1 else ""

        if subcommand == "on":
            self._enable_voice_mode()
        elif subcommand == "off":
            self._disable_voice_mode()
        elif subcommand == "tts":
            self._toggle_voice_tts()
        elif subcommand == "status":
            self._show_voice_status()
        elif subcommand == "":
            # Toggle
            if self._voice_mode:
                self._disable_voice_mode()
            else:
                self._enable_voice_mode()
        else:
            _cprint(f"Unknown voice subcommand: {subcommand}")
            _cprint("Usage: /voice [on|off|tts|status]")

    def _handle_connect_command(self, raw: str) -> None:
        from cli import _cprint
        from connect.cli import handle_connect_command as hcc, build_connect_parser
        import shlex, argparse
        parts = shlex.split(raw)[1:]
        p = argparse.ArgumentParser(prog="connect")
        sp = p.add_subparsers(dest="connect_command")
        build_connect_parser(sp)
        try:
            args = p.parse_args(parts or ["--help"])
            if hasattr(args, "connect_command"):
                hcc(args)
        except SystemExit:
            pass
        except Exception as e:
            _cprint(f"Connect error: {e}")

    def _handle_dashboard_command(self, raw: str) -> None:
        from aetheros_platform.cli import plt_handle_dashboard
        import shlex, argparse
        parts = shlex.split(raw)[1:]
        parser = argparse.ArgumentParser(prog="dashboard")
        parser.add_argument("command", nargs="?", default="status",
                            choices=["start", "stop", "status", "layout",
                                     "widget", "panel", "info"])
        parser.add_argument("--port", type=int, default=8756)
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--layout", default="")
        parser.add_argument("--widget", default="")
        parser.add_argument("-v", "--verbose", action="store_true")
        args = parser.parse_args(parts or ["status"])
        plt_handle_dashboard(args)

    def _handle_knowledge_command(self, raw: str) -> None:
        from aetheros_platform.cli import plt_handle_knowledge
        import shlex, argparse
        parts = shlex.split(raw)[1:]
        parser = argparse.ArgumentParser(prog="knowledge")
        parser.add_argument("command", nargs="?", default="status",
                            choices=["status", "search", "entity", "relation",
                                     "memory", "stats", "clear"])
        parser.add_argument("--query", default="")
        parser.add_argument("--id", default="")
        parser.add_argument("--type", default="")
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--db", default="")
        args = parser.parse_args(parts or ["status"])
        plt_handle_knowledge(args)

    def _handle_security_command(self, raw: str) -> None:
        from aetheros_platform.cli import plt_handle_security
        import shlex, argparse
        parts = shlex.split(raw)[1:]
        parser = argparse.ArgumentParser(prog="security")
        parser.add_argument("command", nargs="?", default="status",
                            choices=["status", "users", "roles", "sessions",
                                     "audit", "keys", "mfa", "providers",
                                     "scorecard", "kill-switch", "shutdown",
                                     "classify", "flow", "guard"])
        parser.add_argument("--user", default="")
        parser.add_argument("--role", default="")
        parser.add_argument("--action", default="")
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--db", default="")
        parser.add_argument("--name", default="")
        parser.add_argument("--state", choices=["on", "off"], default=None)
        parser.add_argument("--source", default="")
        parser.add_argument("--destination", default="")
        parser.add_argument("--classification", default="")
        args = parser.parse_args(parts or ["status"])
        plt_handle_security(args)

    def _handle_observability_command(self, raw: str) -> None:
        from aetheros_platform.cli import plt_handle_observability
        import shlex, argparse
        parts = shlex.split(raw)[1:]
        parser = argparse.ArgumentParser(prog="observability")
        parser.add_argument("command", nargs="?", default="status",
                            choices=["status", "metrics", "traces", "logs",
                                     "telemetry", "analytics", "export",
                                     "health", "diagnostics", "incidents",
                                     "recovery", "costs", "evaluation"])
        parser.add_argument("--format",
                            choices=["json", "prometheus", "csv", "text"],
                            default="json")
        parser.add_argument("--trace", default="")
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--db", default="")
        parser.add_argument("--out", default="")
        args = parser.parse_args(parts or ["status"])
        plt_handle_observability(args)

    def _handle_desktop_command(self, raw: str) -> None:
        from aetheros_platform.cli import plt_handle_desktop
        import shlex, argparse
        parts = shlex.split(raw)[1:]
        parser = argparse.ArgumentParser(prog="desktop")
        parser.add_argument("command", nargs="?", default="status",
                            choices=["status", "start", "stop", "windows",
                                     "tray", "notifications"])
        parser.add_argument("--action", default="")
        args = parser.parse_args(parts or ["status"])
        plt_handle_desktop(args)

    def _handle_jarvis_command(self, raw: str) -> None:
        import shlex, argparse, sys, time, threading
        from core.jarvis.startup import initialize_engine, shutdown_engine
        from core.jarvis.websocket_server import run_jarvis_server
        from aetheros_cli.config import load_config
        from aetheros_constants import get_aetheros_home

        parts = shlex.split(raw)[1:]
        parser = argparse.ArgumentParser(prog="jarvis")
        parser.add_argument("command", nargs="?", default="status",
                            choices=["start", "stop", "status", "restart"])
        args = parser.parse_args(parts or ["status"])

        if args.command == "start":
            cfg = load_config()
            host = cfg.get("jarvis", {}).get("host", "127.0.0.1")
            port = cfg.get("jarvis", {}).get("port", 9789)
            storage = get_aetheros_home() / "jarvis"

            t = threading.Thread(
                target=lambda: run_jarvis_server(
                    host=host, port=port, storage_dir=str(storage)
                ),
                daemon=True,
            )
            t.start()
            time.sleep(1)
            print(f" Jarvis Engine started on ws://{host}:{port}")

        elif args.command == "stop":
            shutdown_engine()
            print(" Jarvis Engine stopped")

        elif args.command == "status":
            from core.jarvis.startup import get_engine
            engine = get_engine()
            if engine and engine.is_running:
                state = engine.get_state()
                print(f" Jarvis Engine: Running")
                print(f"   Phase: {state['phase']}")
                print(f"   Cycles: {state['cycleCount']}")
                print(f"   Memory: {engine.memory.get_stats()['total']} entries")
                print(f"   Notifications: {engine.notifications.unread_count} unread")
            else:
                print(" Jarvis Engine: Not running")

        elif args.command == "restart":
            shutdown_engine()
            time.sleep(1)
            cfg = load_config()
            host = cfg.get("jarvis", {}).get("host", "127.0.0.1")
            port = cfg.get("jarvis", {}).get("port", 9789)
            storage = get_aetheros_home() / "jarvis"
            t = threading.Thread(
                target=lambda: run_jarvis_server(
                    host=host, port=port, storage_dir=str(storage)
                ),
                daemon=True,
            )
            t.start()
            print(" Jarvis Engine restarted")
