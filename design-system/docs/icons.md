# AetherOS Icon System

## Overview

The AetherOS icon system provides consistent, accessible, and scalable icons across all surfaces.

## Icon Library

### Primary: Tabler Icons
```bash
npm install @tabler/icons-react
```

### Usage
```tsx
import { IconCheck, IconX, IconSearch } from '@tabler/icons-react';

function App() {
  return (
    <div>
      <IconCheck size={24} />
      <IconX size={24} />
      <IconSearch size={24} />
    </div>
  );
}
```

## Icon Specifications

### Grid Size
```css
--icon-grid: 24px;
```

### Stroke Width
```css
--icon-stroke: 1.5px;
```

### Corner Radius
```css
--icon-radius: 2px;
```

### Padding
```css
--icon-padding: 2px;
```

## Icon Sizes

| Name | Size | Usage |
|------|------|-------|
| xs | 16px | Inline text, badges |
| sm | 20px | Compact UI, buttons |
| md | 24px | Default |
| lg | 32px | Large UI, navigation |
| xl | 48px | Hero sections, empty states |

### Size Classes
```css
.icon-xs { width: 16px; height: 16px; }
.icon-sm { width: 20px; height: 20px; }
.icon-md { width: 24px; height: 24px; }
.icon-lg { width: 32px; height: 32px; }
.icon-xl { width: 48px; height: 48px; }
```

## SVG Rules

### ViewBox
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
  <!-- Icon path -->
</svg>
```

### Stroke
- Always use `stroke="currentColor"`
- Always use `fill="none"`
- Consistent stroke width: 1.5px

### Path
- Use consistent corner radius
- Align to pixel grid
- Optimize for clarity

## Icon Categories

### Navigation
- Menu
- ChevronLeft
- ChevronRight
- ChevronUp
- ChevronDown
- ArrowLeft
- ArrowRight
- Home
- Settings
- Search

### Actions
- Plus
- Minus
- Edit
- Trash
- Copy
- Paste
- Save
- Download
- Upload
- Share

### Status
- Check
- X
- AlertTriangle
- AlertCircle
- InfoCircle
- Success
- Warning
- Error

### Media
- Play
- Pause
- Stop
- Volume
- VolumeOff
- Camera
- Image
- Video
- Music

### Communication
- Mail
- Message
- Phone
- Send
- Bell
- BellOff
- Chat
- Comment

### Development
- Code
- Terminal
- Database
- Server
- Cloud
- Git
- Branch
- Commit
- PullRequest

## Usage Guidelines

### Do
- Use consistent sizes
- Maintain proper alignment
- Use appropriate colors
- Provide aria-labels for interactive icons
- Use semantic icons

### Don't
- Stretch icons
- Change stroke width
- Add effects not in the original
- Use decorative icons without labels
- Mix icon styles

## Accessibility

### Interactive Icons
```tsx
<button aria-label="Close dialog">
  <IconX size={24} />
</button>
```

### Decorative Icons
```tsx
<IconCheck size={24} aria-hidden="true" />
```

### Icon with Text
```tsx
<button>
  <IconSearch size={24} />
  <span>Search</span>
</button>
```

## Color Usage

### Default
```css
.icon {
  color: var(--text-primary);
}
```

### Brand
```css
.icon-brand {
  color: var(--brand-cyan);
}
```

### Success
```css
.icon-success {
  color: var(--success-500);
}
```

### Warning
```css
.icon-warning {
  color: var(--warning-500);
}
```

### Danger
```css
.icon-danger {
  color: var(--danger-500);
}
```

### Disabled
```css
.icon-disabled {
  color: var(--text-disabled);
}
```

## Animation

### Spin
```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.icon-spin {
  animation: spin 1s linear infinite;
}
```

### Pulse
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.icon-pulse {
  animation: pulse 2s ease-in-out infinite;
}
```

## Export Sizes

### React Component
```tsx
import { IconCheck } from '@tabler/icons-react';

// Default (24px)
<IconCheck />

// Custom size
<IconCheck size={32} />

// With color
<IconCheck color="var(--success-500)" />
```

### SVG Export
```html
<!-- 16px -->
<svg width="16" height="16" viewBox="0 0 24 24">...</svg>

<!-- 24px -->
<svg width="24" height="24" viewBox="0 0 24 24">...</svg>

<!-- 32px -->
<svg width="32" height="32" viewBox="0 0 24 24">...</svg>
```

## Custom Icons

### Creating Custom Icons
1. Design on 24x24 grid
2. Use 1.5px stroke
3. Apply 2px corner radius
4. Align to pixel grid
5. Export as SVG

### Icon Template
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <!-- Your icon path here -->
</svg>
```

## Examples

### Button with Icon
```tsx
<button className="aetheros-button">
  <IconPlus size={20} />
  <span>Add Item</span>
</button>
```

### Icon Button
```tsx
<button className="aetheros-button-icon" aria-label="Delete">
  <IconTrash size={20} />
</button>
```

### Icon in Input
```tsx
<div className="aetheros-input-wrapper">
  <IconSearch size={20} className="aetheros-input-icon" />
  <input type="text" className="aetheros-input" />
</div>
```

### Icon in Navigation
```tsx
<nav>
  <a href="/" className="aetheros-nav-item">
    <IconHome size={24} />
    <span>Home</span>
  </a>
  <a href="/settings" className="aetheros-nav-item">
    <IconSettings size={24} />
    <span>Settings</span>
  </a>
</nav>
```
