import { describe, expect, it } from 'vitest';

import { detectSnapZone, resolveSnap, snapRect } from './snap';

const B = { width: 1000, height: 800 };

describe('snap geometry (Master 23 P4)', () => {
  it('detects the nine standard zones', () => {
    expect(detectSnapZone(50, 50, B)).toBe('top-left');
    expect(detectSnapZone(950, 50, B)).toBe('top-right');
    expect(detectSnapZone(50, 750, B)).toBe('bottom-left');
    expect(detectSnapZone(950, 750, B)).toBe('bottom-right');
    expect(detectSnapZone(60, 400, B)).toBe('left');
    expect(detectSnapZone(940, 400, B)).toBe('right');
    expect(detectSnapZone(500, 40, B)).toBe('top');
    expect(detectSnapZone(500, 760, B)).toBe('bottom');
    expect(detectSnapZone(500, 400, B)).toBe('full');
  });

  it('half zones produce exact halves', () => {
    expect(snapRect('left', B)).toEqual({ x: 0, y: 0, w: 500, h: 800 });
    expect(snapRect('right', B)).toEqual({ x: 500, y: 0, w: 500, h: 800 });
    expect(snapRect('bottom', B)).toEqual({ x: 0, y: 400, w: 1000, h: 400 });
  });

  it('corner zones tile the plane without gaps or overlaps', () => {
    const tl = snapRect('top-left', B);
    const br = snapRect('bottom-right', B);
    expect(tl.w + br.x).toBe(B.width);
    expect(tl.h + br.y).toBe(B.height);
  });

  it('resolveSnap pairs zone and rect consistently', () => {
    const { zone, rect } = resolveSnap(30, 750, B);
    expect(zone).toBe('bottom-left');
    expect(rect).toEqual({ x: 0, y: 400, w: 500, h: 400 });
  });
});
