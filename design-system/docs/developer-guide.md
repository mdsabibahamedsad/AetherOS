# AetherOS Developer Guide

## Overview

This guide provides developers with everything needed to implement the AetherOS design system.

## Installation

### npm
```bash
npm install @aetheros/design-system
```

### yarn
```bash
yarn add @aetheros/design-system
```

### pnpm
```bash
pnpm add @aetheros/design-system
```

## Quick Start

### CSS Import
```css
@import '@aetheros/design-system/tokens';
@import '@aetheros/design-system/components';
```

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

## Design Tokens

### CSS Variables
```css
:root {
  /* Colors */
  --brand-blue: #0066FF;
  --brand-cyan: #00D4FF;
  --brand-purple: #9933FF;
  
  /* Typography */
  --font-sans: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  
  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  
  /* etc. */
}
```

### Tailwind CSS
```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        brand: {
          blue: '#0066FF',
          cyan: '#00D4FF',
          purple: '#9933FF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
};
```

### SCSS Variables
```scss
// _variables.scss
$brand-blue: #0066FF;
$brand-cyan: #00D4FF;
$brand-purple: #9933FF;

$font-sans: 'Inter', sans-serif;
$font-mono: 'JetBrains Mono', monospace;

$space-1: 4px;
$space-2: 8px;
$space-3: 12px;
$space-4: 16px;
```

## Naming Conventions

### CSS Classes
```css
/* Component */
.aetheros-button { }
.aetheros-input { }
.aetheros-card { }

/* Modifier */
.aetheros-button--primary { }
.aetheros-button--secondary { }
.aetheros-input--error { }

/* State */
.aetheros-button:hover { }
.aetheros-button:focus { }
.aetheros-button:disabled { }

/* Element */
.aetheros-button__icon { }
.aetheros-button__text { }
```

### CSS Variables
```css
/* Brand */
--brand-blue: #0066FF;
--brand-cyan: #00D4FF;

/* Semantic */
--text-primary: #E8ECF4;
--bg-base: #060816;

/* Component */
--button-bg: var(--brand-blue);
--input-border: var(--border-default);
```

### React Components
```tsx
// PascalCase for components
function Button() { }
function Input() { }
function Card() { }

// camelCase for props
interface ButtonProps {
  variant: 'primary' | 'secondary';
  size: 'sm' | 'md' | 'lg';
  onClick: () => void;
}
```

## Folder Structure

```
design-system/
├── tokens/
│   ├── index.css
│   ├── colors.css
│   ├── typography.css
│   ├── spacing.css
│   └── animations.css
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.css
│   │   └── Button.test.tsx
│   ├── Input/
│   │   ├── Input.tsx
│   │   ├── Input.css
│   │   └── Input.test.tsx
│   └── ...
├── docs/
│   ├── typography.md
│   ├── colors.md
│   ├── motion.md
│   └── ...
├── guidelines/
│   ├── branding.md
│   └── accessibility.md
└── README.md
```

## Component Implementation

### Button Example
```tsx
import { forwardRef } from 'react';
import { cn } from '@aetheros/design-system/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', className, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'aetheros-button',
          `aetheros-button--${variant}`,
          `aetheros-button--${size}`,
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);
```

### CSS Implementation
```css
/* Button.css */
.aetheros-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 8px;
  font-weight: 500;
  transition: all 200ms ease-out;
  cursor: pointer;
}

.aetheros-button--primary {
  background: var(--brand-blue);
  color: white;
}

.aetheros-button--primary:hover {
  background: var(--primary-400);
  transform: scale(1.02);
  box-shadow: var(--shadow-glow-blue);
}

.aetheros-button--sm {
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
}

.aetheros-button--md {
  height: 40px;
  padding: 0 16px;
  font-size: 14px;
}

.aetheros-button--lg {
  height: 48px;
  padding: 0 24px;
  font-size: 16px;
}
```

## Theming

### Dark Mode (Default)
```css
:root {
  color-scheme: dark;
  
  --bg-base: #060816;
  --text-primary: #E8ECF4;
}
```

### Light Mode
```css
[data-theme="light"] {
  color-scheme: light;
  
  --bg-base: #FFFFFF;
  --text-primary: #111827;
}
```

### Theme Switching
```tsx
function ThemeToggle() {
  const [theme, setTheme] = useState('dark');
  
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);
  
  return (
    <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
      Toggle Theme
    </button>
  );
}
```

## Accessibility

### Focus Management
```css
.aetheros-button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.5);
}
```

### ARIA Labels
```tsx
<button aria-label="Close dialog">
  <CloseIcon />
</button>
```

### Keyboard Navigation
```tsx
function Menu() {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      // Handle selection
    }
  };
  
  return (
    <div role="menu" onKeyDown={handleKeyDown}>
      {/* Menu items */}
    </div>
  );
}
```

## Performance

### CSS Optimization
```css
/* Use transform for animations */
.aetheros-button:hover {
  transform: scale(1.02); /* Good */
  /* width: 100%; */ /* Bad - triggers layout */
}

/* Use will-change for known animations */
.aetheros-modal {
  will-change: transform, opacity;
}
```

### Component Optimization
```tsx
// Memoize expensive components
const ExpensiveComponent = React.memo(({ data }) => {
  // Expensive computation
  return <div>{/* ... */}</div>;
});

// Use useCallback for event handlers
const handleClick = useCallback(() => {
  // Handle click
}, []);
```

## Testing

### Unit Tests
```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@aetheros/design-system';

describe('Button', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });
  
  it('handles click', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalled();
  });
});
```

### Accessibility Tests
```tsx
import { axe, toHaveNoViolations } from 'jest-axe';
import { render } from '@testing-library/react';
import { Button } from '@aetheros/design-system';

expect.extend(toHaveNoViolations);

describe('Button', () => {
  it('has no accessibility violations', async () => {
    const { container } = render(<Button>Click me</Button>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

## Migration Guide

### From Custom CSS
1. Replace custom variables with design tokens
2. Update class names to follow naming conventions
3. Test all components
4. Update documentation

### From Other Design Systems
1. Map existing components to AetherOS components
2. Replace custom tokens with AetherOS tokens
3. Update component implementations
4. Test thoroughly

## Support

- Documentation: https://aetheros.aetheros.com/design-system
- GitHub: https://github.com/aetheros/aetheros
- Discord: https://discord.gg/aetheros
