import { useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { getErrorMessage } from '@/api/client';
import type { IdempotencyAttempt } from '@/features/households/idempotency';
import { resolveIdempotencyAttempt } from '@/features/households/idempotency';
import { useCreateHousehold } from '@/features/households/mutations';
import { householdFormSchema } from '@/features/households/schemas';
import {
  defaultTimezone,
  filterBrazilTimezones,
  timezoneLabel,
} from '@/features/households/timezones';

type CreateHouseholdFormProps = {
  onCancel: () => void;
};

export function CreateHouseholdForm({ onCancel }: CreateHouseholdFormProps) {
  const [name, setName] = useState('');
  const [timezone, setTimezone] = useState(() => defaultTimezone());
  const [isTimezonePickerOpen, setIsTimezonePickerOpen] = useState(false);
  const [timezoneQuery, setTimezoneQuery] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const attemptRef = useRef<IdempotencyAttempt | null>(null);
  const createHousehold = useCreateHousehold();
  const timezoneOptions = useMemo(() => filterBrazilTimezones(timezoneQuery), [timezoneQuery]);
  const createErrorMessage = getErrorMessage(
    createHousehold.error,
    'Nao foi possivel criar a casa. Tente novamente.',
  );

  function handleSelectTimezone(id: string) {
    setTimezone(id);
    setIsTimezonePickerOpen(false);
    setTimezoneQuery('');
    setValidationError(null);
  }

  function handleSubmit() {
    const parsed = householdFormSchema.safeParse({ name, timezone });

    if (!parsed.success) {
      setValidationError(parsed.error.issues[0]?.message ?? 'Revise os dados da casa.');
      return;
    }

    setValidationError(null);

    attemptRef.current = resolveIdempotencyAttempt(attemptRef.current, JSON.stringify(parsed.data));

    createHousehold.mutate(
      { ...parsed.data, idempotencyKey: attemptRef.current.key },
      {
        onSuccess: () => {
          attemptRef.current = null;
        },
      },
    );
  }

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={styles.title}>Criar casa</Text>
      <Text style={styles.subtitle}>Dê um nome para a casa e confirme o fuso horário.</Text>

      <Text style={styles.label}>Nome da casa</Text>
      <TextInput
        style={styles.input}
        value={name}
        onChangeText={setName}
        placeholder="Casa da Praia"
        placeholderTextColor="#8A968E"
        autoCapitalize="sentences"
        autoCorrect={false}
        maxLength={255}
        editable={!createHousehold.isPending}
        accessibilityLabel="Nome da casa"
      />

      <Text style={styles.label}>Fuso horário</Text>
      <Pressable
        style={[
          styles.input,
          styles.selectField,
          createHousehold.isPending && styles.inputDisabled,
        ]}
        onPress={() => setIsTimezonePickerOpen((open) => !open)}
        disabled={createHousehold.isPending}
        accessibilityRole="button"
        accessibilityLabel={`Fuso horário: ${timezoneLabel(timezone)}`}
        accessibilityHint="Abre a lista de fusos horários do Brasil"
        accessibilityState={{
          expanded: isTimezonePickerOpen,
          disabled: createHousehold.isPending,
        }}
      >
        <Text style={styles.selectValue}>{timezoneLabel(timezone)}</Text>
        <Text style={styles.selectChevron}>{isTimezonePickerOpen ? '▲' : '▼'}</Text>
      </Pressable>

      {isTimezonePickerOpen ? (
        <View style={styles.picker}>
          <TextInput
            style={styles.searchInput}
            value={timezoneQuery}
            onChangeText={setTimezoneQuery}
            placeholder="Buscar por cidade ou Brasil"
            placeholderTextColor="#8A968E"
            autoCapitalize="none"
            autoCorrect={false}
            accessibilityLabel="Buscar fuso horário"
          />

          <ScrollView
            style={styles.optionList}
            keyboardShouldPersistTaps="handled"
            nestedScrollEnabled
          >
            {timezoneOptions.length > 0 ? (
              timezoneOptions.map((option) => {
                const isSelected = option.id === timezone;

                return (
                  <Pressable
                    key={option.id}
                    style={[styles.option, isSelected && styles.optionSelected]}
                    onPress={() => handleSelectTimezone(option.id)}
                    accessibilityRole="button"
                    accessibilityState={{ selected: isSelected }}
                    accessibilityLabel={option.label}
                  >
                    <Text style={[styles.optionLabel, isSelected && styles.optionLabelSelected]}>
                      {option.label}
                    </Text>
                    {isSelected ? <Text style={styles.optionHint}>Selecionado</Text> : null}
                  </Pressable>
                );
              })
            ) : (
              <Text style={styles.empty}>Nenhum fuso encontrado.</Text>
            )}
          </ScrollView>
        </View>
      ) : null}

      {validationError ? <Text style={styles.error}>{validationError}</Text> : null}
      {createHousehold.isError ? <Text style={styles.error}>{createErrorMessage}</Text> : null}

      <Pressable
        style={[styles.button, createHousehold.isPending && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={createHousehold.isPending}
        accessibilityRole="button"
      >
        {createHousehold.isPending ? (
          <ActivityIndicator color="#F7F6F2" />
        ) : (
          <Text style={styles.buttonLabel}>Criar casa</Text>
        )}
      </Pressable>

      <Pressable
        style={styles.secondaryButton}
        onPress={onCancel}
        disabled={createHousehold.isPending}
        accessibilityRole="button"
      >
        <Text style={styles.secondaryButtonLabel}>Voltar</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#F7F6F2' },
  container: { flexGrow: 1, justifyContent: 'center', padding: 32, backgroundColor: '#F7F6F2' },
  title: { fontSize: 32, fontWeight: '700', color: '#1C2B22' },
  subtitle: { marginTop: 8, fontSize: 16, color: '#526258' },

  label: { marginTop: 24, fontSize: 14, fontWeight: '600', color: '#1C2B22' },
  input: {
    marginTop: 8,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    color: '#1C2B22',
    fontSize: 16,
  },
  inputDisabled: { opacity: 0.6 },

  selectField: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  selectValue: { flexShrink: 1, fontSize: 16, color: '#1C2B22' },
  selectChevron: { marginLeft: 12, fontSize: 12, color: '#526258' },

  picker: {
    marginTop: 8,
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  searchInput: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: '#F1F3EF',
    color: '#1C2B22',
    fontSize: 16,
  },
  optionList: { marginTop: 8, maxHeight: 220 },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderRadius: 8,
  },
  optionSelected: { backgroundColor: '#1C2B22' },
  optionLabel: { flexShrink: 1, fontSize: 16, color: '#1C2B22' },
  optionLabelSelected: { color: '#F7F6F2' },
  optionHint: { marginLeft: 8, fontSize: 12, color: '#D8E2DA' },
  empty: { paddingHorizontal: 12, paddingVertical: 12, fontSize: 14, color: '#526258' },

  error: { marginTop: 12, fontSize: 14, color: '#B3261E' },

  button: {
    marginTop: 24,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
    borderRadius: 12,
    backgroundColor: '#1C2B22',
  },
  buttonDisabled: { opacity: 0.6 },
  buttonLabel: { fontSize: 16, fontWeight: '600', color: '#F7F6F2' },

  secondaryButton: {
    marginTop: 16,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1C2B22',
  },
  secondaryButtonLabel: { fontSize: 16, fontWeight: '600', color: '#1C2B22' },
});
