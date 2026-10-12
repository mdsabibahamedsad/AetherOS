import { describe, expect, it } from 'vitest';

import {
  boxShadow,
  breakpoints,
  duration,
  easing,
  fontSize,
  radius,
  spacing,
  zIndex,
} from './design-tokens';

describe('design tokens (Master 22 P5)', () => {
  it('exposes the desktop breakpoint ladder in ascending order', () => {
    const vals = Object.values(breakpoints).map((v) => parseInt(v, 10));
    const sorted = [...vals].sort((a, b) => a - b);
    expect(vals).toEqual(sorted);
    expect(vals[0]).toBeGreaterThanOrEqual(1024);
  });

  it('type ramp covers display→status hierarchy exactly once each', () => {
    // Master 36 (Flagship Redesign) adds label/button text styles for form
    // and button surfaces; the ramp stays an explicit, duplicate-free list.
    expect(Object.keys(fontSize)).toEqual([
      'display',
      'heading',
      'subheading',
      'body',
      'caption',
      'metadata',
      'code',
      'label',
      'button',
    ]);
  });

  it('z-index layers are strictly increasing — no ad-hoc stacking', () => {
    const vals = Object.values(zIndex);
    const sorted = [...vals].sort((a, b) => a - b);
    expect(vals).toEqual(sorted);
    expect(new Set(vals).size).toBe(vals.length);
  });

  it('motion durations stay subtle (≤260ms) per P37 anti-decorative rule', () => {
    // Micro-transitions stay subtle. The single named exception is the modal
    // enter transition (320ms), an intentional Master 36 addition for dialog
    // open/close; it must remain the only duration above the cap.
    const entries = Object.entries(duration);

    for (const [name, d] of entries) {
      if (name === 'modal') {
        expect(parseInt(d, 10)).toBe(320);

        continue;
      }

      expect(parseInt(d, 10)).toBeLessThanOrEqual(260);
    }
  });

  it('elevations stay neutral and calm (black-based rgb, no glow colors)', () => {
    for (const [name, shadow] of Object.entries(boxShadow)) {
      if (name === 'focus') {
        expect(shadow).toContain('--ring-color'); // ring token, not elevation

        continue;
      }

      expect(shadow).toContain('rgb(0 0 0 /'); // neutral black elevations
      expect(shadow).not.toMatch(/#[0-9a-fA-F]{3,8}\b/); // no tinted glow
    }
  });

  it('spacing scale covers the standard step ladder in rem units', () => {
    // note: JS orders integer-like keys before '0.5'; assert by value set.
    // Master 36 extends the ladder with 24/32 for large panel layouts.
    const steps = Object.keys(spacing)
      .filter((k) => k !== 'px')
      .map(Number)
      .sort((a, b) => a - b);

    expect(steps).toEqual([0.5, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32]);

    for (const [k, v] of Object.entries(spacing)) {
      if (k === 'px') {
        expect(v).toBe('1px');
      } else {
        expect(v.endsWith('rem')).toBe(true);
      }
    }
  });

  it('easing curves are defined cubic-beziers', () => {
    for (const curve of Object.values(easing)) {
      expect(curve).toMatch(/^cubic-bezier\(/);
    }
  });

  it('radius includes panel/dialog semantics for shell consistency', () => {
    expect(radius.panel).toBeDefined();
    expect(radius.dialog).toBeDefined();
  });
});
