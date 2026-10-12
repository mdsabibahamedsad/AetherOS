# AetherOS Accessibility Guidelines

## Overview

AetherOS is committed to making our products accessible to everyone. These guidelines ensure all interfaces meet WCAG 2.1 AA standards.

## Principles

1. **Perceivable** — Information must be presentable in ways users can perceive
2. **Operable** — UI components must be operable by all users
3. **Understandable** — Information and UI operation must be understandable
4. **Robust** — Content must be robust enough for assistive technologies

## Color Contrast

### Minimum Ratios
| Element | Normal Text | Large Text | UI Components |
|---------|-------------|------------|---------------|
| AA | 4.5:1 | 3:1 | 3:1 |
| AAA | 7:1 | 4.5:1 | 4.5:1 |

### AetherOS Colors
| Color Pair | Ratio | Status |
|------------|-------|--------|
| #E8ECF4 on #060816 | 14.2:1 | ✅ AAA |
| #8B95A8 on #060816 | 5.1:1 | ✅ AA |
| #00D4FF on #060816 | 9.4:1 | ✅ AAA |
| #0066FF on #FFFFFF | 4.6:1 | ✅ AA |

### Testing Tools
- WebAIM Contrast Checker
- Chrome DevTools Accessibility
- Colour Contrast Analyser

## Keyboard Navigation

### Focus Management
```css
/* Visible focus ring */
:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.5);
}

/* Skip link */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--brand-blue);
  color: white;
  padding: 8px;
  z-index: 100;
}

.skip-link:focus {
  top: 0;
}
```

### Tab Order
1. Logical reading order
2. No positive tabindex
3. Skip navigation links
4. Focus trap in modals

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| Tab | Move to next element |
| Shift+Tab | Move to previous element |
| Enter/Space | Activate button |
| Escape | Close modal/dropdown |
| Arrow keys | Navigate within component |

## Screen Readers

### ARIA Labels
```tsx
<!-- Interactive elements -->
<button aria-label="Close dialog">
  <IconX />
</button>

<!-- Form inputs -->
<input aria-label="Email address" type="email" />

<!-- Images -->
<img src="logo.png" alt="AetherOS Logo" />

<!-- Icons -->
<IconCheck aria-hidden="true" />
```

### ARIA Roles
```tsx
<!-- Navigation -->
<nav aria-label="Main navigation">
  <ul role="menubar">
    <li role="menuitem">
      <a href="/">Home</a>
    </li>
  </ul>
</nav>

<!-- Live regions -->
<div aria-live="polite">
  {message && <p>{message}</p>}
</div>

<!-- Modals -->
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Dialog Title</h2>
</div>
```

### Semantic HTML
```tsx
<!-- Use semantic elements -->
<header>Header</header>
<nav>Navigation</nav>
<main>Main content</main>
<aside>Sidebar</aside>
<footer>Footer</footer>

<!-- Use headings hierarchy -->
<h1>Page Title</h1>
<h2>Section Title</h2>
<h3>Subsection Title</h3>

<!-- Use lists -->
<ul>
  <li>Item 1</li>
  <li>Item 2</li>
</ul>
```

## Form Accessibility

### Labels
```tsx
<label htmlFor="email">Email Address</label>
<input id="email" type="email" aria-required="true" />
```

### Error Messages
```tsx
<label htmlFor="email">Email Address</label>
<input
  id="email"
  type="email"
  aria-invalid="true"
  aria-describedby="email-error"
/>
<span id="email-error" role="alert">
  Please enter a valid email address
</span>
```

### Required Fields
```tsx
<label htmlFor="email">
  Email Address <span aria-hidden="true">*</span>
</label>
<input id="email" type="email" aria-required="true" />
```

## Motion Accessibility

### Reduced Motion
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

### Pause Animation
```tsx
<button onClick={() => setPaused(!paused)}>
  {paused ? 'Play' : 'Pause'}
</button>
```

## Image Accessibility

### Alt Text
```tsx
<!-- Informative images -->
<img src="chart.png" alt="Sales increased 20% in Q4" />

<!-- Decorative images -->
<img src="decorative.png" alt="" aria-hidden="true" />

<!-- Complex images -->
<figure>
  <img src="chart.png" alt="Sales data for 2024" />
  <figcaption>Sales increased 20% in Q4 2024</figcaption>
</figure>
```

## Video Accessibility

### Captions
```html
<video>
  <source src="video.mp4" type="video/mp4" />
  <track kind="captions" src="captions.vtt" srclang="en" label="English" />
</video>
```

### Transcripts
```tsx
<details>
  <summary>View Transcript</summary>
  <div>{transcript}</div>
</details>
```

## Testing

### Automated Testing
```bash
# Install axe-core
npm install axe-core

# Run tests
npm run test:a11y
```

### Manual Testing
1. Keyboard navigation
2. Screen reader testing
3. Color contrast checking
4. Zoom testing (200%)
5. High contrast mode

### Testing Checklist
- [ ] All interactive elements focusable
- [ ] Focus visible on all elements
- [ ] Tab order logical
- [ ] Screen reader announces all content
- [ ] Color contrast meets AA
- [ ] Forms have labels
- [ ] Errors announced
- [ ] Reduced motion respected
- [ ] Images have alt text
- [ ] Videos have captions

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apd/)
- [WebAIM](https://webaim.org/)
- [A11y Project](https://www.a11yproject.com/)
