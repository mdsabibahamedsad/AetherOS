# AetherOS Component Library

## Overview

The AetherOS component library provides reusable, accessible, and consistent UI components for all AetherOS surfaces.

## Component Standards

### Buttons

#### Variants
| Variant | Usage | Colors |
|---------|-------|--------|
| Primary | Main actions | Blue gradient |
| Secondary | Alternative actions | Glass border |
| Success | Positive actions | Green |
| Danger | Destructive actions | Red |
| Ghost | Minimal actions | Transparent |
| Glass | Premium actions | Glassmorphism |

#### Sizes
| Size | Height | Padding | Font Size |
|------|--------|---------|-----------|
| xs | 24px | 8px 12px | 12px |
| sm | 32px | 8px 16px | 13px |
| md | 40px | 10px 20px | 14px |
| lg | 48px | 12px 24px | 16px |
| xl | 56px | 16px 32px | 18px |

#### States
- Default
- Hover (scale 1.02, glow)
- Active (scale 0.98)
- Focus (ring)
- Disabled (opacity 0.5)

### Inputs

#### Variants
| Variant | Usage | Style |
|---------|-------|-------|
| Default | Standard forms | Border |
| Glass | Premium forms | Glassmorphism |
| Ghost | Minimal forms | No border |

#### Sizes
| Size | Height | Padding | Font Size |
|------|--------|---------|-----------|
| sm | 32px | 8px 12px | 13px |
| md | 40px | 10px 16px | 14px |
| lg | 48px | 12px 20px | 16px |

#### States
- Default
- Hover (border color change)
- Focus (cyan glow)
- Error (red border)
- Disabled (opacity 0.5)

### Checkboxes

#### States
- Unchecked
- Checked (gradient fill)
- Indeterminate
- Focus (cyan glow)
- Disabled

### Switches

#### States
- Off
- On (gradient track)
- Focus (cyan glow)
- Disabled

### Radio Buttons

#### States
- Unselected
- Selected (gradient fill)
- Focus (cyan glow)
- Disabled

### Dropdowns

#### Features
- Searchable
- Multi-select
- Grouped options
- Custom renderers

### Context Menus

#### Features
- Keyboard navigation
- Icons
- Dividers
- Submenus
- Shortcuts

### Dialogs/Modals

#### Sizes
| Size | Width | Max Height |
|------|-------|------------|
| sm | 400px | 85vh |
| md | 500px | 85vh |
| lg | 600px | 85vh |
| xl | 800px | 85vh |
| full | 100% | 100vh |

#### Features
- Glassmorphism overlay
- Smooth open/close animations
- Focus trap
- Escape to close
- Click outside to close

### Drawers/Sheets

#### Positions
- Left
- Right
- Top
- Bottom

#### Sizes
| Size | Width/Height |
|------|--------------|
| sm | 320px |
| md | 400px |
| lg | 500px |
| xl | 600px |
| full | 100% |

### Cards

#### Variants
| Variant | Usage | Style |
|---------|-------|-------|
| Default | Standard cards | Border |
| Glass | Premium cards | Glassmorphism |
| Elevated | Floating cards | Shadow |

#### Features
- Hover lift effect
- Consistent padding
- Border radius 16px

### Tabs

#### Variants
| Variant | Usage | Style |
|---------|-------|-------|
| Underline | Standard tabs | Bottom border |
| Pill | Compact tabs | Background |
| Enclosed | Boxed tabs | Border |

### Tables

#### Features
- Sortable columns
- Row hover
- Selection
- Sticky headers
- Virtual scrolling

### Breadcrumbs

#### Features
- Truncation
- Icons
- Dropdowns

### Pagination

#### Features
- Page numbers
- Previous/Next
- Items per page
- Jump to page

### Lists

#### Features
- Selection
- Reorder
- Virtual scrolling

### Trees

#### Features
- Expand/collapse
- Selection
- Drag and drop
- Virtual scrolling

### Navigation

#### Components
- Sidebar
- Navbar
- Tabs
- Breadcrumbs
- Dock
- Taskbar

### Search

#### Features
- Keyboard shortcut (Cmd+K)
- Recent searches
- Categorized results
- Keyboard navigation

### Terminal

#### Features
- Syntax highlighting
- Autocomplete
- Split panes
- Tabs

### Toast/Notifications

#### Positions
- Top-right
- Top-left
- Bottom-right
- Bottom-left

#### Types
- Info
- Success
- Warning
- Error

### Tooltip

#### Features
- Delay
- Positioning
- Arrow
- Rich content

### Popover

#### Features
- Anchor positioning
- Close on outside click
- Rich content

### Progress

#### Variants
| Variant | Usage | Style |
|---------|-------|-------|
| Bar | Standard progress | Horizontal bar |
| Circle | Compact progress | Circular |
| Spinner | Indeterminate | Spinning |

### Badge

#### Variants
| Variant | Usage | Style |
|---------|-------|-------|
| Default | Standard badge | Solid |
| Outline | Minimal badge | Border |
| Dot | Status indicator | Small dot |

### Avatar

#### Sizes
| Size | Dimensions |
|------|------------|
| xs | 24px |
| sm | 32px |
| md | 40px |
| lg | 48px |
| xl | 64px |

#### Features
- Image
- Initials
- Status indicator
- Group

### Agent Card

#### Features
- Avatar
- Name
- Status
- Description
- Actions

### Plugin Card

#### Features
- Icon
- Name
- Description
- Version
- Install/Uninstall

### Workspace Card

#### Features
- Preview
- Name
- Description
- Last modified
- Actions

## Accessibility

All components must:
- Be keyboard navigable
- Have proper ARIA labels
- Support screen readers
- Maintain focus visibility
- Meet WCAG AA contrast

## Implementation

### React Components
```tsx
import { Button, Input, Card } from '@aetheros/design-system';

function App() {
  return (
    <Card>
      <Input placeholder="Enter text..." />
      <Button variant="primary">Submit</Button>
    </Card>
  );
}
```

### CSS Classes
```css
.aetheros-button {
  /* Button styles */
}

.aetheros-input {
  /* Input styles */
}

.aetheros-card {
  /* Card styles */
}
```

## Testing

All components must pass:
- Unit tests
- Integration tests
- Accessibility tests
- Visual regression tests
- Performance tests
