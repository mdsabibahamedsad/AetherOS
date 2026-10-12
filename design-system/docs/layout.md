# AetherOS Layout System

## Overview

The AetherOS layout system provides flexible, responsive, and consistent layouts across all surfaces.

## Grid System

### Columns
```css
--grid-columns: 12;
```

### Gutter
```css
--grid-gutter: 24px; /* var(--space-6) */
```

### Margin
```css
--grid-margin: 24px; /* var(--space-6) */
```

## Breakpoints

| Name | Width | Usage |
|------|-------|-------|
| sm | 640px | Mobile landscape |
| md | 768px | Tablet portrait |
| lg | 1024px | Tablet landscape / Desktop |
| xl | 1280px | Desktop |
| 2xl | 1536px | Large desktop |

## Containers

### Default Container
```css
.container {
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}
```

### Narrow Container
```css
.container-narrow {
  width: 100%;
  max-width: 768px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}
```

### Wide Container
```css
.container-wide {
  width: 100%;
  max-width: 1536px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}
```

## Grid Classes

### 12-Column Grid
```css
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--grid-gutter);
}
```

### Column Spans
```css
.col-1 { grid-column: span 1; }
.col-2 { grid-column: span 2; }
.col-3 { grid-column: span 3; }
.col-4 { grid-column: span 4; }
.col-5 { grid-column: span 5; }
.col-6 { grid-column: span 6; }
.col-7 { grid-column: span 7; }
.col-8 { grid-column: span 8; }
.col-9 { grid-column: span 9; }
.col-10 { grid-column: span 10; }
.col-11 { grid-column: span 11; }
.col-12 { grid-column: span 12; }
```

### Responsive Columns
```css
@media (min-width: 640px) {
  .sm\:col-6 { grid-column: span 6; }
}

@media (min-width: 768px) {
  .md\:col-4 { grid-column: span 4; }
}

@media (min-width: 1024px) {
  .lg\:col-3 { grid-column: span 3; }
}
```

## Flexbox Utilities

### Display
```css
.flex { display: flex; }
.inline-flex { display: inline-flex; }
```

### Direction
```css
.flex-row { flex-direction: row; }
.flex-col { flex-direction: column; }
.flex-row-reverse { flex-direction: row-reverse; }
.flex-col-reverse { flex-direction: column-reverse; }
```

### Wrap
```css
.flex-wrap { flex-wrap: wrap; }
.flex-nowrap { flex-wrap: nowrap; }
```

### Justify
```css
.justify-start { justify-content: flex-start; }
.justify-end { justify-content: flex-end; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.justify-around { justify-content: space-around; }
.justify-evenly { justify-content: space-evenly; }
```

### Align
```css
.items-start { align-items: flex-start; }
.items-end { align-items: flex-end; }
.items-center { align-items: center; }
.items-baseline { align-items: baseline; }
.items-stretch { align-items: stretch; }
```

### Gap
```css
.gap-0 { gap: 0; }
.gap-1 { gap: var(--space-1); }
.gap-2 { gap: var(--space-2); }
.gap-3 { gap: var(--space-3); }
.gap-4 { gap: var(--space-4); }
.gap-5 { gap: var(--space-5); }
.gap-6 { gap: var(--space-6); }
.gap-8 { gap: var(--space-8); }
.gap-10 { gap: var(--space-10); }
.gap-12 { gap: var(--space-12); }
```

## Spacing Utilities

### Margin
```css
.m-0 { margin: 0; }
.m-1 { margin: var(--space-1); }
.m-2 { margin: var(--space-2); }
.m-3 { margin: var(--space-3); }
.m-4 { margin: var(--space-4); }
.m-auto { margin: auto; }

.mx-auto { margin-left: auto; margin-right: auto; }
.my-auto { margin-top: auto; margin-bottom: auto; }

.mt-0 { margin-top: 0; }
.mt-1 { margin-top: var(--space-1); }
.mt-2 { margin-top: var(--space-2); }
.mt-3 { margin-top: var(--space-3); }
.mt-4 { margin-top: var(--space-4); }

.mb-0 { margin-bottom: 0; }
.mb-1 { margin-bottom: var(--space-1); }
.mb-2 { margin-bottom: var(--space-2); }
.mb-3 { margin-bottom: var(--space-3); }
.mb-4 { margin-bottom: var(--space-4); }
```

