"""AetherOS ASCII art logo for CLI branding.

This module provides ASCII art representations of the AetherOS wolf logo
for use in terminal displays, CLI banners, and text-based interfaces.
"""

# ANSI color codes for the AetherOS brand
BLUE = "\033[38;2;0;102;255m"
CYAN = "\033[38;2;0;212;255m"
PURPLE = "\033[38;2;153;51;255m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Main ASCII art wolf logo - compact version
WOLF_LOGO_COMPACT = f"""{BLUE}    /\\{RESET}
{BLUE}   /  \\{RESET}{CYAN}   /\\{RESET}
{BLUE}  /    \\{RESET}{CYAN} /  \\{RESET}
{BLUE} /  /\\  \\{RESET}{CYAN}/    \\{RESET}
{BLUE}/  /  \\  \\{RESET}{PURPLE}/  /\\  \\{RESET}
{BLUE}\\  \\  /  /{RESET}{PURPLE}\\  \\  /{RESET}
{BLUE} \\  \\/  /{RESET}{PURPLE}  \\  \\/{RESET}
{BLUE}  \\    /{RESET}{PURPLE}    \\{RESET}
{BLUE}   \\  /{RESET}
{BLUE}    \\/{RESET}"""

# Main ASCII art wolf logo - detailed version
WOLF_LOGO_DETAILED = f"""{BLUE}           /\\      /\\{RESET}
{BLUE}          /  \\    /  \\{RESET}
{BLUE}         /    \\  /    \\{RESET}
{BLUE}        /  /\\  \\/  /\\  \\{RESET}
{BLUE}       /  /  \\    /  \\  \\{RESET}
{BLUE}      /  /    \\  /    \\  \\{RESET}
{BLUE}     /  /      \\/      \\  \\{RESET}
{BLUE}    /  /                \\  \\{RESET}
{BLUE}   /  /                  \\  \\{RESET}
{BLUE}  /  /                    \\  \\{RESET}
{BLUE} /  /                      \\  \\{RESET}
{BLUE}/  /                        \\  \\{RESET}
{BLUE}\\  \\                        /  /{RESET}
{BLUE} \\  \\                      /  /{RESET}
{BLUE}  \\  \\                    /  /{RESET}
{BLUE}   \\  \\                  /  /{RESET}
{BLUE}    \\  \\                /  /{RESET}
{BLUE}     \\  \\              /  /{RESET}
{BLUE}      \\  \\            /  /{RESET}
{BLUE}       \\  \\          /  /{RESET}
{BLUE}        \\  \\        /  /{RESET}
{BLUE}         \\  \\      /  /{RESET}
{BLUE}          \\  \\    /  /{RESET}
{BLUE}           \\  \\  /  /{RESET}
{BLUE}            \\  \\/  /{RESET}
{BLUE}             \\    /{RESET}
{BLUE}              \\  /{RESET}
{BLUE}               \\/{RESET}"""

# Minimal wolf icon for small terminals
WOLF_ICON_MINIMAL = f"""{BLUE}/{RESET}{CYAN}|\\{RESET}{PURPLE}/{RESET}
{BLUE}/{RESET}{CYAN}| \\{RESET}{PURPLE}/{RESET}
{BLUE}\\{RESET}{CYAN}|_{RESET}{PURPLE}/{RESET}"""

# Brand text with gradient effect
def get_brand_text():
    """Return the AetherOS brand text with gradient colors."""
    text = "AetherOS"
    colored = ""
    colors = [BLUE, BLUE, CYAN, CYAN, CYAN, PURPLE, PURPLE, PURPLE]
    for i, char in enumerate(text):
        if i < len(colors):
            colored += f"{colors[i]}{char}"
        else:
            colored += char
    return colored + RESET


def get_tagline():
    """Return the tagline with styling."""
    return f"{DIM}AI Operating System{RESET}"


def get_full_banner(model=None, context_length=None):
    """Get the full AetherOS CLI banner.
    
    Args:
        model: Optional model name to display
        context_length: Optional context length to display
    
    Returns:
        Formatted banner string with ASCII art and info
    """
    banner_lines = []
    
    # Add logo
    banner_lines.append(WOLF_LOGO_DETAILED)
    banner_lines.append("")
    
    # Add brand name with gradient
    banner_lines.append(f"  {BOLD}{get_brand_text()}{RESET}")
    banner_lines.append(f"  {get_tagline()}")
    banner_lines.append("")
    
    # Add model info if provided
    if model:
        model_short = model.split("/")[-1] if "/" in model else model
        if len(model_short) > 40:
            model_short = model_short[:37] + "..."
        banner_lines.append(f"  {CYAN}Model{RESET}")
        banner_lines.append(f"  {model_short}")
        banner_lines.append("")
    
    # Add context length if provided
    if context_length:
        banner_lines.append(f"  {CYAN}Context{RESET}")
        banner_lines.append(f"  {context_length} tokens")
        banner_lines.append("")
    
    # Add ready message
    banner_lines.append(f"  {DIM}Ready.{RESET}")
    
    return "\n".join(banner_lines)


def get_compact_banner():
    """Get a compact version of the banner for narrow terminals."""
    return f"{WOLF_ICON_MINIMAL}  {BOLD}{get_brand_text()}{RESET} {DIM}Ready.{RESET}"


def get_splash_screen():
    """Get the splash screen content."""
    lines = [
        "",
        "",
        WOLF_LOGO_DETAILED,
        "",
        f"  {BOLD}{get_brand_text()}{RESET}",
        f"  {get_tagline()}",
        "",
        f"  {DIM}Loading...{RESET}",
        "",
    ]
    return "\n".join(lines)


# Export for use in other modules
__all__ = [
    "WOLF_LOGO_COMPACT",
    "WOLF_LOGO_DETAILED",
    "WOLF_ICON_MINIMAL",
    "get_brand_text",
    "get_tagline",
    "get_full_banner",
    "get_compact_banner",
    "get_splash_screen",
]
