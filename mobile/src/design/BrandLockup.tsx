import { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { BrandMark } from './BrandMark';
import type { Theme } from './tokens';
import { useTheme } from './useTheme';

type BrandLockupProps = {
  /** Brandmark size in dp. */
  markSize?: number;
  /** Wordmark size; defaults to the display type token. */
  variant?: 'display' | 'heading';
};

/**
 * Brandmark plus the Homely wordmark, used on auth and onboarding surfaces.
 * The wordmark carries the accessible name; the mark is decorative here.
 */
export function BrandLockup({ markSize = 56, variant = 'display' }: BrandLockupProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const type = theme.typography[variant];

  return (
    <View style={styles.container} accessible accessibilityLabel="Homely">
      <BrandMark size={markSize} accessible={false} />
      <Text style={[styles.wordmark, type, { color: theme.colors.textPrimary }]}>Homely</Text>
    </View>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    container: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm },
    wordmark: { letterSpacing: -0.5 },
  });
