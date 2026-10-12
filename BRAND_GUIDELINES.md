# AetherOS Brand Guidelines

## Brand Identity

**AetherOS** is a premium AI Operating System with a distinctive visual identity centered around a wolf-inspired geometric symbol.

## Logo

### Primary Logo
The primary logo features a geometric wolf head with:
- **Blue → Cyan → Purple gradient** (top-left to bottom-right)
- **Sharp, aggressive edges** representing precision and power
- **Glowing cyan eyes** symbolizing intelligence and awareness
- **Circular outer ring** providing containment and unity

### Logo Variants
- `logo.svg` - Master SVG with text and tagline
- `logo-dark.svg` - For dark backgrounds
- `logo-light.svg` - For light backgrounds
- `logo-white.svg` - White version for dark UI elements
- `logo-black.svg` - Black version for light UI elements

### Icon Sizes
- `favicon-16.png` - Browser tab
- `favicon-32.png` - Standard favicon
- `favicon-64.png` - High-DPI favicon
- `icon-128.png` - Small application icon
- `icon-256.png` - Medium application icon
- `icon-512.png` - Large application icon
- `icon-1024.png` - High-resolution icon

## Color Palette

### Primary Colors
- **Blue**: `#0066FF` - Primary brand color
- **Cyan**: `#00D4FF` - Accent and eye glow
- **Purple**: `#9933FF` - Secondary accent

### Background Colors
- **Dark**: `#0A0A0F` - Primary dark background
- **Light**: `#FFFFFF` - Light mode background

### Text Colors
- **Primary Text**: `#E6EDF3` - Main text on dark backgrounds
- **Secondary Text**: `#888888` - Muted text and taglines
- **Accent Text**: Uses gradient colors for emphasis

## Typography

### Brand Name
- **Font**: System UI stack (`'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif`)
- **Weight**: 700 (Bold)
- **Size**: 48px (scales with context)
- **Letter Spacing**: 2px

### Tagline
- **Font**: Same as brand name
- **Weight**: 400 (Regular)
- **Size**: 18px
- **Letter Spacing**: 4px
- **Color**: `#888888`

## Spacing Rules

```
Logo (wolf icon)
    ↓ 24px
AetherOS (brand name)
    ↓ 12px
AI Operating System (tagline)
```

## Usage Rules

### Do
- Use the official SVG files as source of truth
- Maintain aspect ratio when scaling
- Use appropriate variant for background (dark/light)
- Keep minimum clear space around logo
- Use provided color palette

### Don't
- Rotate the logo
- Stretch or distort proportions
- Change the gradient colors
- Add effects not in the original
- Recreate from scratch
- Crop the logo
- Use low-resolution versions for print

## File Locations

### Master Assets
- `assets/logo.svg` - Master SVG
- `assets/logo-dark.svg` - Dark variant
- `assets/logo-light.svg` - Light variant
- `assets/logo-white.svg` - White variant
- `assets/logo-black.svg` - Black variant

### Website
- `website/static/img/logo.png` - Website logo
- `website/static/img/favicon.svg` - Website favicon SVG
- `website/static/img/favicon.ico` - Website favicon ICO
- `website/static/img/favicon-16x16.png` - 16px favicon
- `website/static/img/favicon-32x32.png` - 32px favicon
- `website/static/img/apple-touch-icon.png` - Apple touch icon

### Desktop Application
- `apps/desktop/assets/icon.png` - Main app icon
- `apps/desktop/assets/icon.ico` - Windows ICO
- `apps/desktop/assets/icon.icns` - macOS ICNS

### Bootstrap Installer (Tauri)
- `apps/bootstrap-installer/src-tauri/icons/32x32.png`
- `apps/bootstrap-installer/src-tauri/icons/128x128.png`
- `apps/bootstrap-installer/src-tauri/icons/128x128@2x.png`
- `apps/bootstrap-installer/src-tauri/icons/icon.ico`
- `apps/bootstrap-installer/src-tauri/icons/icon.icns`

### Packaging
- `packaging/windows/icon.ico` - Windows installer icon

### Web Application
- `web/public/favicon.ico`
- `web/public/favicon-16.png`
- `web/public/favicon-32.png`
- `web/public/favicon-48.png`
- `web/public/favicon-64.png`

## ASCII Art for CLI

The CLI uses ASCII art representations defined in `aetheros_cli/ascii_logo.py`:
- `WOLF_LOGO_DETAILED` - Full detailed ASCII art
- `WOLF_LOGO_COMPACT` - Compact version
- `WOLF_ICON_MINIMAL` - Minimal icon for small terminals

## Brand Voice

- **Premium**: High-quality, polished appearance
- **Futuristic**: Cutting-edge technology feel
- **Minimal**: Clean, uncluttered design
- **Aggressive**: Sharp edges, bold presence
- **Intelligent**: Glowing eyes, AI-focused

## Asset Generation

To regenerate all assets from the master SVG:
```bash
python scripts/generate_branding_simple.py
```

## Version Control

All branding assets should be committed to version control. When updating:
1. Update the master SVG in `assets/`
2. Run the generation script
3. Test across all platforms
4. Commit all changes together