### Padding
```css
.p-0 { padding: 0; }
.p-1 { padding: var(--space-1); }
.p-2 { padding: var(--space-2); }
.p-3 { padding: var(--space-3); }
.p-4 { padding: var(--space-4); }
.p-5 { padding: var(--space-5); }
.p-6 { padding: var(--space-6); }
.p-8 { padding: var(--space-8); }

.px-0 { padding-left: 0; padding-right: 0; }
.px-1 { padding-left: var(--space-1); padding-right: var(--space-1); }
.px-2 { padding-left: var(--space-2); padding-right: var(--space-2); }
.px-3 { padding-left: var(--space-3); padding-right: var(--space-3); }
.px-4 { padding-left: var(--space-4); padding-right: var(--space-4); }

.py-0 { padding-top: 0; padding-bottom: 0; }
.py-1 { padding-top: var(--space-1); padding-bottom: var(--space-1); }
.py-2 { padding-top: var(--space-2); padding-bottom: var(--space-2); }
.py-3 { padding-top: var(--space-3); padding-bottom: var(--space-3); }
.py-4 { padding-top: var(--space-4); padding-bottom: var(--space-4); }
```

## Width/Height Utilities

### Width
```css
.w-auto { width: auto; }
.w-full { width: 100%; }
.w-screen { width: 100vw; }
.w-min { width: min-content; }
.w-max { width: max-content; }
.w-fit { width: fit-content; }

.w-0 { width: 0; }
.w-1 { width: var(--space-1); }
.w-2 { width: var(--space-2); }
.w-3 { width: var(--space-3); }
.w-4 { width: var(--space-4); }
```

### Height
```css
.h-auto { height: auto; }
.h-full { height: 100%; }
.h-screen { height: 100vh; }
.h-min { height: min-content; }
.h-max { height: max-content; }
.h-fit { height: fit-content; }

.h-0 { height: 0; }
.h-1 { height: var(--space-1); }
.h-2 { height: var(--space-2); }
.h-3 { height: var(--space-3); }
.h-4 { height: var(--space-4); }
```

## Position Utilities

```css
.relative { position: relative; }
.absolute { position: absolute; }
.fixed { position: fixed; }
.sticky { position: sticky; }
.static { position: static; }

.inset-0 { top: 0; right: 0; bottom: 0; left: 0; }
.top-0 { top: 0; }
.right-0 { right: 0; }
.bottom-0 { bottom: 0; }
.left-0 { left: 0; }
```

## Overflow Utilities

```css
.overflow-auto { overflow: auto; }
.overflow-hidden { overflow: hidden; }
.overflow-visible { overflow: visible; }
.overflow-scroll { overflow: scroll; }
.overflow-x-auto { overflow-x: auto; }
.overflow-y-auto { overflow-y: auto; }
```

## Z-Index Utilities

```css
.z-below { z-index: -1; }
.z-base { z-index: 0; }
.z-above { z-index: 10; }
.z-dropdown { z-index: 100; }
.z-sticky { z-index: 200; }
.z-overlay { z-index: 300; }
.z-modal { z-index: 400; }
.z-popover { z-index: 500; }
.z-toast { z-index: 600; }
.z-tooltip { z-index: 700; }
.z-max { z-index: 9999; }
```

## Responsive Layout Examples

### Mobile First
```css
/* Mobile: 1 column */
.grid {
  grid-template-columns: 1fr;
}

/* Tablet: 2 columns */
@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Desktop: 3 columns */
@media (min-width: 1024px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

### Sidebar Layout
```css
.layout-sidebar {
  display: grid;
  grid-template-columns: 250px 1fr;
  height: 100vh;
}

@media (max-width: 768px) {
  .layout-sidebar {
    grid-template-columns: 1fr;
  }
}
```

### Dashboard Layout
```css
.layout-dashboard {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-template-rows: auto 1fr auto;
  gap: var(--space-6);
  height: 100vh;
}

.layout-dashboard-header {
  grid-column: 1 / -1;
}

.layout-dashboard-sidebar {
  grid-column: 1 / 4;
}

.layout-dashboard-main {
  grid-column: 4 / -1;
}

.layout-dashboard-footer {
  grid-column: 1 / -1;
}
```

## Accessibility

- Ensure proper heading hierarchy
- Use semantic HTML elements
- Maintain reading order
- Provide skip links
- Support keyboard navigation
