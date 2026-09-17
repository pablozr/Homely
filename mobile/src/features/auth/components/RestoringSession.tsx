import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

export function RestoringSession() {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#1C2B22" />
      <Text style={styles.label}>Restaurando sessao...</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    padding: 32,
    backgroundColor: '#F7F6F2',
  },

  label: { fontSize: 16, color: '#526258' },
});
