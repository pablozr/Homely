import { useEffect, useMemo } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { BrandMark } from '@/design/BrandMark';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import { resolveActiveHouseholdId, useHouseholds } from '@/features/households/queries';
import { useActiveHouseholdStore } from '@/stores/active-household';

import { HouseholdHome } from './HouseholdHome';
import { NoHouseholdHome } from './NoHouseholdHome';

export function HouseholdGate() {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const { data, isPending, isError, refetch } = useHouseholds();
  const activeHouseholdId = useActiveHouseholdStore((state) => state.activeHouseholdId);
  const setActiveHouseholdId = useActiveHouseholdStore((state) => state.setActiveHouseholdId);
  const clearActiveHousehold = useActiveHouseholdStore((state) => state.clearActiveHousehold);

  const resolvedId = data ? resolveActiveHouseholdId(data.data) : null;

  useEffect(() => {
    if (!data) {
      return;
    }

    const activeIsValid =
      activeHouseholdId !== null &&
      data.data.households.some((household) => household.id === activeHouseholdId);

    if (activeIsValid) {
      return;
    }

    if (resolvedId === null) {
      if (activeHouseholdId !== null) {
        clearActiveHousehold();
      }
      return;
    }

    setActiveHouseholdId(resolvedId);
  }, [data, resolvedId, activeHouseholdId, setActiveHouseholdId, clearActiveHousehold]);

  if (isPending) {
    return (
      <View style={styles.container}>
        <BrandMark size={48} />
        <ActivityIndicator color={theme.colors.primary} />
        <Text style={styles.subtitle}>Carregando suas casas...</Text>
      </View>
    );
  }

  if (isError || !data) {
    return (
      <View style={styles.container}>
        <BrandMark size={48} />
        <Text style={styles.title}>Nao foi possivel carregar suas casas</Text>
        <Pressable
          style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]}
          onPress={() => refetch()}
          accessibilityRole="button"
          accessibilityLabel="Tentar novamente"
        >
          <Text style={styles.buttonLabel}>Tentar novamente</Text>
        </Pressable>
      </View>
    );
  }

  if (data.data.households.length === 0) {
    return <NoHouseholdHome />;
  }

  const activeHousehold = data.data.households.find(
    (household) => household.id === activeHouseholdId,
  );

  if (!activeHousehold) {
    return (
      <View style={styles.container}>
        <BrandMark size={48} />
        <ActivityIndicator color={theme.colors.primary} />
      </View>
    );
  }

  return <HouseholdHome household={activeHousehold} households={data.data.households} />;
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
    title: {
      ...theme.typography.heading,
      color: theme.colors.textPrimary,
      textAlign: 'center',
    },
    subtitle: { ...theme.typography.body, color: theme.colors.textSecondary, textAlign: 'center' },

    button: {
      marginTop: theme.spacing.sm,
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.lg,
      borderRadius: theme.radius.md,
      backgroundColor: theme.colors.primary,
    },
    buttonPressed: { backgroundColor: theme.colors.primaryPressed },
    buttonLabel: { ...theme.typography.bodyStrong, color: theme.colors.textOnPrimary },
  });
