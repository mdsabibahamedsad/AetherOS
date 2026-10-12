from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from typing import Optional

log = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self):
        self._platform = sys.platform
        self._toast_notifier = None
        self._use_toast_notifier = False
        self._plyer = None
        self._use_plyer = False
        self._init_backend()

    def _init_backend(self):
        if self._platform == "win32":
            try:
                from win10toast import ToastNotifier
                self._toast_notifier = ToastNotifier()
                self._use_toast_notifier = True
                log.debug("NotificationManager: using win10toast")
                return
            except ImportError:
                pass

            try:
                from plyer import notification as plyer_notify
                self._plyer = plyer_notify
                self._use_plyer = True
                log.debug("NotificationManager: using plyer")
                return
            except ImportError:
                pass

        elif self._platform == "darwin":
            try:
                from plyer import notification as plyer_notify
                self._plyer = plyer_notify
                self._use_plyer = True
                log.debug("NotificationManager: using plyer")
                return
            except ImportError:
                pass
        else:
            try:
                from plyer import notification as plyer_notify
                self._plyer = plyer_notify
                self._use_plyer = True
                log.debug("NotificationManager: using plyer")
                return
            except ImportError:
                pass

        log.debug("NotificationManager: using subprocess fallback")

    def send(self, title: str, message: str, urgency: str = "normal"):
        if self._use_toast_notifier:
            self._toast_notifier.show_toast(title, message, duration=5, threaded=True)
        elif self._use_plyer:
            self._plyer.notify(title=title, message=message, timeout=5)
        elif self._platform == "win32":
            self._send_win32_fallback(title, message)
        elif self._platform == "darwin":
            self._send_macos(title, message)
        else:
            self._send_linux(title, message, urgency)

    def _send_win32_fallback(self, title: str, message: str):
        escaped_title = title.replace("'", "''").replace('"', '`"')
        escaped_msg = message.replace("'", "''").replace('"', '`"')
        ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms;
$notify = New-Object System.Windows.Forms.NotifyIcon;
$notify.Icon = [System.Drawing.SystemIcons]::Information;
$notify.BalloonTipTitle = "{escaped_title}";
$notify.BalloonTipText = "{escaped_msg}";
$notify.Visible = $true;
$notify.ShowBalloonTip(5000);
Start-Sleep -Seconds 5;
$notify.Dispose()
'''
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
        except (FileNotFoundError, OSError) as e:
            log.warning("Failed to send Windows notification: %s", e)

    def _send_macos(self, title: str, message: str):
        try:
            script = f'display notification "{message}" with title "{title}"'
            subprocess.Popen(["osascript", "-e", script])
        except (FileNotFoundError, OSError) as e:
            log.warning("Failed to send macOS notification: %s", e)

    def _send_linux(self, title: str, message: str, urgency: str = "normal"):
        if shutil.which("notify-send"):
            try:
                subprocess.Popen(
                    ["notify-send", f"--urgency={urgency}", title, message]
                )
                return
            except (FileNotFoundError, OSError) as e:
                log.warning("notify-send failed: %s", e)

        log.info("Desktop notification: [%s] %s - %s", urgency, title, message)
