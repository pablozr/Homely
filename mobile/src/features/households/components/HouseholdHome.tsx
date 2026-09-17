import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useSignOut } from '@/features/auth/mutations';
import { useSelectHousehold } from '@/features/households/mutations';
import type { HouseholdSummary } from '@/features/households/types';

import { HouseholdSelector } from './HouseholdSelector';

type HouseholdHomeProps = {
  household: HouseholdSummary;
  households: HouseholdSummary[];
};

export function HouseholdHome({ household, households }: HouseholdHomeProps) {
  const signOut = useSignOut();
  const selectHousehold = useSelectHousehold();

  return (
    <View style={styles.container}>
      <Text style={styles.eyebrow}>Sua casa</Text>
      <Text style={styles.title}>{household.name}</Text>
      <Text style={styles.subtitle}>Fuso horário: {household.timezone}</Text>

      <HouseholdSelector
        households={households}
        activeHouseholdId={household.id}
        onSelect={(householdId) => selectHousehold.mutate(householdId)}
        disabled={selectHousehold.isPending}
        isError={selectHousehold.isError}
      />

      <Pressable
        style={[styles.secondaryButton, signOut.isPending && styles.buttonDisabled]}
        onPress={() => signOut.mutate()}
        disabled={signOut.isPending}
        accessibilityRole="button"
      >
        <Text style={styles.secondaryButtonLabel}>{signOut.isPending ? 'Saindo...' : 'Sair'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 32, backgroundColor: '#F7F6F2' },
  eyebrow: { fontSize: 14, fontWeight: '600', color: '#526258', textTransform: 'uppercase' },
  title: { marginTop: 8, fontSize: 32, fontWeight: '700', color: '#1C2B22' },
  subtitle: { marginTop: 8, fontSize: 16, color: '#526258' },

  secondaryButton: {
    marginTop: 32,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1C2B22',
  },
  buttonDisabled: { opacity: 0.6 },
  secondaryButtonLabel: { fontSize: 16, fontWeight: '600', color: '#1C2B22' },
});
