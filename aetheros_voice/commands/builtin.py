from __future__ import annotations

from aetheros_voice.commands.registry import CommandRegistry
from aetheros_voice.computer.controller import ComputerController


class BuiltInCommands:
    def __init__(self, registry: CommandRegistry, computer: ComputerController | None = None):
        self._registry = registry
        self._computer = computer or ComputerController()
        self._register_all()

    def _register_all(self):
        r = self._registry

        r.register("open terminal", "terminal.open", self._open_terminal, "system")
        r.register("open browser", "browser.open", self._open_browser, "system")
        r.register("open settings", "settings.open", self._open_settings, "system")
        r.register("open file manager", "files.open", self._open_file_manager, "system")
        r.register("open calculator", "calc.open", self._open_calculator, "system")
        r.register("take screenshot", "screenshot.take", self._take_screenshot, "system")
        r.register("show clipboard", "clipboard.show", self._show_clipboard, "system")
        r.register("lock screen", "screen.lock", self._lock_screen, "system", requires_confirm=True)
        r.register("shutdown", "system.shutdown", self._shutdown, "system", requires_confirm=True)
        r.register("restart", "system.restart", self._restart, "system", requires_confirm=True)
        r.register("sleep", "system.sleep", self._sleep, "system", requires_confirm=True)
        r.register("volume up", "volume.up", self._volume_up, "media")
        r.register("volume down", "volume.down", self._volume_down, "media")
        r.register("mute", "volume.mute", self._mute, "media")
        r.register("unmute", "volume.unmute", self._unmute, "media")
        r.register("next track", "media.next", self._next_track, "media")
        r.register("previous track", "media.previous", self._previous_track, "media")
        r.register("play pause", "media.play_pause", self._play_pause, "media")
        r.register("stop listening", "voice.stop", self._stop_listening, "voice")
        r.register("start listening", "voice.start", self._start_listening, "voice")
        r.register("pause listening", "voice.pause", self._pause_listening, "voice")
        r.register("switch to command mode", "mode.command", lambda: "command", "voice")
        r.register("switch to dictation mode", "mode.dictation", lambda: "dictation", "voice")
        r.register("switch to conversation mode", "mode.conversation", lambda: "conversation", "voice")
        r.register("what time is it", "info.time", self._what_time, "info")
        r.register("what is the date", "info.date", self._what_date, "info")
        r.register("clear conversation", "chat.clear", self._clear_chat, "chat", requires_confirm=True)
        r.register("help", "help.show", self._show_help, "info")

    async def _open_terminal(self):
        if self._computer:
            await self._computer.open_app("terminal")
        return "Opening terminal"

    async def _open_browser(self):
        if self._computer:
            await self._computer.open_app("browser")
        return "Opening browser"

    async def _open_settings(self):
        if self._computer:
            await self._computer.open_app("settings")
        return "Opening settings"

    async def _open_file_manager(self):
        if self._computer:
            await self._computer.open_app("file manager")
        return "Opening file manager"

    async def _open_calculator(self):
        if self._computer:
            await self._computer.open_app("calculator")
        return "Opening calculator"

    async def _take_screenshot(self):
        if self._computer:
            return await self._computer.take_screenshot()
        return "Screenshot captured"

    async def _show_clipboard(self):
        if self._computer:
            return await self._computer.get_clipboard_text()
        return "Clipboard content"

    async def _lock_screen(self):
        if self._computer:
            await self._computer.lock_screen()
        return "Screen locked"

    async def _shutdown(self):
        if self._computer:
            await self._computer.shutdown()
        return "Shutting down"

    async def _restart(self):
        if self._computer:
            await self._computer.restart()
        return "Restarting"

    async def _sleep(self):
        if self._computer:
            await self._computer.sleep()
        return "Sleeping"

    async def _volume_up(self):
        if self._computer:
            await self._computer.volume_up()
        return "Volume up"

    async def _volume_down(self):
        if self._computer:
            await self._computer.volume_down()
        return "Volume down"

    async def _mute(self):
        if self._computer:
            await self._computer.mute()
        return "Muted"

    async def _unmute(self):
        if self._computer:
            await self._computer.unmute()
        return "Unmuted"

    async def _next_track(self):
        if self._computer:
            await self._computer.media_next()
        return "Next track"

    async def _previous_track(self):
        if self._computer:
            await self._computer.media_previous()
        return "Previous track"

    async def _play_pause(self):
        if self._computer:
            await self._computer.media_play_pause()
        return "Play/Pause toggled"

    def _stop_listening(self):
        return "Stopped listening"

    def _start_listening(self):
        return "Started listening"

    def _pause_listening(self):
        return "Paused listening"

    async def _what_time(self):
        import datetime
        now = datetime.datetime.now()
        return f"The time is {now.strftime('%I:%M %p')}"

    async def _what_date(self):
        import datetime
        now = datetime.datetime.now()
        return f"Today is {now.strftime('%A, %B %d, %Y')}"

    def _clear_chat(self):
        return "Conversation cleared"

    def _show_help(self):
        cmds = self._registry.list_commands()
        lines = ["Available voice commands:"]
        for c in cmds:
            confirm = " [requires confirmation]" if c.requires_confirm else ""
            lines.append(f"  \"{c.phrase}\" — {c.category}{confirm}")
        return "\n".join(lines)
