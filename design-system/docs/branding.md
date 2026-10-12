# AetherOS Branding Guidelines

## Overview

The AetherOS brand identity represents a premium AI Operating System. Every use of the brand must maintain consistency and quality.

## Logo

### Primary Logo
The primary logo consists of:
1. Wolf icon (geometric, gradient)
2. Brand name "AetherOS"
3. Tagline "AI Operating System"

### Logo Variants
| Variant | Usage |
|---------|-------|
| Full Color | Default on dark backgrounds |
| White | On light backgrounds |
| Black | On light backgrounds (alternative) |
| Monochrome | Single-color applications |

### Minimum Size
| Context | Minimum Width |
|---------|---------------|
| Digital | 32px |
| Print | 10mm |
| Favicon | 16px |

### Safe Area
Maintain clear space around the logo equal to the height of the "A" in "AetherOS".

### Dark Background Usage
```css
.logo-dark {
  /* Use full color logo on dark backgrounds */
  filter: none;
}
```

### Light Background Usage
```css
.logo-light {
  /* Use white or black logo on light backgrounds */
  filter: brightness(0) invert(1);
}
```

### Monochrome Usage
```css
.logo-mono {
  /* Use monochrome logo for single-color applications */
  filter: grayscale(1);
}
```

## Colors

### Primary Colors
| Color | Hex | Usage |
|-------|-----|-------|
| Blue | #0066FF | Primary brand color |
| Cyan | #00D4FF | Secondary brand color |
| Purple | #9933FF | Accent brand color |

### Gradient
```css
.brand-gradient {
  background: linear-gradient(135deg, #0066FF 0%, #00D4FF 50%, #9933FF 100%);
}
```

### Gradient Rules
- Use gradients sparingly for emphasis
- Never stretch or distort gradients
- Maintain consistent angle (135deg)
- Ensure sufficient contrast

## Typography

### Brand Font
```css
--font-brand: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
```

### Usage
- **Bold (700)**: Logo, headings
- **Semibold (600)**: Subheadings, labels
- **Medium (500)**: Button labels, navigation
- **Regular (400)**: Body text

## Spacing

### Logo Spacing
```css
.logo-spacing {
  padding: 24px; /* var(--space-6) */
}
```

### Minimum Padding
- Horizontal: 16px
- Vertical: 16px

## Iconography

### Icon Style
- Stroke width: 1.5px
- Corner radius: 2px
- Grid size: 24px
- Padding: 2px

### Icon Sizes
| Size | Pixels | Usage |
|------|--------|-------|
| xs | 16px | Inline text |
| sm | 20px | Compact UI |
| md | 24px | Default |
| lg | 32px | Large UI |
| xl | 48px | Hero sections |

## Forbidden Usage

### Don't
- Rotate the logo
- Stretch or distort the logo
- Change the logo colors
- Add effects not in the original
- Recreate from scratch
- Crop the logo
- Use low-resolution versions
- Place on busy backgrounds
- Add drop shadows
- Outline the logo

### Do
- Use official assets
- Maintain aspect ratio
- Use appropriate variant
- Keep minimum size
- Maintain safe area
- Test on target background

## Application Examples

### App Icon
```css
.app-icon {
  width: 1024px;
  height: 1024px;
  border-radius: 22%; /* iOS standard */
}
```

### Favicon
```css
.favicon {
  width: 32px;
  height: 32px;
  border-radius: 4px;
}
```

### Social Media Avatar
```css
.social-avatar {
  width: 400px;
  height: 400px;
  border-radius: 50%;
}
```

### Email Signature
```html
<table>
  <tr>
    <td>
      <img src="logo.png" width="120" alt="AetherOS" />
    </td>
  </tr>
</table>
```

## Color Combinations

### Approved Combinations
| Background | Logo Variant |
|------------|--------------|
| Dark (#060816) | Full Color |
| Black (#000000) | Full Color |
| White (#FFFFFF) | Black |
| Light Gray (#F5F5F5) | Black |
| Blue (#0066FF) | White |

### Unapproved Combinations
| Background | Logo Variant |
|------------|--------------|
| busy images | Any |
| gradients | Any |
| patterns | Any |

## Print Guidelines

### Minimum Size
- Business cards: 20mm width
- Letterhead: 30mm width
- Posters: 50mm width

### Color Mode
- Digital: RGB
- Print: CMYK

### Resolution
- Digital: 72 DPI
- Print: 300 DPI

## File Formats

| Format | Usage |
|--------|-------|
| SVG | Web, scalable |
| PNG | Web, fixed size |
| ICO | Favicon |
| ICNS | macOS |
| PDF | Print |

## Brand Voice

### Tone
- Professional
- Confident
- Innovative
- Approachable

### Language
- Clear and concise
- Active voice
- User-focused
- Jargon-free

## Marketing Materials

### Slide Deck
- Use brand colors
- Include logo on every slide
- Use approved templates
- Maintain consistent typography

### Website
- Use brand colors
- Include logo in header
- Use approved fonts
- Maintain consistent spacing

### Social Media
- Use brand colors
- Include logo in images
- Use approved templates
- Maintain consistent voice
