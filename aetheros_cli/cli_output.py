"""AetherOS CLI output helpers — minimal, clean, professional.
"""

from aetheros_cli.colors import Colors, color
from aetheros_cli.secret_prompt import masked_secret_prompt


# ─── Print Helpers ────────────────────────────────────────────────────────────


def print_info(text: str) -> None:
    """Print a dim informational message."""
    print(color(f"  {text}", Colors.GRAY))


def print_success(text: str) -> None:
    """Print a success message."""
    print(color(f"  {text}", Colors.SUCCESS))


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(color(f"  {text}", Colors.WARN))


def print_error(text: str) -> None:
    """Print an error message."""
    print(color(f"  {text}", Colors.ERROR))


def print_header(text: str) -> None:
    """Print a header."""
    print(color(f"\n  {text}", Colors.BLUE))


# ─── Input Prompts ────────────────────────────────────────────────────────────


def prompt(
    question: str,
    default: str | None = None,
    password: bool = False,
) -> str:
    """Prompt the user for input with optional default and password masking.

    Replaces the four independent ``_prompt()`` / ``prompt()`` implementations
    in setup.py, tools_config.py, mcp_config.py, and memory_setup.py.

    Returns the user's input (stripped), or *default* if the user presses Enter.
    Returns empty string on Ctrl-C or EOF.
    """
    suffix = f" [{default}]" if default else ""
    display = color(f"  {question}{suffix}: ", Colors.CYAN)

    try:
        if password:
            value = masked_secret_prompt(display)
        else:
            value = input(display)
        value = value.strip()
        return value if value else (default or "")
    except (KeyboardInterrupt, EOFError):
        print()
        return ""


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt for a yes/no answer. Returns bool."""
    hint = "Y/n" if default else "y/N"
    answer = prompt(f"{question} ({hint})")
    if not answer:
        return default
    return answer.lower().startswith("y")
