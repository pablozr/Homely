import { useMemo } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import { useRemoveMember, useTransferOwnership } from '@/features/households/mutations';
import { useHouseholdMembers } from '@/features/households/queries';
import { useSessionStore } from '@/stores/session';

type HouseholdMembersPanelProps = {
  householdId: string;
  role: string;
};

export function roleLabel(role: string): string {
  return role === 'OWNER' ? 'Owner' : 'Morador';
}

export function HouseholdMembersPanel({ householdId, role }: HouseholdMembersPanelProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const currentUserId = useSessionStore((state) => state.user?.id ?? null);
  const membersQuery = useHouseholdMembers(householdId);
  const removeMember = useRemoveMember();
  const transferOwnership = useTransferOwnership();
  const isOwner = role === 'OWNER';

  function handleRemove(membershipId: string, fullname: string) {
    Alert.alert('Remover morador', `Remover ${fullname} da casa?`, [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Remover',
        style: 'destructive',
        onPress: () => removeMember.mutate({ householdId, membershipId }),
      },
    ]);
  }

  function handleTransfer(membershipId: string, fullname: string) {
    Alert.alert(
      'Transferir ownership',
      `Transferir a posse da casa para ${fullname}? Voce passa a ser morador.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Transferir',
          onPress: () =>
            transferOwnership.mutate({ householdId, targetMembershipId: membershipId }),
        },
      ],
    );
  }

  const members = (membersQuery.data?.data.memberships ?? []).filter(
    (member) => member.status === 'ACTIVE',
  );

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Moradores</Text>

      {membersQuery.isPending ? <ActivityIndicator color={theme.colors.primary} /> : null}

      {membersQuery.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel carregar os moradores.
        </Text>
      ) : null}

      {members.map((member) => {
        const isSelf = member.user_id === currentUserId;
        const canRemove = isOwner && !isSelf && member.role === 'MEMBER';
        const canTransfer = isOwner && !isSelf && member.role === 'MEMBER';

        return (
          <View key={member.id} style={styles.member}>
            <View style={styles.memberInfo}>
              <Text style={styles.memberName}>
                {member.fullname}
                {isSelf ? ' (voce)' : ''}
              </Text>
              <Text style={styles.memberRole}>{roleLabel(member.role)}</Text>
            </View>

            {canTransfer ? (
              <Pressable
                style={({ pressed }) => [styles.action, pressed && styles.actionPressed]}
                onPress={() => handleTransfer(member.id, member.fullname)}
                disabled={transferOwnership.isPending}
                accessibilityRole="button"
                accessibilityLabel={`Transferir ownership para ${member.fullname}`}
              >
                <Text style={styles.actionLabel}>Tornar owner</Text>
              </Pressable>
            ) : null}

            {canRemove ? (
              <Pressable
                style={({ pressed }) => [styles.action, pressed && styles.actionPressed]}
                onPress={() => handleRemove(member.id, member.fullname)}
                disabled={removeMember.isPending}
                accessibilityRole="button"
                accessibilityLabel={`Remover ${member.fullname}`}
              >
                <Text style={styles.removeLabel}>Remover</Text>
              </Pressable>
            ) : null}
          </View>
        );
      })}

      {removeMember.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel remover o morador. Tente novamente.
        </Text>
      ) : null}
      {transferOwnership.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel transferir a posse. Tente novamente.
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

    member: {
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
    memberInfo: { flexShrink: 1 },
    memberName: { ...theme.typography.label, color: theme.colors.textPrimary },
    memberRole: {
      ...theme.typography.caption,
      marginTop: theme.spacing.xxs,
      color: theme.colors.textMuted,
    },

    action: {
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.sm,
      borderRadius: theme.radius.sm,
    },
    actionPressed: { backgroundColor: theme.colors.surfaceSunken },
    actionLabel: { ...theme.typography.label, color: theme.colors.primary },
    removeLabel: { ...theme.typography.label, color: theme.colors.error },

    error: { ...theme.typography.label, marginTop: theme.spacing.sm, color: theme.colors.error },
  });
