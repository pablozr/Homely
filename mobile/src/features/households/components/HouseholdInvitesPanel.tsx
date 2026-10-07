import { useMemo, useRef, useState } from 'react';
import * as Clipboard from 'expo-clipboard';
import {
  AccessibilityInfo,
  ActivityIndicator,
  Linking,
  Pressable,
  Share,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { getErrorMessage } from '@/api/client';
import { ConfirmationSheet } from '@/design/ConfirmationSheet';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import type { IdempotencyAttempt } from '@/features/households/idempotency';
import { resolveIdempotencyAttempt } from '@/features/households/idempotency';
import { buildInviteMessage, buildWhatsAppShareUrl } from '@/features/households/invite-sharing';
import { useCreateInvite, useRevokeInvite } from '@/features/households/mutations';
import { useHouseholdInvites } from '@/features/households/queries';
import type { InviteSummary } from '@/features/households/types';
import { useSessionStore } from '@/stores/session';

type HouseholdInvitesPanelProps = {
  householdId: string;
  householdName: string;
};

type ShareFeedback = {
  tone: 'success' | 'error';
  message: string;
};

export function HouseholdInvitesPanel({ householdId, householdName }: HouseholdInvitesPanelProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const invites = useHouseholdInvites(householdId);
  const createInvite = useCreateInvite();
  const revokeInvite = useRevokeInvite();
  const fullname = useSessionStore((state) => state.user?.fullname ?? '');
  const attemptRef = useRef<IdempotencyAttempt | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<InviteSummary | null>(null);
  const [shareFeedback, setShareFeedback] = useState<ShareFeedback | null>(null);

  function announce(tone: ShareFeedback['tone'], message: string) {
    setShareFeedback({ tone, message });
    AccessibilityInfo.announceForAccessibility(message);
  }

  function handleCreate() {
    attemptRef.current = resolveIdempotencyAttempt(attemptRef.current, householdId);

    createInvite.mutate(
      { householdId, idempotencyKey: attemptRef.current.key },
      {
        onSuccess: () => {
          attemptRef.current = null;
          setShareFeedback(null);
        },
      },
    );
  }

  async function handleCopyLink(inviteUrl: string) {
    try {
      await Clipboard.setStringAsync(inviteUrl);
      announce('success', 'Link copiado.');
    } catch {
      announce('error', 'Nao foi possivel copiar o link. Tente novamente.');
    }
  }

  async function shareInviteMessage(inviteUrl: string) {
    const message = buildInviteMessage({ fullname, householdName, inviteUrl });

    try {
      const result = await Share.share({ message });

      if (result.action === Share.sharedAction) {
        announce('success', 'Convite compartilhado.');
      }
    } catch {
      announce('error', 'Nao foi possivel compartilhar o convite. Tente novamente.');
    }
  }

  async function handleWhatsApp(inviteUrl: string) {
    const message = buildInviteMessage({ fullname, householdName, inviteUrl });

    try {
      await Linking.openURL(buildWhatsAppShareUrl(message));
    } catch {
      // No WhatsApp handler: fall back to the native share sheet.
      await shareInviteMessage(inviteUrl);
    }
  }

  function handleOpenRevoke(invite: InviteSummary) {
    revokeInvite.reset();
    setShareFeedback(null);
    setRevokeTarget(invite);
  }

  function handleCancelRevoke() {
    if (revokeInvite.isPending) {
      return;
    }

    revokeInvite.reset();
    setRevokeTarget(null);
  }

  function handleConfirmRevoke() {
    if (!revokeTarget) {
      return;
    }

    revokeInvite.mutate(
      { householdId, inviteId: revokeTarget.id },
      { onSuccess: () => setRevokeTarget(null) },
    );
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

          <View style={styles.shareActions}>
            <Pressable
              style={({ pressed }) => [styles.shareButton, pressed && styles.shareButtonPressed]}
              onPress={() => handleCopyLink(created.invite_url)}
              accessibilityRole="button"
              accessibilityLabel="Copiar link do convite"
            >
              <Text style={styles.shareLabel}>Copiar link</Text>
            </Pressable>

            <Pressable
              style={({ pressed }) => [styles.shareButton, pressed && styles.shareButtonPressed]}
              onPress={() => handleWhatsApp(created.invite_url)}
              accessibilityRole="button"
              accessibilityLabel="Compartilhar convite pelo WhatsApp"
            >
              <Text style={styles.shareLabel}>WhatsApp</Text>
            </Pressable>

            <Pressable
              style={({ pressed }) => [styles.shareButton, pressed && styles.shareButtonPressed]}
              onPress={() => shareInviteMessage(created.invite_url)}
              accessibilityRole="button"
              accessibilityLabel="Compartilhar convite"
            >
              <Text style={styles.shareLabel}>Compartilhar</Text>
            </Pressable>
          </View>

          {shareFeedback ? (
            <Text
              style={shareFeedback.tone === 'error' ? styles.error : styles.feedback}
              accessibilityLiveRegion="polite"
            >
              {shareFeedback.message}
            </Text>
          ) : null}
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
            onPress={() => handleOpenRevoke(invite)}
            disabled={revokeInvite.isPending}
            accessibilityRole="button"
            accessibilityLabel={`Revogar convite ${invite.id.slice(0, 8)}`}
          >
            <Text style={styles.revokeLabel}>Revogar</Text>
          </Pressable>
        </View>
      ))}

      <ConfirmationSheet
        visible={revokeTarget !== null}
        title="Revogar convite"
        message={
          revokeTarget
            ? `Convite ${revokeTarget.id.slice(0, 8)} — quem ainda nao aceitou vai perder o acesso pelo link.`
            : ''
        }
        confirmLabel="Revogar convite"
        onConfirm={handleConfirmRevoke}
        onCancel={handleCancelRevoke}
        pending={revokeInvite.isPending}
        errorMessage={
          revokeInvite.isError ? 'Nao foi possivel revogar o convite. Tente novamente.' : null
        }
        destructive
      />
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

    shareActions: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      gap: theme.spacing.xs,
      marginTop: theme.spacing.sm,
    },
    shareButton: {
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.md,
      borderRadius: theme.radius.sm,
      borderWidth: 1,
      borderColor: theme.colors.outlineStrong,
      backgroundColor: theme.colors.surface,
    },
    shareButtonPressed: { backgroundColor: theme.colors.surfaceAccent },
    shareLabel: { ...theme.typography.label, color: theme.colors.primary },

    feedback: {
      ...theme.typography.label,
      marginTop: theme.spacing.sm,
      color: theme.colors.success,
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
