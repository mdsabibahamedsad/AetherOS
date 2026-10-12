# Computer Use System

The Computer Use system enables secure AI-driven desktop interaction when explicitly enabled and permitted by the user.

## Architecture

```
aetheros_automation/browser_automation/computer_use_manager.py
```

The `ComputerUseManager` wraps desktop automation libraries behind a permission-gated interface.

## Capabilities

| Action | Library | Permission Required |
|--------|---------|-------------------|
| Screen Capture | pyautogui | screenshot |
| Mouse Click | pyautogui | click |
| Mouse Move | pyautogui | move_mouse |
| Drag & Drop | pyautogui | drag_drop |
| Keyboard Typing | pyautogui | type |
| Keyboard Shortcuts | pyautogui | keyboard_shortcut |
| Scroll | pyautogui | scroll |
| Window Detection | pygetwindow / PowerShell | detect_windows |
| Window Focus | pygetwindow / PowerShell | focus_window |
| Screen Info | pyautogui | get_screen_info (always allowed) |

## Security Model

1. **Opt-in**: Computer use is disabled by default. User must explicitly enable.
2. **Per-action permissions**: Every action requires a specific permission grant.
3. **Duration control**: Permissions can be granted for once, session, or permanent.
4. **Revocation**: All non-permanent grants are revoked on disable.
5. **Desktop actions always require approval**: High/critical risk actions always need user consent.

## Usage

```python
from aetheros_automation.browser_automation import ComputerUseManager

cu = ComputerUseManager()
cu.enable()
cu.grant_permission(ComputerAction.SCREENSHOT, "session")
screenshot = await cu.take_screenshot()
```

## Cross-Platform

- Windows: pyautogui + pygetwindow + PowerShell
- Linux: pyautogui + pygetwindow (X11/Wayland)
- macOS: pyautogui + pygetwindow

All platform-specific code is isolated; no hardcoded platform assumptions.
