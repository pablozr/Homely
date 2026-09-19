import { useMemo } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { BrandMark } from '@/design/BrandMark';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';

export function RestoringSession() {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);

  return (
    <View style={styles.container}>
      <BrandMark size={64} />
      <ActivityIndicator size="large" color={theme.colors.primary} />
      <Text style={styles.label}>Restaurando sessao...</Text>
    </View>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    container: {
      flex: 1,
      alignItems: 'center',
      justifyContent: 'center',
      gap: theme.spacing.md,
      padding: theme.spacing.xl,
      backgroundColor: theme.colors.background,
    },

    label: { ...theme.typography.body, color: theme.colors.textSecondary },
  });
