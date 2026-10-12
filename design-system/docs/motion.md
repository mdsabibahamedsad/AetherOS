# AetherOS Motion System

## Overview

The AetherOS motion system provides smooth, purposeful, and consistent animations across all interfaces. Every animation serves a purpose and enhances the user experience.

## Principles

1. **Purposeful** — Every animation has a reason
2. **Smooth** — 60 FPS minimum, no jank
3. **Subtle** — Enhance, don't distract
4. **Consistent** — Same timing, same easing, everywhere
5. **Respectful** — Honor reduced motion preferences

## Duration Scale

| Token | Value | Usage |
|-------|-------|-------|
| --duration-instant | 0ms | Immediate feedback |
| --duration-fast | 100ms | Micro-interactions |
| --duration-normal | 200ms | Standard transitions |
| --duration-slow | 300ms | Complex transitions |
| --duration-slower | 400ms | Page transitions |
| --duration-slowest | 500ms | Dramatic effects |

## Easing Curves

| Token | Value | Usage |
|-------|-------|-------|
| --ease-linear | linear | Continuous motion |
| --ease-in | cubic-bezier(0.4, 0, 1, 1) | Exiting elements |
| --ease-out | cubic-bezier(0, 0, 0.2, 1) | Entering elements |
| --ease-in-out | cubic-bezier(0.4, 0, 0.2, 1) | Moving elements |
| --ease-spring | cubic-bezier(0.34, 1.56, 0.64, 1) | Playful bounce |
| --ease-bounce | cubic-bezier(0.68, -0.55, 0.265, 1.55) | Bouncy effects |

## Transition Presets

### Fast (100ms)
```css
transition-fast: all 100ms var(--ease-out);
```
Use for: Hover states, focus rings, subtle feedback

### Normal (200ms)
```css
transition-normal: all 200ms var(--ease-out);
```
Use for: Button states, input focus, standard transitions

### Slow (300ms)
```css
transition-slow: all 300ms var(--ease-out);
```
Use for: Modal openings, sidebar transitions, complex animations

### Color Transitions
```css
transition-colors: color 200ms var(--ease-out), 
                   background-color 200ms var(--ease-out), 
                   border-color 200ms var(--ease-out);
```

### Transform Transitions
```css
transition-transform: transform 200ms var(--ease-out);
```

### Opacity Transitions
```css
transition-opacity: opacity 200ms var(--ease-out);
```

### Shadow Transitions
```css
transition-shadow: box-shadow 200ms var(--ease-out);
```

## Animation Patterns

### Hover Effects

#### Scale Up
```css
@keyframes hover-scale-up {
  from { transform: scale(1); }
  to { transform: scale(1.02); }
}

.hover-lift {
  transition: transform 200ms var(--ease-out);
}

.hover-lift:hover {
  transform: scale(1.02);
}
```

#### Glow
```css
@keyframes hover-glow {
  from { box-shadow: 0 0 0 rgba(0, 212, 255, 0); }
  to { box-shadow: 0 0 20px rgba(0, 212, 255, 0.3); }
}

.hover-glow {
  transition: box-shadow 200ms var(--ease-out);
}

.hover-glow:hover {
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
}
```

### Focus Effects

#### Focus Ring
```css
@keyframes focus-ring {
  from { box-shadow: 0 0 0 0 rgba(0, 212, 255, 0.5); }
  to { box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.5); }
}

.focus-ring:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.5);
}
```

### Loading Animations

#### Spinner
```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spinner {
  animation: spin 1s linear infinite;
}
```

#### Pulse
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.pulse {
  animation: pulse 2s ease-in-out infinite;
}
```

#### Shimmer
```css
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.shimmer {
  background: linear-gradient(90deg, 
    var(--surface-2) 0%, 
    var(--surface-4) 50%, 
    var(--surface-2) 100%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
```

### Page Transitions

#### Fade In
```css
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-in {
  animation: fade-in 300ms var(--ease-out);
}
```

#### Slide Up
```css
@keyframes slide-up {
  from { 
    opacity: 0;
    transform: translateY(8px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

.slide-up {
  animation: slide-up 300ms var(--ease-out);
}
```

#### Slide Down
```css
@keyframes slide-down {
  from { 
    opacity: 0;
    transform: translateY(-8px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

.slide-down {
  animation: slide-down 300ms var(--ease-out);
}
```

### Modal Animations

#### Modal Open
```css
@keyframes modal-open {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-open {
  animation: modal-open 300ms var(--ease-spring);
}
```

#### Modal Close
```css
@keyframes modal-close {
  from {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
  to {
    opacity: 0;
    transform: scale(0.95) translateY(10px);
  }
}

.modal-close {
  animation: modal-close 200ms var(--ease-in);
}
```

### Sidebar Animations

#### Sidebar Open
```css
@keyframes sidebar-open {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(0);
  }
}

.sidebar-open {
  animation: sidebar-open 300ms var(--ease-out);
}
```

### Search Animations

#### Search Expand
```css
@keyframes search-expand {
  from {
    width: 0;
    opacity: 0;
  }
  to {
    width: 100%;
    opacity: 1;
  }
}

.search-expand {
  animation: search-expand 200ms var(--ease-out);
}
```

### Notification Animations

#### Toast Slide In
```css
@keyframes toast-slide-in {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.toast-slide-in {
  animation: toast-slide-in 300ms var(--ease-spring);
}
```

### Expansion Animations

#### Expand
```css
@keyframes expand {
  from {
    height: 0;
    opacity: 0;
  }
  to {
    height: auto;
    opacity: 1;
  }
}

.expand {
  animation: expand 300ms var(--ease-out);
  overflow: hidden;
}
```

#### Collapse
```css
@keyframes collapse {
  from {
    height: auto;
    opacity: 1;
  }
  to {
    height: 0;
    opacity: 0;
  }
}

.collapse {
  animation: collapse 200ms var(--ease-in);
  overflow: hidden;
}
```

### Drag and Drop

#### Drag
```css
@keyframes drag {
  from {
    transform: scale(1);
    box-shadow: 0 0 0 rgba(0, 0, 0, 0);
  }
  to {
    transform: scale(1.05);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  }
}

.dragging {
  animation: drag 200ms var(--ease-out);
}
```

#### Drop
```css
@keyframes drop {
  from {
    transform: scale(1.05);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  }
  to {
    transform: scale(1);
    box-shadow: 0 0 0 rgba(0, 0, 0, 0);
  }
}

.dropped {
  animation: drop 200ms var(--ease-out);
}
```

## Reduced Motion

Always respect user preferences for reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Performance Guidelines

### Do
- Use `transform` and `opacity` for animations
- Use `will-change` for known animations
- Keep animations under 500ms
- Test on low-end devices

### Don't
- Animate layout properties (width, height, margin, padding)
- Use `setTimeout` for animations
- Chain too many animations
- Animate more than 3 elements simultaneously

## Examples

### Button Hover
```tsx
<button className="transition-all duration-200 hover:scale-105 hover:shadow-lg">
  Click me
</button>
```

### Card Hover
```tsx
<div className="transition-all duration-200 hover:-translate-y-1 hover:shadow-xl">
  Card content
</div>
```

### Modal
```tsx
<div className="animate-in fade-in zoom-in-95 duration-300">
  Modal content
</div>
```

### Toast
```tsx
<div className="animate-in slide-in-from-right duration-300">
  Toast message
</div>
```
