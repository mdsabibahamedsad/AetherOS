#!/usr/bin/env python3
"""Generate AetherOS branding assets using PIL directly.

This script creates PNG icons in various sizes by drawing the wolf logo
directly using PIL, without requiring cairosvg.
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

# Configuration
ASSETS_DIR = Path(__file__).parent.parent / "assets"
WEBSITE_IMG_DIR = Path(__file__).parent.parent / "website" / "static" / "img"
DESKTOP_ASSETS_DIR = Path(__file__).parent.parent / "apps" / "desktop" / "assets"
BOOTSTRAP_ICONS_DIR = Path(__file__).parent.parent / "apps" / "bootstrap-installer" / "src-tauri" / "icons"
WEB_PUBLIC_DIR = Path(__file__).parent.parent / "web" / "public"
PACKAGING_DIR = Path(__file__).parent.parent / "packaging" / "windows"

# Brand colors
BLUE = (0, 102, 255)
CYAN = (0, 212, 255)
PURPLE = (153, 51, 255)
DARK_BG = (10, 10, 15)


def interpolate_color(color1, color2, t):
    """Linearly interpolate between two RGB colors."""
    return tuple(int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1, color2))


def get_gradient_color(x, y, size):
    """Get gradient color based on position."""
    t = (x + y) / (2 * size)
    if t < 0.5:
        return interpolate_color(BLUE, CYAN, t * 2)
    else:
        return interpolate_color(CYAN, PURPLE, (t - 0.5) * 2)


def draw_wolf_logo(img_size=512, with_text=True, dark_bg=True):
    """Draw the AetherOS wolf logo."""
    # Create image
    if dark_bg:
        img = Image.new('RGBA', (img_size, img_size), DARK_BG + (255,))
    else:
        img = Image.new('RGBA', (img_size, img_size), (255, 255, 255, 0))
    
    draw = ImageDraw.Draw(img)
    
    # Scale factor
    scale = img_size / 512
    center = img_size // 2
    
    # Draw outer ring
    ring_radius = int(220 * scale)
    ring_width = int(4 * scale)
    for i in range(ring_width):
        r = ring_radius - i
        for angle in range(360):
            rad = math.radians(angle)
            x = center + int(r * math.cos(rad))
            y = center + int(r * math.sin(rad))
            color = get_gradient_color(x, y, img_size)
            draw.point((x, y), fill=color + (153,))
    
    # Draw wolf head (simplified geometric shape)
    def draw_polygon(points, fill_color):
        """Draw a filled polygon with gradient."""
        scaled_points = [(int(x * scale + center), int(y * scale + center)) for x, y in points]
        # Create a temporary image for the polygon
        poly_img = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
        poly_draw = ImageDraw.Draw(poly_img)
        poly_draw.polygon(scaled_points, fill=fill_color)
        return poly_img
    
    # Main head shape
    head_points = [
        (0, -120), (60, -80), (80, -40), (100, 0),
        (90, 40), (60, 80), (30, 100), (0, 110),
        (-30, 100), (-60, 80), (-90, 40), (-100, 0),
        (-80, -40), (-60, -80)
    ]
    
    # Create gradient fill for head
    head_img = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
    head_draw = ImageDraw.Draw(head_img)
    scaled_head = [(int(x * scale + center), int(y * scale + center)) for x, y in head_points]
    head_draw.polygon(scaled_head, fill=BLUE + (255,))
    
    # Apply gradient to head
    for x in range(img_size):
        for y in range(img_size):
            if head_img.getpixel((x, y))[3] > 0:
                color = get_gradient_color(x, y, img_size)
                head_img.putpixel((x, y), color + (255,))
    
    img = Image.alpha_composite(img, head_img)
    draw = ImageDraw.Draw(img)
    
    # Left ear
    ear_points = [(-60, -80), (-80, -140), (-40, -100), (-20, -90), (-40, -70)]
    ear_img = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
    ear_draw = ImageDraw.Draw(ear_img)
    scaled_ear = [(int(x * scale + center), int(y * scale + center)) for x, y in ear_points]
    ear_draw.polygon(scaled_ear, fill=BLUE + (255,))
    for x in range(img_size):
        for y in range(img_size):
            if ear_img.getpixel((x, y))[3] > 0:
                color = get_gradient_color(x, y, img_size)
                ear_img.putpixel((x, y), color + (255,))
    img = Image.alpha_composite(img, ear_img)
    
    # Right ear
    ear_points = [(60, -80), (80, -140), (40, -100), (20, -90), (40, -70)]
    ear_img = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
    ear_draw = ImageDraw.Draw(ear_img)
    scaled_ear = [(int(x * scale + center), int(y * scale + center)) for x, y in ear_points]
    ear_draw.polygon(scaled_ear, fill=BLUE + (255,))
    for x in range(img_size):
        for y in range(img_size):
            if ear_img.getpixel((x, y))[3] > 0:
                color = get_gradient_color(x, y, img_size)
                ear_img.putpixel((x, y), color + (255,))
    img = Image.alpha_composite(img, ear_img)
    
    # Snout
    snout_points = [(-40, 20), (-30, 60), (0, 80), (30, 60), (40, 20), (20, 40), (0, 50), (-20, 40)]
    snout_img = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
    snout_draw = ImageDraw.Draw(snout_img)
    scaled_snout = [(int(x * scale + center), int(y * scale + center)) for x, y in snout_points]
    snout_draw.polygon(scaled_snout, fill=BLUE + (230,))
    for x in range(img_size):
        for y in range(img_size):
            if snout_img.getpixel((x, y))[3] > 0:
                color = get_gradient_color(x, y, img_size)
                snout_img.putpixel((x, y), color + (230,))
    img = Image.alpha_composite(img, snout_img)
    
    # Eyes (cyan glow)
    eye_radius_x = int(12 * scale)
    eye_radius_y = int(8 * scale)
    
    # Left eye
    left_eye_x = center - int(35 * scale)
    left_eye_y = center - int(10 * scale)
    draw.ellipse(
        [left_eye_x - eye_radius_x, left_eye_y - eye_radius_y,
         left_eye_x + eye_radius_x, left_eye_y + eye_radius_y],
        fill=CYAN + (255,)
    )
    
    # Right eye
    right_eye_x = center + int(35 * scale)
    right_eye_y = center - int(10 * scale)
    draw.ellipse(
        [right_eye_x - eye_radius_x, right_eye_y - eye_radius_y,
         right_eye_x + eye_radius_x, right_eye_y + eye_radius_y],
        fill=CYAN + (255,)
    )
    
    # Nose
    nose_points = [(-8, 65), (0, 75), (8, 65)]
    scaled_nose = [(int(x * scale + center), int(y * scale + center)) for x, y in nose_points]
    draw.polygon(scaled_nose, fill=DARK_BG + (255,))
    
    # Add text if requested
    if with_text and img_size >= 256:
        try:
            # Try to use a nice font
            font_large = ImageFont.truetype("arial.ttf", int(48 * scale))
            font_small = ImageFont.truetype("arial.ttf", int(18 * scale))
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Brand name
        text_y = center + int(170 * scale)
        draw.text((center, text_y), "AetherOS", font=font_large, fill=BLUE + (255,), anchor="mm")
        
        # Tagline
        tagline_y = text_y + int(50 * scale)
        draw.text((center, tagline_y), "AI OPERATING SYSTEM", font=font_small, fill=(136, 136, 136, 255), anchor="mm")
    
    return img


def draw_favicon(size=32):
    """Draw a simplified favicon."""
    img = Image.new('RGBA', (size, size), DARK_BG + (255,))
    draw = ImageDraw.Draw(img)
    
    scale = size / 32
    center = size // 2
    
    # Simplified wolf head
    head_points = [
        (0, -10), (5, -6), (7, -3), (8, 0),
        (7, 3), (5, 6), (3, 8), (0, 9),
        (-3, 8), (-5, 6), (-7, 3), (-8, 0),
        (-7, -3), (-5, -6)
    ]
    scaled_head = [(int(x * scale + center), int(y * scale + center)) for x, y in head_points]
    draw.polygon(scaled_head, fill=BLUE + (255,))
    
    # Ears
    left_ear = [(-5, -6), (-7, -11), (-3, -8), (-2, -7), (-3, -5)]
    scaled_left_ear = [(int(x * scale + center), int(y * scale + center)) for x, y in left_ear]
    draw.polygon(scaled_left_ear, fill=BLUE + (255,))
    
    right_ear = [(5, -6), (7, -11), (3, -8), (2, -7), (3, -5)]
    scaled_right_ear = [(int(x * scale + center), int(y * scale + center)) for x, y in right_ear]
    draw.polygon(scaled_right_ear, fill=BLUE + (255,))
    
    # Eyes
    eye_rx = max(1, int(1 * scale))
    eye_ry = max(1, int(0.7 * scale))
    draw.ellipse([center - int(3*scale) - eye_rx, center - int(1*scale) - eye_ry,
                  center - int(3*scale) + eye_rx, center - int(1*scale) + eye_ry], fill=CYAN + (255,))
    draw.ellipse([center + int(3*scale) - eye_rx, center - int(1*scale) - eye_ry,
                  center + int(3*scale) + eye_rx, center - int(1*scale) + eye_ry], fill=CYAN + (255,))
    
    # Nose
    nose_points = [(-0.7, 6), (0, 7), (0.7, 6)]
    scaled_nose = [(int(x * scale + center), int(y * scale + center)) for x, y in nose_points]
    draw.polygon(scaled_nose, fill=DARK_BG + (255,))
    
    return img


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


def save_image(img, path, format="PNG"):
    """Save image, converting RGBA to RGB for ICO."""
    if format == "ICO":
        # ICO doesn't support RGBA, convert to RGB with black background
        rgb_img = Image.new('RGB', img.size, DARK_BG)
        rgb_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
        rgb_img.save(path, format=format)
    else:
        img.save(path, format=format)


def main():
    """Main entry point."""
    print("AetherOS Branding Asset Generator (Simple Version)")
    print("=" * 50)
    
    ensure_directories()
    
    # Generate main logo variants
    print("\n=== Generating Main Logo Variants ===")
    
    # Master SVG (already created manually)
    print("  Master SVG already exists: assets/logo.svg")
    
    # Generate PNG variants with text
    sizes_with_text = {
        "logo.png": 512,
        "icon-1024.png": 1024,
        "icon-512.png": 512,
        "icon-256.png": 256,
        "icon-128.png": 128,
    }
    
    for name, size in sizes_with_text.items():
        img = draw_wolf_logo(size, with_text=True, dark_bg=True)
        save_image(img, ASSETS_DIR / name)
        print(f"  Created {name} ({size}x{size})")
    
    # Generate icon-only variants (no text)
    sizes_icon_only = {
        "favicon-64.png": 64,
        "favicon-32.png": 32,
        "favicon-16.png": 16,
    }
    
    for name, size in sizes_icon_only.items():
        img = draw_wolf_logo(size, with_text=False, dark_bg=True)
        save_image(img, ASSETS_DIR / name)
        print(f"  Created {name} ({size}x{size})")
    
    # Generate dark/light/white/black variants
    for variant, dark_bg in [("dark", True), ("light", False)]:
        img = draw_wolf_logo(512, with_text=True, dark_bg=dark_bg)
        save_image(img, ASSETS_DIR / f"logo-{variant}.png")
        print(f"  Created logo-{variant}.png")
    
    # Generate website assets
    print("\n=== Generating Website Assets ===")
    
    # Website logo
    img = draw_wolf_logo(512, with_text=True, dark_bg=True)
    save_image(img, WEBSITE_IMG_DIR / "logo.png")
    print("  Created website/static/img/logo.png")
    
    # Website favicons
    for size in [16, 32]:
        img = draw_favicon(size)
        save_image(img, WEBSITE_IMG_DIR / f"favicon-{size}x{size}.png")
        print(f"  Created website/static/img/favicon-{size}x{size}.png")
    
    # Apple touch icon
    img = draw_wolf_logo(180, with_text=False, dark_bg=True)
    save_image(img, WEBSITE_IMG_DIR / "apple-touch-icon.png")
    print("  Created website/static/img/apple-touch-icon.png")
    
    # Generate desktop app assets
    print("\n=== Generating Desktop App Assets ===")
    
    img = draw_wolf_logo(1024, with_text=False, dark_bg=True)
    save_image(img, DESKTOP_ASSETS_DIR / "icon.png")
    print("  Created apps/desktop/assets/icon.png")
    
    # Desktop ICO
    ico_img = draw_wolf_logo(256, with_text=False, dark_bg=True)
    save_image(ico_img, DESKTOP_ASSETS_DIR / "icon.ico", format="ICO")
    print("  Created apps/desktop/assets/icon.ico")
    
    # Generate Tauri installer assets
    print("\n=== Generating Tauri Installer Assets ===")
    
    for name, size in [("32x32.png", 32), ("128x128.png", 128), ("128x128@2x.png", 256)]:
        img = draw_wolf_logo(size, with_text=False, dark_bg=True)
        save_image(img, BOOTSTRAP_ICONS_DIR / name)
        print(f"  Created apps/bootstrap-installer/src-tauri/icons/{name}")
    
    # Tauri ICO
    ico_img = draw_wolf_logo(256, with_text=False, dark_bg=True)
    save_image(ico_img, BOOTSTRAP_ICONS_DIR / "icon.ico", format="ICO")
    print("  Created apps/bootstrap-installer/src-tauri/icons/icon.ico")
    
    # Generate web public favicons
    print("\n=== Generating Web Public Favicons ===")
    
    for size in [16, 32, 48, 64]:
        img = draw_favicon(size)
        save_image(img, WEB_PUBLIC_DIR / f"favicon-{size}.png")
        print(f"  Created web/public/favicon-{size}.png")
    
    # Web ICO
    ico_img = draw_favicon(48)
    save_image(ico_img, WEB_PUBLIC_DIR / "favicon.ico", format="ICO")
    print("  Created web/public/favicon.ico")
    
    # Generate packaging assets
    print("\n=== Generating Packaging Assets ===")
    
    ico_img = draw_wolf_logo(256, with_text=False, dark_bg=True)
    save_image(ico_img, PACKAGING_DIR / "icon.ico", format="ICO")
    print("  Created packaging/windows/icon.ico")
    
    print("\n" + "=" * 50)
    print("✓ All branding assets generated successfully!")
    print("\nAssets created:")
    print("  - Main logo variants (logo.png, logo-dark.png, logo-light.png)")
    print("  - Icon sizes (16, 32, 64, 128, 256, 512, 1024)")
    print("  - Website favicons and logos")
    print("  - Desktop app icons")
    print("  - Tauri installer icons")
    print("  - Web public favicons")
    print("  - Windows packaging icons")


if __name__ == "__main__":
    main()
