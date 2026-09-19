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
import { BrandMark } from '@/design/BrandMark';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
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
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
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
      <BrandMark size={36} />
      <Text style={styles.title}>Criar casa</Text>
      <Text style={styles.subtitle}>Dê um nome para a casa e confirme o fuso horário.</Text>

      <Text style={styles.label}>Nome da casa</Text>
      <TextInput
        style={styles.input}
        value={name}
        onChangeText={setName}
        placeholder="Casa da Praia"
        placeholderTextColor={theme.colors.placeholder}
        autoCapitalize="sentences"
        autoCorrect={false}
        maxLength={255}
        editable={!createHousehold.isPending}
        accessibilityLabel="Nome da casa"
      />

      <Text style={styles.label}>Fuso horário</Text>
      <Pressable
        style={({ pressed }) => [
          styles.input,
          styles.selectField,
          pressed && !createHousehold.isPending && styles.fieldPressed,
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
            placeholderTextColor={theme.colors.placeholder}
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

      {validationError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {validationError}
        </Text>
      ) : null}
      {createHousehold.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {createErrorMessage}
        </Text>
      ) : null}

      <Pressable
        style={({ pressed }) => [
          styles.button,
          pressed && !createHousehold.isPending && styles.buttonPressed,
          createHousehold.isPending && styles.buttonDisabled,
        ]}
        onPress={handleSubmit}
        disabled={createHousehold.isPending}
        accessibilityRole="button"
        accessibilityState={{
          disabled: createHousehold.isPending,
          busy: createHousehold.isPending,
        }}
      >
        {createHousehold.isPending ? (
          <ActivityIndicator color={theme.colors.textOnPrimary} />
        ) : (
          <Text style={styles.buttonLabel}>Criar casa</Text>
        )}
      </Pressable>

      <Pressable
        style={({ pressed }) => [styles.secondaryButton, pressed && styles.secondaryButtonPressed]}
        onPress={onCancel}
        disabled={createHousehold.isPending}
        accessibilityRole="button"
      >
        <Text style={styles.secondaryButtonLabel}>Voltar</Text>
      </Pressable>
    </ScrollView>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    screen: { flex: 1, backgroundColor: theme.colors.background },
    container: {
      flexGrow: 1,
      justifyContent: 'center',
      padding: theme.spacing.xl,
      backgroundColor: theme.colors.background,
    },
    title: {
      ...theme.typography.title,
      marginTop: theme.spacing.md,
      color: theme.colors.textPrimary,
    },
    subtitle: {
      ...theme.typography.body,
      marginTop: theme.spacing.xs,
      color: theme.colors.textSecondary,
    },

    label: {
      ...theme.typography.label,
      marginTop: theme.spacing.lg,
      color: theme.colors.textSecondary,
    },
    input: {
      ...theme.typography.body,
      marginTop: theme.spacing.xs,
      minHeight: 48,
      paddingHorizontal: theme.spacing.md,
      paddingVertical: theme.spacing.sm,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outline,
      backgroundColor: theme.colors.surfaceElevated,
      color: theme.colors.textPrimary,
    },
    inputDisabled: { opacity: 0.6 },
    fieldPressed: { borderColor: theme.colors.primary },

    selectField: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    selectValue: { ...theme.typography.body, flexShrink: 1, color: theme.colors.textPrimary },
    selectChevron: {
      ...theme.typography.caption,
      marginLeft: theme.spacing.sm,
      color: theme.colors.textSecondary,
    },

    picker: {
      marginTop: theme.spacing.xs,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outline,
      backgroundColor: theme.colors.surface,
      paddingHorizontal: theme.spacing.sm,
      paddingVertical: theme.spacing.sm,
    },
    searchInput: {
      ...theme.typography.body,
      minHeight: 48,
      paddingHorizontal: theme.spacing.sm,
      paddingVertical: theme.spacing.xs,
      borderRadius: theme.radius.sm,
      backgroundColor: theme.colors.surfaceSunken,
      color: theme.colors.textPrimary,
    },
    optionList: { marginTop: theme.spacing.xs, maxHeight: 220 },
    option: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      minHeight: 48,
      paddingHorizontal: theme.spacing.sm,
      paddingVertical: theme.spacing.sm,
      borderRadius: theme.radius.sm,
    },
    optionSelected: { backgroundColor: theme.colors.primarySubtle },
    optionLabel: { ...theme.typography.body, flexShrink: 1, color: theme.colors.textPrimary },
    optionLabelSelected: { color: theme.colors.primary, fontWeight: '600' },
    optionHint: {
      ...theme.typography.caption,
      marginLeft: theme.spacing.xs,
      color: theme.colors.textSecondary,
    },
    empty: {
      ...theme.typography.label,
      paddingHorizontal: theme.spacing.sm,
      paddingVertical: theme.spacing.sm,
      color: theme.colors.textSecondary,
    },

    error: { ...theme.typography.label, marginTop: theme.spacing.sm, color: theme.colors.error },

    button: {
      marginTop: theme.spacing.lg,
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.lg,
      borderRadius: theme.radius.md,
      backgroundColor: theme.colors.primary,
    },
    buttonPressed: { backgroundColor: theme.colors.primaryPressed },
    buttonDisabled: { opacity: 0.6 },
    buttonLabel: { ...theme.typography.bodyStrong, color: theme.colors.textOnPrimary },

    secondaryButton: {
      marginTop: theme.spacing.md,
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.lg,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outlineStrong,
      backgroundColor: theme.colors.surface,
    },
    secondaryButtonPressed: { backgroundColor: theme.colors.surfaceAccent },
    secondaryButtonLabel: { ...theme.typography.bodyStrong, color: theme.colors.primary },
  });
