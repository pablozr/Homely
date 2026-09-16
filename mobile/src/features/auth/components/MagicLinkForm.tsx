import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { useRequestMagicLink } from '@/features/auth/mutations';
import { emailSchema } from '@/features/auth/schemas';

export function MagicLinkForm() {
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
      <Text style={styles.title}>Homely</Text>
      <Text style={styles.subtitle}>Entre com seu e-mail, sem senha.</Text>

      <TextInput
        style={styles.input}
        value={email}
        onChangeText={setEmail}
        placeholder="voce@exemplo.com"
        placeholderTextColor="#8A968E"
        keyboardType="email-address"
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="email"
        editable={!requestMagicLink.isPending}
        onSubmitEditing={handleSubmit}
      />

      {validationError ? <Text style={styles.error}>{validationError}</Text> : null}
      {requestMagicLink.isError ? (
        <Text style={styles.error}>Nao foi possivel enviar o link. Tente novamente.</Text>
      ) : null}

      <Pressable
        style={[styles.button, requestMagicLink.isPending && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={requestMagicLink.isPending}
      >
        {requestMagicLink.isPending ? (
          <ActivityIndicator color="#F7F6F2" />
        ) : (
          <Text style={styles.buttonLabel}>Enviar link de acesso</Text>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 32, backgroundColor: '#F7F6F2' },
  title: { fontSize: 42, fontWeight: '700', color: '#1C2B22' },
  subtitle: { marginTop: 8, fontSize: 18, color: '#526258' },
  input: {
    marginTop: 32,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    color: '#1C2B22',
    fontSize: 16,
  },
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
});
