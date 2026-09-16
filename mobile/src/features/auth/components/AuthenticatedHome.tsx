import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useSignOut } from '@/features/auth/mutations';
import { useSessionStore } from '@/stores/session';

export function AuthenticatedHome() {
  const user = useSessionStore((state) => state.user);
  const signOut = useSignOut();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Homely</Text>
      <Text style={styles.subtitle}>Sessao ativa</Text>
      <Text style={styles.identity}>{user ? `${user.fullname} - ${user.email}` : 'Sessao restaurada'}</Text>

      <Pressable
        style={[styles.button, signOut.isPending && styles.buttonDisabled]}
        onPress={() => signOut.mutate()}
        disabled={signOut.isPending}
      >
        <Text style={styles.buttonLabel}>{signOut.isPending ? 'Saindo...' : 'Sair'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 32, backgroundColor: '#F7F6F2' },
  title: { fontSize: 42, fontWeight: '700', color: '#1C2B22' },
  subtitle: { marginTop: 8, fontSize: 18, color: '#526258' },
  identity: { marginTop: 24, fontSize: 16, color: '#1C2B22' },
  button: {
    marginTop: 32,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 52,
    borderRadius: 12,
    backgroundColor: '#1C2B22',
  },
  buttonDisabled: { opacity: 0.6 },
  buttonLabel: { fontSize: 16, fontWeight: '600', color: '#F7F6F2' },
});
