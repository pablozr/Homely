import assert from 'node:assert/strict';
import { test } from 'node:test';

import { darkTheme, lightTheme, radius, spacing, themes, typography, type Theme } from './tokens';

function relativeLuminance(hex: string): number {
  const value = hex.replace('#', '');
  const channels = [0, 2, 4].map((index) => {
    const channel = parseInt(value.slice(index, index + 2), 16) / 255;
    return channel <= 0.03928 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
  });

  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(a: string, b: string): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const lighter = Math.max(la, lb);
  const darker = Math.min(la, lb);

  return (lighter + 0.05) / (darker + 0.05);
}

const HEX_PATTERN = /^#[0-9A-F]{6}$/i;
const COLOR_PATTERN = /^(#[0-9A-F]{6}|rgba?\([\d\s.,]+\))$/i;

function assertAccessible(theme: Theme, foreground: string, background: string, minimum: number) {
  const ratio = contrastRatio(foreground, background);
  assert.ok(
    ratio >= minimum,
    `${theme.scheme}: expected contrast >= ${minimum}, got ${ratio.toFixed(2)}`,
  );
}

test('tokens: light and dark schemes are both defined with every colour role', () => {
  const lightRoles = Object.keys(lightTheme.colors).sort();
  const darkRoles = Object.keys(darkTheme.colors).sort();

  assert.deepEqual(lightRoles, darkRoles);
  assert.ok(lightRoles.length >= 20);
  assert.equal(lightTheme.scheme, 'light');
  assert.equal(darkTheme.scheme, 'dark');
  assert.equal(themes.light, lightTheme);
  assert.equal(themes.dark, darkTheme);
});

test('tokens: every colour role is a valid colour literal', () => {
  for (const theme of [lightTheme, darkTheme]) {
    for (const [role, value] of Object.entries(theme.colors)) {
      assert.match(value, COLOR_PATTERN, `${theme.scheme}.${role} must be a colour`);
    }
  }
});

test('tokens: no legacy palette hex survives in the token layer', () => {
  const legacy = ['#F7F6F2', '#1C2B22', '#526258', '#B3261E', '#8A968E', '#FFFFFF', '#F1F3EF'];

  for (const theme of [lightTheme, darkTheme]) {
    for (const [role, value] of Object.entries(theme.colors)) {
      assert.ok(
        !legacy.some((hex) => hex.toLowerCase() === value.toLowerCase()),
        `${theme.scheme}.${role} must not reuse the legacy palette (${value})`,
      );
    }
  }
});

test('tokens: body text keeps AA contrast on the base background in both schemes', () => {
  for (const theme of [lightTheme, darkTheme]) {
    assertAccessible(theme, theme.colors.textPrimary, theme.colors.background, 4.5);
    assertAccessible(theme, theme.colors.textSecondary, theme.colors.background, 4.5);
    assertAccessible(theme, theme.colors.textSecondary, theme.colors.surface, 4.5);
  }
});

test('tokens: primary actions keep AA contrast for their labels', () => {
  for (const theme of [lightTheme, darkTheme]) {
    assertAccessible(theme, theme.colors.textOnPrimary, theme.colors.primary, 4.5);
    assertAccessible(theme, theme.colors.textOnPrimary, theme.colors.primaryPressed, 4.5);
    assertAccessible(theme, theme.colors.error, theme.colors.background, 4.5);
    assertAccessible(theme, theme.colors.success, theme.colors.background, 4.5);
  }
});

test('tokens: spacing follows the 4/8/12/16/24/32 scale', () => {
  assert.deepEqual(spacing, { xxs: 4, xs: 8, sm: 12, md: 16, lg: 24, xl: 32 });
});

test('tokens: radii are moderate, with one reserved full round', () => {
  assert.equal(radius.full, 999);
  assert.ok(radius.sm < radius.md);
  assert.ok(radius.md < radius.lg);
  assert.ok(radius.lg <= 16);
});

test('tokens: type scale is descending and uses native weights', () => {
  const sizes = [
    typography.display.fontSize,
    typography.title.fontSize,
    typography.heading.fontSize,
    typography.body.fontSize,
    typography.label.fontSize,
    typography.caption.fontSize,
  ];

  for (let index = 1; index < sizes.length; index += 1) {
    assert.ok(sizes[index - 1] > sizes[index], 'type scale must strictly descend');
  }

  for (const token of Object.values(typography)) {
    assert.ok(token.lineHeight >= token.fontSize);
    assert.ok(['400', '500', '600', '700'].includes(token.fontWeight));
  }
});

test('tokens: share the same scales across schemes', () => {
  assert.equal(lightTheme.spacing, spacing);
  assert.equal(darkTheme.spacing, spacing);
  assert.equal(lightTheme.radius, radius);
  assert.equal(darkTheme.typography, typography);
  assert.match(lightTheme.colors.background, HEX_PATTERN);
});
