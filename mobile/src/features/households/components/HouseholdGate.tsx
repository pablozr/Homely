import { useEffect } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { resolveActiveHouseholdId, useHouseholds } from '@/features/households/queries';
import { useActiveHouseholdStore } from '@/stores/active-household';

import { HouseholdHome } from './HouseholdHome';
import { NoHouseholdHome } from './NoHouseholdHome';

export function HouseholdGate() {
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
        <ActivityIndicator color="#1C2B22" />
        <Text style={styles.subtitle}>Carregando suas casas...</Text>
      </View>
    );
  }

  if (isError || !data) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Nao foi possivel carregar suas casas</Text>
        <Pressable
          style={styles.button}
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
        <ActivityIndicator color="#1C2B22" />
      </View>
    );
  }

  return <HouseholdHome household={activeHousehold} households={data.data.households} />;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    backgroundColor: '#F7F6F2',
  },
  title: { fontSize: 22, fontWeight: '700', color: '#1C2B22', textAlign: 'center' },
  subtitle: { marginTop: 12, fontSize: 16, color: '#526258', textAlign: 'center' },

  button: {
    marginTop: 24,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
    paddingHorizontal: 24,
    borderRadius: 12,
    backgroundColor: '#1C2B22',
  },
  buttonLabel: { fontSize: 16, fontWeight: '600', color: '#F7F6F2' },
});
