# AetherOS Typography System

## Overview

The AetherOS typography system provides a clear, scalable, and consistent type hierarchy across all surfaces. Built on Inter for UI and JetBrains Mono for code.

## Font Families

### Primary (UI)
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
```

### Monospace (Code)
```css
--font-mono: 'JetBrains Mono', 'SF Mono', 'Cascadia Code', ui-monospace, Menlo, Consolas, monospace;
```

### Display (Headings)
```css
--font-display: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
```

## Type Scale

| Name | Size | Weight | Line Height | Letter Spacing | Usage |
|------|------|--------|-------------|----------------|-------|
| Display Large | 48px (3rem) | 700 | 1.1 | -0.025em | Hero headlines |
| Display Medium | 36px (2.25rem) | 700 | 1.2 | -0.025em | Page titles |
| Display Small | 30px (1.875rem) | 600 | 1.25 | -0.02em | Section headers |
| H1 | 24px (1.5rem) | 700 | 1.3 | -0.02em | Page headings |
| H2 | 20px (1.25rem) | 600 | 1.35 | -0.015em | Section headings |
| H3 | 18px (1.125rem) | 600 | 1.4 | -0.01em | Subsection headings |
| H4 | 16px (1rem) | 600 | 1.4 | -0.01em | Card headings |
| H5 | 14px (0.875rem) | 600 | 1.45 | 0em | Small headings |
| H6 | 13px (0.8125rem) | 600 | 1.45 | 0em | Label headings |
| Body Large | 16px (1rem) | 400 | 1.6 | 0em | Large body text |
| Body | 14px (0.875rem) | 400 | 1.5 | 0em | Default body text |
| Body Small | 13px (0.8125rem) | 400 | 1.5 | 0em | Secondary text |
| Caption | 12px (0.75rem) | 400 | 1.5 | 0.01em | Captions, metadata |
| Label Large | 14px (0.875rem) | 500 | 1.4 | 0.01em | Button labels |
| Label | 13px (0.8125rem) | 500 | 1.4 | 0.01em | Input labels |
| Label Small | 12px (0.75rem) | 500 | 1.4 | 0.02em | Badges, tags |
| Code | 13px (0.8125rem) | 400 | 1.6 | 0em | Inline code |
| Code Block | 13px (0.8125rem) | 400 | 1.6 | 0em | Code blocks |

## Usage Guidelines

### Display Typography
Use for hero sections, landing pages, and major announcements.

```css
.display-large {
  font-size: var(--text-5xl);
  font-weight: var(--weight-bold);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tight);
}

.display-medium {
  font-size: var(--text-4xl);
  font-weight: var(--weight-bold);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tight);
}
```

### Heading Typography
Use for page and section structure.

```css
h1 {
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tight);
}

h2 {
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  line-height: var(--leading-snug);
  letter-spacing: var(--tracking-tight);
}
```

### Body Typography
Use for content and readable text.

```css
.body-large {
  font-size: var(--text-md);
  font-weight: var(--weight-regular);
  line-height: var(--leading-relaxed);
}

.body {
  font-size: var(--text-base);
  font-weight: var(--weight-regular);
  line-height: var(--leading-normal);
}

.body-small {
  font-size: var(--text-sm);
  font-weight: var(--weight-regular);
  line-height: var(--leading-normal);
}
```

### Label Typography
Use for UI controls and interactive elements.

```css
.label-large {
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-wide);
}

.label {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-wide);
}

.label-small {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-wider);
}
```

### Code Typography
Use for code blocks and technical content.

```css
.code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: var(--weight-regular);
  line-height: var(--leading-relaxed);
}
```

## Responsive Typography

Adjust font sizes for different screen sizes:

```css
/* Mobile */
@media (max-width: 640px) {
  .display-large { font-size: var(--text-3xl); }
  .display-medium { font-size: var(--text-2xl); }
}

/* Tablet */
@media (max-width: 768px) {
  .display-large { font-size: var(--text-3xl); }
}

/* Desktop */
@media (min-width: 1024px) {
  .display-large { font-size: var(--text-5xl); }
}
```

## Accessibility

- Minimum body text size: 14px
- Minimum line height: 1.5
- Maximum line length: 75 characters
- Sufficient contrast ratios (WCAG AA)

## Examples

### Hero Section
```html
<h1 class="display-large">AetherOS</h1>
<p class="body-large">AI Operating System</p>
```

### Card Header
```html
<h3 class="h3">Settings</h3>
<p class="body-small text-secondary">Configure your preferences</p>
```

### Form Label
```html
<label class="label">Email Address</label>
<input type="email" class="input" />
```

### Code Block
```html
<pre class="code">
const app = new AetherOS();
app.start();
</pre>
```
