"""AetherOS Design System — color palette.

A premium, minimal, dark-first palette using only:
white, gray, blue, cyan, purple accents.

No yellow. No orange. No rainbow.
"""

import os
import sys


def should_use_color() -> bool:
    """Return True when colored output is appropriate.

    Respects NO_COLOR and TERM=dumb.
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    if not sys.stdout.isatty():
        return False
    return True


def color(text: str, *codes) -> str:
    """Apply color codes to text (only when color output is appropriate)."""
    if not should_use_color():
        return text
    return "".join(codes) + text + Colors.RESET


class Colors:
    """AetherOS Design System ANSI colors.

    Palette: white, gray, blue, cyan, purple.
    """
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"

    # Core palette
    WHITE = "\033[38;2;230;237;243m"
    GRAY = "\033[38;2;139;148;158m"
    GRAY_DIM = "\033[38;2;100;106;115m"
    BLUE = "\033[38;2;88;166;255m"
    CYAN = "\033[38;2;57;210;192m"
    PURPLE = "\033[38;2;188;140;255m"

    # Semantic
    SUCCESS = "\033[38;2;87;210;160m"
    ERROR = "\033[38;2;255;107;107m"
    WARN = "\033[38;2;255;193;100m"
    INFO = "\033[38;2;139;148;158m"

    # Legacy aliases — callers that predate the semantic palette.
    RED = ERROR
    GREEN = SUCCESS
    YELLOW = WARN
    MAGENTA = PURPLE

    # Backgrounds
    BG_DARK = "\033[48;2;13;17;23m"
    BG_MID = "\033[48;2;22;27;34m"
    BG_HIGHLIGHT = "\033[48;2;30;36;48m"

    @classmethod
    def hex_fg(cls, hex_color: str) -> str:
        """Convert a hex color to an ANSI foreground escape."""
        if len(hex_color) == 7 and hex_color[0] == "#":
            try:
                r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
                return f"\033[38;2;{r};{g};{b}m"
            except ValueError:
                pass
        return cls.WHITE

    @classmethod
    def hex_bg(cls, hex_color: str) -> str:
        """Convert a hex color to an ANSI background escape."""
        if len(hex_color) == 7 and hex_color[0] == "#":
            try:
                r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
                return f"\033[48;2;{r};{g};{b}m"
            except ValueError:
                pass
        return cls.BG_DARK
