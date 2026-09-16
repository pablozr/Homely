import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View } from 'react-native';

import { useApiHealth } from '@/features/system/queries';

export default function HomeScreen() {
  const health = useApiHealth();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Homely</Text>
      <Text style={styles.subtitle}>A casa, em ordem.</Text>
      <Text style={styles.status}>
        {health.isPending
          ? 'Conectando a API local...'
          : health.isSuccess
            ? 'API local conectada'
            : 'API local indisponivel'}
      </Text>
      <StatusBar style="dark" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 32, backgroundColor: '#F7F6F2' },
  title: { fontSize: 42, fontWeight: '700', color: '#1C2B22' },
  subtitle: { marginTop: 8, fontSize: 18, color: '#526258' },
  status: { marginTop: 48, fontSize: 16, color: '#526258' },
});
