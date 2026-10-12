# AetherOS Color System

## Overview

The AetherOS color system provides semantic, accessible, and consistent colors across all surfaces. Built on a foundation of brand colors with extensive palette variations.

## Brand Colors

### Primary Blue
The primary brand color for interactive elements and key actions.

| Token | Hex | Usage |
|-------|-----|-------|
| --brand-blue | #0066FF | Primary brand color |
| --primary-500 | #0066FF | Default primary |
| --primary-400 | #3385FF | Hover state |
| --primary-600 | #0052CC | Pressed state |

### Secondary Cyan
The secondary brand color for accents and highlights.

| Token | Hex | Usage |
|-------|-----|-------|
| --brand-cyan | #00D4FF | Secondary brand color |
| --secondary-500 | #00D4FF | Default secondary |
| --secondary-400 | #33E0FF | Hover state |
| --secondary-600 | #00AACC | Pressed state |

### Accent Purple
The accent brand color for special elements.

| Token | Hex | Usage |
|-------|-----|-------|
| --brand-purple | #9933FF | Accent brand color |
| --accent-500 | #9933FF | Default accent |
| --accent-400 | #A64DFF | Hover state |
| --accent-600 | #7A29CC | Pressed state |

## Semantic Colors

### Success
For positive feedback and successful states.

| Token | Hex | Usage |
|-------|-----|-------|
| --success-50 | #ECFDF5 | Background |
| --success-100 | #D1FAE5 | Light background |
| --success-500 | #10B981 | Default |
| --success-600 | #059669 | Hover |
| --success-700 | #047857 | Pressed |

### Warning
For caution and attention states.

| Token | Hex | Usage |
|-------|-----|-------|
| --warning-50 | #FFFBEB | Background |
| --warning-100 | #FEF3C7 | Light background |
| --warning-500 | #F59E0B | Default |
| --warning-600 | #D97706 | Hover |
| --warning-700 | #B45309 | Pressed |

### Danger
For errors and destructive actions.

| Token | Hex | Usage |
|-------|-----|-------|
| --danger-50 | #FFF1F2 | Background |
| --danger-100 | #FFE4E6 | Light background |
| --danger-500 | #FF4D6A | Default |
| --danger-600 | #E11D48 | Hover |
| --danger-700 | #BE123C | Pressed |

### Info
For informational states.

| Token | Hex | Usage |
|-------|-----|-------|
| --info-50 | #EFF6FF | Background |
| --info-100 | #DBEAFE | Light background |
| --info-500 | #3B82F6 | Default |
| --info-600 | #2563EB | Hover |
| --info-700 | #1D4ED8 | Pressed |

## Background Levels

| Token | Hex | Usage |
|-------|-----|-------|
| --bg-base | #060816 | App background |
| --bg-raised | #0B1020 | Card background |
| --bg-overlay | #121826 | Modal background |
| --bg-surface | #1A2233 | Elevated surface |
| --bg-elevated | #232D42 | Highest elevation |

## Surface Levels

| Token | Value | Usage |
|-------|-------|-------|
| --surface-0 | transparent | No surface |
| --surface-1 | rgba(255,255,255,0.02) | Minimal surface |
| --surface-2 | rgba(255,255,255,0.04) | Light surface |
| --surface-3 | rgba(255,255,255,0.06) | Medium surface |
| --surface-4 | rgba(255,255,255,0.08) | Strong surface |
| --surface-5 | rgba(255,255,255,0.10) | Maximum surface |

## Text Colors

| Token | Hex | Usage |
|-------|-----|-------|
| --text-primary | #E8ECF4 | Primary text |
| --text-secondary | #8B95A8 | Secondary text |
| --text-tertiary | #6B7280 | Tertiary text |
| --text-quaternary | #4B5563 | Quaternary text |
| --text-disabled | #374151 | Disabled text |
| --text-inverse | #060816 | Inverse text |
| --text-brand | #00D4FF | Brand text |
| --text-link | #00D4FF | Link text |
| --text-link-hover | #00E5FF | Link hover |

## Interactive States

| Token | Usage |
|-------|-------|
| --interactive-default | Default interactive state |
| --interactive-hover | Hover state |
| --interactive-pressed | Pressed state |
| --interactive-disabled | Disabled state |
| --interactive-focus | Focus state |

## Border Colors

| Token | Value | Usage |
|-------|-------|-------|
| --border-subtle | rgba(255,255,255,0.04) | Subtle borders |
| --border-default | rgba(255,255,255,0.08) | Default borders |
| --border-strong | rgba(255,255,255,0.12) | Strong borders |
| --border-emphasis | rgba(255,255,255,0.16) | Emphasis borders |
| --border-brand | rgba(0,212,255,0.3) | Brand borders |

## Color Usage Guidelines

### Do
- Use semantic colors for their intended purpose
- Maintain sufficient contrast ratios
- Use brand colors sparingly for emphasis
- Test colors in both light and dark modes

### Don't
- Use color as the only indicator
- Use brand colors for large backgrounds
- Mix semantic colors inappropriately
- Ignore accessibility requirements

## Accessibility

All colors in the AetherOS design system meet WCAG AA contrast requirements:

- Normal text: 4.5:1 minimum
- Large text: 3:1 minimum
- UI components: 3:1 minimum

## Examples

### Button with Semantic Colors
```css
.button-primary {
  background: var(--primary-500);
  color: white;
}

.button-primary:hover {
  background: var(--primary-400);
}

.button-danger {
  background: var(--danger-500);
  color: white;
}
```

### Card with Background Levels
```css
.card {
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
}
```

### Text Hierarchy
```css
.text-primary { color: var(--text-primary); }
.text-secondary { color: var(--text-secondary); }
.text-tertiary { color: var(--text-tertiary); }
```
