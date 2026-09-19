import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
} from 'react-native';

import { BrandMark } from '@/design/BrandMark';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import { useSubmitInviteToken } from '@/features/households/mutations';
import { inviteTokenFromInput } from '@/lib/deep-link';

type JoinByInviteFormProps = {
  onCancel: () => void;
};

export function JoinByInviteForm({ onCancel }: JoinByInviteFormProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const [value, setValue] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const submitInvite = useSubmitInviteToken();

  function handleSubmit() {
    const token = inviteTokenFromInput(value);

    if (!token) {
      setValidationError('Cole um link ou token de convite valido.');
      return;
    }

    setValidationError(null);
    submitInvite.mutate(token, {
      onSuccess: () => setValue(''),
    });
  }

  const result = submitInvite.data;

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <BrandMark size={36} />
      <Text style={styles.title}>Entrar por convite</Text>
      <Text style={styles.subtitle}>Cole o link recebido ou o token do convite.</Text>

      <TextInput
        style={styles.input}
        value={value}
        onChangeText={setValue}
        placeholder="homely://invite?invite_token=..."
        placeholderTextColor={theme.colors.placeholder}
        autoCapitalize="none"
        autoCorrect={false}
        maxLength={512}
        editable={!submitInvite.isPending}
        accessibilityLabel="Link ou token do convite"
      />

      {validationError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {validationError}
        </Text>
      ) : null}

      {result?.status === 'terminal' ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Convite indisponivel ou ja utilizado.
        </Text>
      ) : null}
      {result?.status === 'retry' || submitInvite.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel confirmar o convite. Tente novamente.
        </Text>
      ) : null}
      {result?.status === 'accepted' ? (
        <Text style={styles.success} accessibilityLiveRegion="polite">
          Convite aceito. Abrindo a casa...
        </Text>
      ) : null}

      <Pressable
        style={({ pressed }) => [
          styles.button,
          pressed && !submitInvite.isPending && styles.buttonPressed,
          submitInvite.isPending && styles.buttonDisabled,
        ]}
        onPress={handleSubmit}
        disabled={submitInvite.isPending}
        accessibilityRole="button"
        accessibilityLabel="Entrar por convite"
        accessibilityState={{ disabled: submitInvite.isPending, busy: submitInvite.isPending }}
      >
        {submitInvite.isPending ? (
          <ActivityIndicator color={theme.colors.textOnPrimary} />
        ) : (
          <Text style={styles.buttonLabel}>Entrar</Text>
        )}
      </Pressable>

      <Pressable
        style={({ pressed }) => [styles.secondaryButton, pressed && styles.secondaryButtonPressed]}
        onPress={onCancel}
        disabled={submitInvite.isPending}
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

    input: {
      ...theme.typography.body,
      marginTop: theme.spacing.lg,
      minHeight: 48,
      paddingHorizontal: theme.spacing.md,
      paddingVertical: theme.spacing.sm,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outline,
      backgroundColor: theme.colors.surfaceElevated,
      color: theme.colors.textPrimary,
    },

    error: { ...theme.typography.label, marginTop: theme.spacing.sm, color: theme.colors.error },
    success: {
      ...theme.typography.label,
      marginTop: theme.spacing.sm,
      color: theme.colors.success,
    },

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
