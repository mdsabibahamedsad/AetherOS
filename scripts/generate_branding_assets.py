#!/usr/bin/env python3
"""Generate all AetherOS branding assets from the master SVG logo.

This script creates:
- PNG icons in various sizes (16, 32, 64, 128, 256, 512, 1024)
- ICO files for Windows
- ICNS files for macOS (requires iconutil on macOS)
- Favicon variants
- App icons for different platforms

Usage:
    python scripts/generate_branding_assets.py

Requirements:
    - Pillow (PIL)
    - cairosvg (for SVG to PNG conversion)
    - ico tool (optional, for ICO generation)
"""

import os
import sys
from pathlib import Path

try:
    import cairosvg
except ImportError:
    print("Installing cairosvg...")
    os.system(f"{sys.executable} -m pip install cairosvg")
    import cairosvg

try:
    from PIL import Image
except ImportError:
    print("Installing Pillow...")
    os.system(f"{sys.executable} -m pip install Pillow")
    from PIL import Image

# Configuration
ASSETS_DIR = Path(__file__).parent.parent / "assets"
WEBSITE_IMG_DIR = Path(__file__).parent.parent / "website" / "static" / "img"
DESKTOP_ASSETS_DIR = Path(__file__).parent.parent / "apps" / "desktop" / "assets"
BOOTSTRAP_ICONS_DIR = Path(__file__).parent.parent / "apps" / "bootstrap-installer" / "src-tauri" / "icons"
WEB_PUBLIC_DIR = Path(__file__).parent.parent / "web" / "public"
PACKAGING_DIR = Path(__file__).parent.parent / "packaging" / "windows"

# Icon sizes
ICON_SIZES = {
    "favicon-16.png": 16,
    "favicon-32.png": 32,
    "favicon-64.png": 64,
    "icon-128.png": 128,
    "icon-256.png": 256,
    "icon-512.png": 512,
    "icon-1024.png": 1024,
}

# Tauri icon sizes
TAURI_ICON_SIZES = {
    "32x32.png": 32,
    "128x128.png": 128,
    "128x128@2x.png": 256,
}

# Desktop app icon sizes
DESKTOP_ICON_SIZES = {
    "icon.png": 1024,
    "icon-256.png": 256,
    "icon-128.png": 128,
    "icon-64.png": 64,
    "icon-32.png": 32,
    "icon-16.png": 16,
}


def ensure_directories():
    """Ensure all output directories exist."""
    for directory in [
        ASSETS_DIR,
        WEBSITE_IMG_DIR,
        DESKTOP_ASSETS_DIR,
        BOOTSTRAP_ICONS_DIR,
        WEB_PUBLIC_DIR,
        PACKAGING_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def svg_to_png(svg_path: Path, png_path: Path, size: int):
    """Convert SVG to PNG at specified size."""
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(png_path),
        output_width=size,
        output_height=size,
    )
    print(f"  Created {png_path.name} ({size}x{size})")


def create_ico(png_paths: list, ico_path: Path):
    """Create ICO file from PNG images."""
    images = []
    for png_path in png_paths:
        if png_path.exists():
            img = Image.open(png_path)
            images.append(img)
    
    if images:
        # Save as ICO with multiple sizes
        images[0].save(
            ico_path,
            format="ICO",
            sizes=[(img.size[0], img.size[1]) for img in images],
        )
        print(f"  Created {ico_path.name}")


def create_favicon_svg():
    """Create the favicon SVG (simplified wolf head)."""
    favicon_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <defs>
    <linearGradient id="mainGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0066FF;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#00D4FF;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#9933FF;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="eyeGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#00D4FF;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#00FFFF;stop-opacity:1" />
    </linearGradient>
  </defs>
  <circle cx="16" cy="16" r="15" fill="#0A0A0F"/>
  <g transform="translate(16, 16)">
    <path d="M 0,-10 L 5,-6 L 7,-3 L 8,0 L 7,3 L 5,6 L 3,8 L 0,9 L -3,8 L -5,6 L -7,3 L -8,0 L -7,-3 L -5,-6 Z" fill="url(#mainGradient)"/>
    <path d="M -5,-6 L -7,-11 L -3,-8 L -2,-7 L -3,-5 Z" fill="url(#mainGradient)"/>
    <path d="M 5,-6 L 7,-11 L 3,-8 L 2,-7 L 3,-5 Z" fill="url(#mainGradient)"/>
    <ellipse cx="-3" cy="-1" rx="1" ry="0.7" fill="url(#eyeGlow)"/>
    <ellipse cx="3" cy="-1" rx="1" ry="0.7" fill="url(#eyeGlow)"/>
    <path d="M -0.7,6 L 0,7 L 0.7,6 Z" fill="#0A0A0F"/>
  </g>
