import { useMemo } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import type { HouseholdSummary } from '@/features/households/types';

type HouseholdSelectorProps = {
  households: HouseholdSummary[];
  activeHouseholdId: string;
  onSelect: (householdId: string) => void;
  disabled: boolean;
  isError: boolean;
};

export function HouseholdSelector({
  households,
  activeHouseholdId,
  onSelect,
  disabled,
  isError,
}: HouseholdSelectorProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);

  if (households.length <= 1) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Trocar de casa</Text>
      {households.map((option) => {
        const isActive = option.id === activeHouseholdId;

        return (
          <Pressable
            key={option.id}
            style={({ pressed }) => [
              styles.option,
              isActive && styles.optionActive,
              pressed && !isActive && !disabled && styles.optionPressed,
            ]}
            onPress={() => {
              if (!isActive) {
                onSelect(option.id);
              }
            }}
            disabled={disabled || isActive}
            accessibilityRole="button"
            accessibilityState={{ selected: isActive, disabled: disabled || isActive }}
            accessibilityLabel={`Ativar casa ${option.name}`}
          >
            <Text style={[styles.optionLabel, isActive && styles.optionLabelActive]}>
              {option.name}
            </Text>
            {isActive ? <Text style={styles.optionHint}>Atual</Text> : null}
          </Pressable>
        );
      })}
      {isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel trocar de casa. Tente novamente.
        </Text>
      ) : null}
    </View>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    container: { marginTop: theme.spacing.xl },
    label: { ...theme.typography.label, color: theme.colors.textSecondary },

    option: {
      marginTop: theme.spacing.sm,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      minHeight: 48,
      paddingHorizontal: theme.spacing.md,
      paddingVertical: theme.spacing.sm,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outlineStrong,
      backgroundColor: theme.colors.surface,
    },
    optionPressed: { backgroundColor: theme.colors.surfaceAccent },
    optionActive: {
      backgroundColor: theme.colors.primarySubtle,
      borderColor: theme.colors.primary,
    },
    optionLabel: { ...theme.typography.bodyStrong, color: theme.colors.primary },
    optionLabelActive: { color: theme.colors.primary },
    optionHint: { ...theme.typography.caption, color: theme.colors.primary },

    error: { ...theme.typography.label, marginTop: theme.spacing.sm, color: theme.colors.error },
  });
