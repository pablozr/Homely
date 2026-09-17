import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { useUpdateProfile } from '@/features/profile/mutations';
import { fullnameSchema } from '@/features/profile/schemas';
import { useSessionStore } from '@/stores/session';

export function ProfileSetup() {
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
      <Text style={styles.title}>Homely</Text>
      <Text style={styles.subtitle}>Como voce quer ser chamado?</Text>

      <TextInput
        style={styles.input}
        value={fullname}
        onChangeText={setFullname}
        placeholder="Seu nome"
        placeholderTextColor="#8A968E"
        autoCapitalize="words"
        autoCorrect={false}
        maxLength={255}
        editable={!updateProfile.isPending}
        onSubmitEditing={handleSubmit}
      />

      {validationError ? <Text style={styles.error}>{validationError}</Text> : null}
      {updateProfile.isError ? (
        <Text style={styles.error}>Nao foi possivel salvar o nome. Tente novamente.</Text>
      ) : null}

      <Pressable
        style={[styles.button, updateProfile.isPending && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={updateProfile.isPending}
        accessibilityRole="button"
      >
        {updateProfile.isPending ? (
          <ActivityIndicator color="#F7F6F2" />
        ) : (
          <Text style={styles.buttonLabel}>Continuar</Text>
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