</svg>"""
    
    favicon_path = ASSETS_DIR / "favicon.svg"
    favicon_path.write_text(favicon_svg, encoding="utf-8")
    print(f"  Created {favicon_path.name}")
    return favicon_path


def generate_main_assets():
    """Generate main logo variants."""
    print("\n=== Generating Main Logo Variants ===")
    
    master_svg = ASSETS_DIR / "logo.svg"
    if not master_svg.exists():
        print(f"Error: Master SVG not found at {master_svg}")
        return
    
    # Generate PNG variants
    for name, size in ICON_SIZES.items():
        png_path = ASSETS_DIR / name
        svg_to_png(master_svg, png_path, size)
    
    # Copy to website
    for name, size in [("logo.png", 512), ("favicon-16x16.png", 16), ("favicon-32x32.png", 32)]:
        png_path = WEBSITE_IMG_DIR / name
        svg_to_png(master_svg, png_path, size)
    
    # Copy Apple touch icon
    apple_touch_path = WEBSITE_IMG_DIR / "apple-touch-icon.png"
    svg_to_png(master_svg, apple_touch_path, 180)
    
    # Copy to desktop assets
    for name, size in DESKTOP_ICON_SIZES.items():
        png_path = DESKTOP_ASSETS_DIR / name
        svg_to_png(master_svg, png_path, size)


def generate_tauri_icons():
    """Generate Tauri installer icons."""
    print("\n=== Generating Tauri Icons ===")
    
    master_svg = ASSETS_DIR / "logo.svg"
    
    for name, size in TAURI_ICON_SIZES.items():
        png_path = BOOTSTRAP_ICONS_DIR / name
        svg_to_png(master_svg, png_path, size)
    
    # Create ICO for Windows
    ico_path = BOOTSTRAP_ICONS_DIR / "icon.ico"
    ico_pngs = [
        BOOTSTRAP_ICONS_DIR / "32x32.png",
        BOOTSTRAP_ICONS_DIR / "128x128.png",
        BOOTSTRAP_ICONS_DIR / "128x128@2x.png",
    ]
    create_ico(ico_pngs, ico_path)
    
    # Create ICNS for macOS (placeholder - requires iconutil on macOS)
    icns_path = BOOTSTRAP_ICONS_DIR / "icon.icns"
    print(f"  Note: {icns_path.name} requires macOS iconutil to generate")


def generate_desktop_icons():
    """Generate desktop application icons."""
    print("\n=== Generating Desktop Icons ===")
    
    master_svg = ASSETS_DIR / "logo.svg"
    
    for name, size in DESKTOP_ICON_SIZES.items():
        png_path = DESKTOP_ASSETS_DIR / name
        svg_to_png(master_svg, png_path, size)
    
    # Create ICO for Windows
    ico_path = DESKTOP_ASSETS_DIR / "icon.ico"
    ico_pngs = [
        DESKTOP_ASSETS_DIR / "icon-16.png",
        DESKTOP_ASSETS_DIR / "icon-32.png",
        DESKTOP_ASSETS_DIR / "icon-64.png",
        DESKTOP_ASSETS_DIR / "icon-128.png",
        DESKTOP_ASSETS_DIR / "icon-256.png",
        DESKTOP_ASSETS_DIR / "icon.png",
    ]
    create_ico(ico_pngs, ico_path)


def generate_web_favicons():
    """Generate web favicons."""
    print("\n=== Generating Web Favicons ===")
    
    favicon_svg = create_favicon_svg()
    
    # Generate favicon PNGs
    for size in [16, 32, 48, 64]:
        png_path = WEB_PUBLIC_DIR / f"favicon-{size}.png"
        svg_to_png(favicon_svg, png_path, size)
    
    # Generate main favicon.ico
    ico_path = WEB_PUBLIC_DIR / "favicon.ico"
    ico_pngs = [
        WEB_PUBLIC_DIR / "favicon-16.png",
        WEB_PUBLIC_DIR / "favicon-32.png",
        WEB_PUBLIC_DIR / "favicon-48.png",
    ]
    create_ico(ico_pngs, ico_path)
    
    # Also copy to website
    website_favicon_ico = WEBSITE_IMG_DIR / "favicon.ico"
    create_ico(ico_pngs, website_favicon_ico)


def generate_packaging_icons():
    """Generate packaging icons."""
    print("\n=== Generating Packaging Icons ===")
    
    master_svg = ASSETS_DIR / "logo.svg"
    
    # Windows icon
    ico_path = PACKAGING_DIR / "icon.ico"
    ico_pngs = [
        ASSETS_DIR / "favicon-16.png",
        ASSETS_DIR / "favicon-32.png",
        ASSETS_DIR / "favicon-64.png",
        ASSETS_DIR / "icon-128.png",
        ASSETS_DIR / "icon-256.png",
    ]
    create_ico(ico_pngs, ico_path)


def main():
    """Main entry point."""
    print("AetherOS Branding Asset Generator")
    print("=" * 50)
    
    ensure_directories()
    
    generate_main_assets()
    generate_tauri_icons()
    generate_desktop_icons()
    generate_web_favicons()
    generate_packaging_icons()
    
    print("\n" + "=" * 50)
    print("✓ All branding assets generated successfully!")
    print("\nNext steps:")
    print("1. Review the generated assets")
    print("2. Update any remaining references in code")
    print("3. Test the icons in your application")


if __name__ == "__main__":
    main()
