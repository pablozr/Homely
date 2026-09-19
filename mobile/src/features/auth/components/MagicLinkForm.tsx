import { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { BrandLockup } from '@/design/BrandLockup';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import { useRequestMagicLink } from '@/features/auth/mutations';
import { emailSchema } from '@/features/auth/schemas';

export function MagicLinkForm() {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const [email, setEmail] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const requestMagicLink = useRequestMagicLink();

  function handleSubmit() {
    const parsed = emailSchema.safeParse(email);

    if (!parsed.success) {
      setValidationError('Informe um e-mail valido.');
      return;
    }

    setValidationError(null);
    requestMagicLink.mutate(parsed.data);
  }

  if (requestMagicLink.isSuccess) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Verifique seu e-mail</Text>
        <Text style={styles.subtitle}>
          Enviamos um link de acesso para {requestMagicLink.variables}. Abra o link para entrar.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <BrandLockup />
      <Text style={styles.lead}>Entre com seu e-mail, sem senha.</Text>

      <TextInput
        style={styles.input}
        value={email}
        onChangeText={setEmail}
        placeholder="voce@exemplo.com"
        placeholderTextColor={theme.colors.placeholder}
        keyboardType="email-address"
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="email"
        editable={!requestMagicLink.isPending}
        onSubmitEditing={handleSubmit}
        accessibilityLabel="E-mail"
      />

      {validationError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {validationError}
        </Text>
      ) : null}
      {requestMagicLink.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel enviar o link. Tente novamente.
        </Text>
      ) : null}

      <Pressable
        style={({ pressed }) => [
          styles.button,
          pressed && !requestMagicLink.isPending && styles.buttonPressed,
          requestMagicLink.isPending && styles.buttonDisabled,
        ]}
        onPress={handleSubmit}
        disabled={requestMagicLink.isPending}
        accessibilityRole="button"
        accessibilityState={{
          disabled: requestMagicLink.isPending,
          busy: requestMagicLink.isPending,
        }}
      >
        {requestMagicLink.isPending ? (
          <ActivityIndicator color={theme.colors.textOnPrimary} />
        ) : (
          <Text style={styles.buttonLabel}>Enviar link de acesso</Text>
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

    title: { ...theme.typography.title, color: theme.colors.textPrimary },
    subtitle: {
      ...theme.typography.body,
      marginTop: theme.spacing.xs,
      color: theme.colors.textSecondary,
    },
    lead: {
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

    error: {
      ...theme.typography.label,
      marginTop: theme.spacing.sm,
      color: theme.colors.error,
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
    buttonLabel: {
      ...theme.typography.bodyStrong,
      color: theme.colors.textOnPrimary,
    },
  });
