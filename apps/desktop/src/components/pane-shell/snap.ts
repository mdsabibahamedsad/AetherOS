/**
 * Snap-zone geometry (Master 23, Phase 4) — pure functions.
 *
 * Maps a pointer position within a container to a desktop-style snap zone
 * and the resulting pane rect. Additive: pane-shell can adopt this without
 * any change to existing resize/paint behavior.
 */

export type SnapZone =
  | 'left'
  | 'right'
  | 'top'
  | 'bottom'
  | 'top-left'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-right'
  | 'full';

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Bounds {
  width: number;
  height: number;
}

const EDGE = 0.12; // 12% border band triggers edge zones

export function detectSnapZone(
  px: number,
  py: number,
  bounds: Bounds,
): SnapZone {
  const { width, height } = bounds;
  const ex = width * EDGE;
  const ey = height * EDGE;
  const nearL = px <= ex;
  const nearR = px >= width - ex;
  const nearT = py <= ey;
  const nearB = py >= height - ey;

  if (nearL && nearT) {return 'top-left';}

  if (nearR && nearT) {return 'top-right';}

  if (nearL && nearB) {return 'bottom-left';}

  if (nearR && nearB) {return 'bottom-right';}

  if (nearL) {return 'left';}

  if (nearR) {return 'right';}

  if (nearT) {return 'top';}

  if (nearB) {return 'bottom';}

  return 'full';
}

export function snapRect(zone: SnapZone, bounds: Bounds): Rect {
  const { width: W, height: H } = bounds;

  switch (zone) {
    case 'left':
      return { x: 0, y: 0, w: W / 2, h: H };

    case 'right':
      return { x: W / 2, y: 0, w: W / 2, h: H };

    case 'top':
      return { x: 0, y: 0, w: W, h: H / 2 };

    case 'bottom':
      return { x: 0, y: H / 2, w: W, h: H / 2 };

    case 'top-left':
      return { x: 0, y: 0, w: W / 2, h: H / 2 };

    case 'top-right':
      return { x: W / 2, y: 0, w: W / 2, h: H / 2 };

    case 'bottom-left':
      return { x: 0, y: H / 2, w: W / 2, h: H / 2 };

    case 'bottom-right':
      return { x: W / 2, y: H / 2, w: W / 2, h: H / 2 };

    case 'full':
      return { x: 0, y: 0, w: W, h: H };
  }
}

export function resolveSnap(
  px: number,
  py: number,
  bounds: Bounds,
): { zone: SnapZone; rect: Rect } {
  const zone = detectSnapZone(px, py, bounds);

  return { zone, rect: snapRect(zone, bounds) };
}
