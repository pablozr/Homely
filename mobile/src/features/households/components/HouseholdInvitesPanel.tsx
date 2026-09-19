import { useMemo, useRef } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { getErrorMessage } from '@/api/client';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import type { IdempotencyAttempt } from '@/features/households/idempotency';
import { resolveIdempotencyAttempt } from '@/features/households/idempotency';
import { useCreateInvite, useRevokeInvite } from '@/features/households/mutations';
import { useHouseholdInvites } from '@/features/households/queries';

type HouseholdInvitesPanelProps = {
  householdId: string;
};

export function HouseholdInvitesPanel({ householdId }: HouseholdInvitesPanelProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const invites = useHouseholdInvites(householdId);
  const createInvite = useCreateInvite();
  const revokeInvite = useRevokeInvite();
  const attemptRef = useRef<IdempotencyAttempt | null>(null);

  function handleCreate() {
    attemptRef.current = resolveIdempotencyAttempt(attemptRef.current, householdId);

    createInvite.mutate(
      { householdId, idempotencyKey: attemptRef.current.key },
      {
        onSuccess: () => {
          attemptRef.current = null;
        },
      },
    );
  }

  function handleRevoke(inviteId: string) {
    Alert.alert('Revogar convite', 'Quem ainda nao aceitou vai perder o acesso pelo link.', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Revogar',
        style: 'destructive',
        onPress: () => revokeInvite.mutate({ householdId, inviteId }),
      },
    ]);
  }

  const created = createInvite.data?.data;
  const outstanding = invites.data?.data.invites ?? [];
  const createError = getErrorMessage(
    createInvite.error,
    'Nao foi possivel criar o convite. Tente novamente.',
  );

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Convites</Text>

      <Pressable
        style={({ pressed }) => [
          styles.button,
          pressed && !createInvite.isPending && styles.buttonPressed,
          createInvite.isPending && styles.buttonDisabled,
        ]}
        onPress={handleCreate}
        disabled={createInvite.isPending}
        accessibilityRole="button"
        accessibilityLabel="Criar convite"
        accessibilityState={{ disabled: createInvite.isPending, busy: createInvite.isPending }}
      >
        {createInvite.isPending ? (
          <ActivityIndicator color={theme.colors.textOnPrimary} />
        ) : (
          <Text style={styles.buttonLabel}>Criar convite</Text>
        )}
      </Pressable>

      {createInvite.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {createError}
        </Text>
      ) : null}

      {created ? (
        <View style={styles.created}>
          <Text style={styles.createdLabel}>Link do convite</Text>
          <Text style={styles.createdUrl} selectable accessibilityLabel="Link do convite">
            {created.invite_url}
          </Text>
        </View>
      ) : null}

      {invites.isPending ? <ActivityIndicator color={theme.colors.primary} /> : null}

      {invites.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel carregar os convites.
        </Text>
      ) : null}

      {!invites.isPending && outstanding.length === 0 ? (
        <Text style={styles.empty}>Nenhum convite em aberto.</Text>
      ) : null}

      {outstanding.map((invite) => (
        <View key={invite.id} style={styles.invite}>
          <View style={styles.inviteInfo}>
            <Text style={styles.inviteId}>Convite {invite.id.slice(0, 8)}</Text>
            <Text style={styles.inviteExpiry}>
              Expira em {new Date(invite.expires_at).toLocaleDateString('pt-BR')}
            </Text>
          </View>
          <Pressable
            style={({ pressed }) => [
              styles.revokeButton,
              pressed && styles.revokeButtonPressed,
              revokeInvite.isPending && styles.buttonDisabled,
            ]}
            onPress={() => handleRevoke(invite.id)}
            disabled={revokeInvite.isPending}
            accessibilityRole="button"
            accessibilityLabel={`Revogar convite ${invite.id.slice(0, 8)}`}
          >
            <Text style={styles.revokeLabel}>Revogar</Text>
          </Pressable>
        </View>
      ))}

      {revokeInvite.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel revogar o convite. Tente novamente.
        </Text>
      ) : null}
    </View>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    container: { marginTop: theme.spacing.xl },
    heading: {
      ...theme.typography.label,
      color: theme.colors.textSecondary,
      textTransform: 'uppercase',
      letterSpacing: 0.6,
    },

    button: {
      marginTop: theme.spacing.sm,
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

    created: {
      marginTop: theme.spacing.sm,
      padding: theme.spacing.sm,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outline,
      backgroundColor: theme.colors.surfaceElevated,
    },
    createdLabel: { ...theme.typography.caption, color: theme.colors.textSecondary },
    createdUrl: {
      ...theme.typography.label,
      marginTop: theme.spacing.xxs,
      color: theme.colors.textPrimary,
    },

    empty: {
      ...theme.typography.label,
      marginTop: theme.spacing.sm,
      color: theme.colors.textMuted,
    },

    invite: {
      marginTop: theme.spacing.sm,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: theme.spacing.xs,
      paddingHorizontal: theme.spacing.sm,
      paddingVertical: theme.spacing.sm,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outline,
      backgroundColor: theme.colors.surface,
    },
    inviteInfo: { flexShrink: 1 },
    inviteId: { ...theme.typography.label, color: theme.colors.textPrimary },
    inviteExpiry: {
      ...theme.typography.caption,
      marginTop: theme.spacing.xxs,
      color: theme.colors.textMuted,
    },

    revokeButton: {
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.sm,
      borderRadius: theme.radius.sm,
    },
    revokeButtonPressed: { backgroundColor: theme.colors.errorSubtle },
    revokeLabel: { ...theme.typography.label, color: theme.colors.error },

    error: { ...theme.typography.label, marginTop: theme.spacing.sm, color: theme.colors.error },
  });
