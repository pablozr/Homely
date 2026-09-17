import { Pressable, StyleSheet, Text, View } from 'react-native';

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
            style={[styles.option, isActive && styles.optionActive]}
            onPress={() => {
              if (!isActive) {
                onSelect(option.id);
              }
            }}
            disabled={disabled || isActive}
            accessibilityRole="button"
            accessibilityState={{ selected: isActive }}
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
        <Text style={styles.error}>Nao foi possivel trocar de casa. Tente novamente.</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 32 },
  label: { fontSize: 14, fontWeight: '600', color: '#1C2B22' },

  option: {
    marginTop: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1C2B22',
  },
  optionActive: { backgroundColor: '#1C2B22' },
  optionLabel: { fontSize: 16, fontWeight: '600', color: '#1C2B22' },
  optionLabelActive: { color: '#F7F6F2' },
  optionHint: { fontSize: 12, color: '#D8E2DA' },

  error: { marginTop: 12, fontSize: 14, color: '#B3261E' },
});
