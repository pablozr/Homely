import { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { BrandLockup } from '@/design/BrandLockup';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import { useUpdateProfile } from '@/features/profile/mutations';
import { fullnameSchema } from '@/features/profile/schemas';
import { useSessionStore } from '@/stores/session';

export function ProfileSetup() {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const suggestedName = useSessionStore((state) => state.user?.fullname ?? '');
  const [fullname, setFullname] = useState(suggestedName);
  const [validationError, setValidationError] = useState<string | null>(null);
  const updateProfile = useUpdateProfile();

  function handleSubmit() {
    const parsed = fullnameSchema.safeParse(fullname);

    if (!parsed.success) {
      setValidationError(parsed.error.issues[0]?.message ?? 'Informe um nome.');
      return;
    }

    setValidationError(null);
    updateProfile.mutate(parsed.data);
  }

  return (
    <View style={styles.container}>
      <BrandLockup />
      <Text style={styles.subtitle}>Como voce quer ser chamado?</Text>

      <TextInput
        style={styles.input}
        value={fullname}
        onChangeText={setFullname}
        placeholder="Seu nome"
        placeholderTextColor={theme.colors.placeholder}
        autoCapitalize="words"
        autoCorrect={false}
        maxLength={255}
        editable={!updateProfile.isPending}
        onSubmitEditing={handleSubmit}
        accessibilityLabel="Seu nome"
      />

      {validationError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {validationError}
        </Text>
      ) : null}
      {updateProfile.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel salvar o nome. Tente novamente.
        </Text>
      ) : null}

      <Pressable
        style={({ pressed }) => [
          styles.button,
          pressed && !updateProfile.isPending && styles.buttonPressed,
          updateProfile.isPending && styles.buttonDisabled,
        ]}
        onPress={handleSubmit}
        disabled={updateProfile.isPending}
        accessibilityRole="button"
        accessibilityState={{ disabled: updateProfile.isPending, busy: updateProfile.isPending }}
      >
        {updateProfile.isPending ? (
          <ActivityIndicator color={theme.colors.textOnPrimary} />
        ) : (
          <Text style={styles.buttonLabel}>Continuar</Text>
        )}
      </Pressable>
    </View>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    container: {
      flex: 1,
      justifyContent: 'center',
      padding: theme.spacing.xl,
      backgroundColor: theme.colors.background,
    },

    subtitle: {
      ...theme.typography.body,
      marginTop: theme.spacing.lg,
      color: theme.colors.textSecondary,
    },

    input: {
      ...theme.typography.body,
      marginTop: theme.spacing.xl,
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
  });
