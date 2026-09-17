import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useSignOut } from '@/features/auth/mutations';
import { useSessionStore } from '@/stores/session';

import { CreateHouseholdForm } from './CreateHouseholdForm';

export function initialsFromFullname(fullname: string): string {
  const parts = fullname.trim().split(/\s+/).filter(Boolean);

  if (parts.length === 0) {
    return '?';
  }

  if (parts.length === 1) {
    return parts[0][0].toUpperCase();
  }

  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function NoHouseholdHome() {
  const user = useSessionStore((state) => state.user);
  const signOut = useSignOut();
  const [creating, setCreating] = useState(false);
  const fullname = user?.fullname ?? '';

  if (creating) {
    return <CreateHouseholdForm onCancel={() => setCreating(false)} />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.avatar}>
        <Text style={styles.avatarLabel}>{initialsFromFullname(fullname)}</Text>
      </View>
      <Text style={styles.title}>{fullname}</Text>
      <Text style={styles.subtitle}>
        Voce ainda nao participa de uma casa. Crie uma casa ou entre por convite para continuar.
      </Text>

      <Pressable
        style={styles.button}
        onPress={() => setCreating(true)}
        accessibilityRole="button"
        accessibilityLabel="Criar casa"
      >
        <Text style={styles.buttonLabel}>Criar casa</Text>
      </Pressable>

      <Pressable
        style={[styles.button, styles.buttonDisabled]}
        disabled
        accessibilityRole="button"
        accessibilityState={{ disabled: true }}
        accessibilityLabel="Entrar por convite. Disponivel em breve."
      >
        <Text style={styles.buttonLabel}>Entrar por convite</Text>
        <Text style={styles.buttonHint}>Em breve</Text>
      </Pressable>

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

  avatar: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#1C2B22',
  },
  avatarLabel: { fontSize: 24, fontWeight: '700', color: '#F7F6F2' },

  title: { marginTop: 16, fontSize: 32, fontWeight: '700', color: '#1C2B22' },
  subtitle: { marginTop: 8, fontSize: 16, color: '#526258' },

  button: {
    marginTop: 16,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
    borderRadius: 12,
    backgroundColor: '#1C2B22',
  },
  buttonDisabled: { opacity: 0.5 },
  buttonLabel: { fontSize: 16, fontWeight: '600', color: '#F7F6F2' },
  buttonHint: { marginTop: 2, fontSize: 12, color: '#D8E2DA' },

  secondaryButton: {
    marginTop: 24,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1C2B22',
  },
  secondaryButtonLabel: { fontSize: 16, fontWeight: '600', color: '#1C2B22' },
});
