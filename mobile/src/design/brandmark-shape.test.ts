import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  BRANDMARK_ACCESSIBILITY_LABEL,
  BRANDMARK_CORE,
  BRANDMARK_SIZE,
  BRANDMARK_STROKES,
  BRANDMARK_STROKE_WIDTH,
  brandmarkSvgProps,
} from './brandmark-shape';

const PATH_NUMBER_PATTERN = /-?\d+(?:\.\d+)?/g;
const ALLOWED_PATH_PATTERN = /^[MmCcLlHhVvZz0-9.,\s-]+$/;

function coordinates(path: string): number[] {
  return (path.match(PATH_NUMBER_PATTERN) ?? []).map(Number);
}

function xCoordinates(path: string): number[] {
  return coordinates(path).filter((_, index) => index % 2 === 0);
}

function yCoordinates(path: string): number[] {
  return coordinates(path).filter((_, index) => index % 2 === 1);
}

test('brandmark: authoring canvas is square', () => {
  assert.equal(BRANDMARK_SIZE, 48);
});

test('brandmark: strokes only use ASCII path commands and numbers', () => {
  for (const path of Object.values(BRANDMARK_STROKES)) {
    assert.match(path, ALLOWED_PATH_PATTERN);
    assert.doesNotMatch(path, /[^\x20-\x7E]/, 'paths must not contain unicode or emoji glyphs');
  }
});

test('brandmark: left and right strokes mirror around the centre', () => {
  const leftX = xCoordinates(BRANDMARK_STROKES.left);
  const rightX = xCoordinates(BRANDMARK_STROKES.right);
  const half = BRANDMARK_SIZE / 2;

  assert.equal(leftX.length, rightX.length);
  assert.ok(leftX.length > 0);

  leftX.forEach((x, index) => {
    assert.equal(Number((BRANDMARK_SIZE - x).toFixed(1)), rightX[index]);
  });

  assert.deepEqual(yCoordinates(BRANDMARK_STROKES.left), yCoordinates(BRANDMARK_STROKES.right));
  assert.ok(leftX.every((x) => x < half));
  assert.ok(rightX.every((x) => x > half));
});

test('brandmark: core sits exactly on the centre', () => {
  assert.equal(BRANDMARK_CORE.cx, BRANDMARK_SIZE / 2);
  assert.equal(BRANDMARK_CORE.cy, BRANDMARK_SIZE / 2);
  assert.ok(BRANDMARK_CORE.r > 0);
  assert.ok(BRANDMARK_CORE.r * 2 < BRANDMARK_STROKE_WIDTH * 4);
});

test('brandmark: svg props are square and use the authoring viewBox', () => {
  const props = brandmarkSvgProps(64);

  assert.equal(props.width, 64);
  assert.equal(props.height, 64);
  assert.equal(props.viewBox, `0 0 ${BRANDMARK_SIZE} ${BRANDMARK_SIZE}`);
});

test('brandmark: svg props fall back to the authoring size for invalid input', () => {
  for (const invalid of [0, -10, Number.NaN, Number.POSITIVE_INFINITY]) {
    assert.equal(brandmarkSvgProps(invalid).width, BRANDMARK_SIZE);
  }
});

test('brandmark: exposes an accessible label without glyphs', () => {
  assert.equal(BRANDMARK_ACCESSIBILITY_LABEL, 'Homely');
  assert.doesNotMatch(BRANDMARK_ACCESSIBILITY_LABEL, /[^\x20-\x7E]/);
});
