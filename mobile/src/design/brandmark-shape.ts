/**
 * Abstract Homely brandmark geometry.
 *
 * Two mirrored strokes cradle an open central space — a home held in balance —
 * with a muted lilac core marking the shared centre. Deliberately not a literal
 * house or a caricatural pitched roof. Kept free of emoji / Unicode glyphs.
 *
 * This module is intentionally free of React and React Native imports so the
 * geometry can be unit-tested in the node:test environment.
 */

/** Square design canvas the paths are authored against. */
export const BRANDMARK_SIZE = 48;

/** Mirrored strokes: left and right halves guarding the centre. */
export const BRANDMARK_STROKES = {
  left: 'M20.5 9.5 C13.5 14.5 13.5 33.5 20.5 38.5',
  right: 'M27.5 9.5 C34.5 14.5 34.5 33.5 27.5 38.5',
} as const;

/** The open space at the centre of the mark. */
export const BRANDMARK_CORE = {
  cx: BRANDMARK_SIZE / 2,
  cy: BRANDMARK_SIZE / 2,
  r: 3.4,
} as const;

/** Stroke weight in viewBox units. */
export const BRANDMARK_STROKE_WIDTH = 3.4;

export type BrandmarkSvgProps = {
  width: number;
  height: number;
  viewBox: string;
};

/**
 * Resolve the SVG presentation props for a rendered brandmark of `size` dp.
 * The mark is square, so width and height always match.
 */
export function brandmarkSvgProps(size: number): BrandmarkSvgProps {
  const safeSize = Number.isFinite(size) && size > 0 ? size : BRANDMARK_SIZE;

  return {
    width: safeSize,
    height: safeSize,
    viewBox: `0 0 ${BRANDMARK_SIZE} ${BRANDMARK_SIZE}`,
  };
}

/** Accessible label announced for the decorative brandmark. */
export const BRANDMARK_ACCESSIBILITY_LABEL = 'Homely';
