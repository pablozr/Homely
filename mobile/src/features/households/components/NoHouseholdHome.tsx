import { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { BrandMark } from '@/design/BrandMark';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import { useSignOut } from '@/features/auth/mutations';
import { useAcceptPendingInvite } from '@/features/households/mutations';
import { usePendingInviteStore } from '@/stores/pending-invite';
import { useSessionStore } from '@/stores/session';

import { CreateHouseholdForm } from './CreateHouseholdForm';
import { JoinByInviteForm } from './JoinByInviteForm';

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
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const user = useSessionStore((state) => state.user);
  const pendingToken = usePendingInviteStore((state) => state.token);
  const pendingStatus = usePendingInviteStore((state) => state.status);
  const signOut = useSignOut();
  const retryInvite = useAcceptPendingInvite();
  const [creating, setCreating] = useState(false);
  const [joining, setJoining] = useState(false);
  const fullname = user?.fullname ?? '';

  if (creating) {
    return <CreateHouseholdForm onCancel={() => setCreating(false)} />;
  }

  if (joining) {
    return <JoinByInviteForm onCancel={() => setJoining(false)} />;
  }

  return (
    <View style={styles.container}>
      <BrandMark size={40} />
      <View style={styles.avatar}>
        <Text style={styles.avatarLabel}>{initialsFromFullname(fullname)}</Text>
      </View>
      <Text style={styles.title}>{fullname}</Text>
      <Text style={styles.subtitle}>
        Voce ainda nao participa de uma casa. Crie uma casa ou entre por convite para continuar.
      </Text>

      <Pressable
        style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]}
        onPress={() => setCreating(true)}
        accessibilityRole="button"
        accessibilityLabel="Criar casa"
      >
        <Text style={styles.buttonLabel}>Criar casa</Text>
      </Pressable>

      <Pressable
        style={({ pressed }) => [styles.secondaryButton, pressed && styles.secondaryButtonPressed]}
        onPress={() => setJoining(true)}
        accessibilityRole="button"
        accessibilityLabel="Entrar por convite"
      >
        <Text style={styles.secondaryButtonLabel}>Entrar por convite</Text>
      </Pressable>

      {pendingStatus === 'terminal' ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Convite indisponivel ou ja utilizado.
        </Text>
      ) : null}

      {pendingToken && pendingStatus === 'retry' ? (
        <View style={styles.pending}>
          <Text style={styles.pendingLabel}>
            {retryInvite.data?.status === 'retry'
              ? 'Nao foi possivel confirmar o convite. Tente novamente.'
              : 'Voce tem um convite pendente.'}
          </Text>
          <Pressable
            style={({ pressed }) => [
              styles.secondaryButton,
              styles.pendingButton,
              pressed && styles.secondaryButtonPressed,
              retryInvite.isPending && styles.buttonDisabled,
            ]}
            onPress={() => retryInvite.mutate()}
            disabled={retryInvite.isPending}
            accessibilityRole="button"
            accessibilityLabel="Tentar aceitar o convite novamente"
            accessibilityState={{ disabled: retryInvite.isPending, busy: retryInvite.isPending }}
          >
            {retryInvite.isPending ? (
              <ActivityIndicator color={theme.colors.primary} />
            ) : (
              <Text style={styles.secondaryButtonLabel}>Tentar novamente</Text>
            )}
          </Pressable>
        </View>
      ) : null}

      <Pressable
        style={({ pressed }) => [
          styles.secondaryButton,
          pressed && styles.secondaryButtonPressed,
          signOut.isPending && styles.buttonDisabled,
        ]}
        onPress={() => signOut.mutate()}
        disabled={signOut.isPending}
        accessibilityRole="button"
        accessibilityState={{ disabled: signOut.isPending, busy: signOut.isPending }}
      >
        <Text style={styles.secondaryButtonLabel}>{signOut.isPending ? 'Saindo...' : 'Sair'}</Text>
      </Pressable>
    </View>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    container: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: theme.spacing.xl,
      backgroundColor: theme.colors.background,
    },

    avatar: {
      alignItems: 'center',
      justifyContent: 'center',
      width: 64,
      height: 64,
      marginTop: theme.spacing.lg,
      borderRadius: theme.radius.full,
      borderWidth: 1,
      borderColor: theme.colors.outlineStrong,
      backgroundColor: theme.colors.primarySubtle,
    },
    avatarLabel: { ...theme.typography.heading, color: theme.colors.primary },

    title: {
      ...theme.typography.title,
      marginTop: theme.spacing.md,
      color: theme.colors.textPrimary,
      textAlign: 'center',
    },
    subtitle: {
      ...theme.typography.body,
      marginTop: theme.spacing.xs,
      color: theme.colors.textSecondary,
      textAlign: 'center',
    },

    button: {
      alignSelf: 'stretch',
      marginTop: theme.spacing.lg,
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.lg,
      borderRadius: theme.radius.md,
      backgroundColor: theme.colors.primary,
    },
    buttonPressed: { backgroundColor: theme.colors.primaryPressed },
    buttonDisabled: { opacity: 0.5 },
    buttonLabel: { ...theme.typography.bodyStrong, color: theme.colors.textOnPrimary },

    pending: {
      alignSelf: 'stretch',
      marginTop: theme.spacing.lg,
      padding: theme.spacing.md,
      borderRadius: theme.radius.md,
      backgroundColor: theme.colors.surfaceSunken,
    },
    pendingLabel: { ...theme.typography.label, color: theme.colors.textSecondary },
    pendingButton: { marginTop: theme.spacing.sm },

    error: {
      ...theme.typography.label,
      alignSelf: 'stretch',
      marginTop: theme.spacing.sm,
      color: theme.colors.error,
    },

    secondaryButton: {
      alignSelf: 'stretch',
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
