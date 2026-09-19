import { useMemo } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { BrandMark } from '@/design/BrandMark';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import { useSignOut } from '@/features/auth/mutations';
import { useLeaveHousehold, useSelectHousehold } from '@/features/households/mutations';
import type { HouseholdSummary } from '@/features/households/types';

import { HouseholdInvitesPanel } from './HouseholdInvitesPanel';
import { HouseholdMembersPanel } from './HouseholdMembersPanel';
import { HouseholdSelector } from './HouseholdSelector';

type HouseholdHomeProps = {
  household: HouseholdSummary;
  households: HouseholdSummary[];
};

export function HouseholdHome({ household, households }: HouseholdHomeProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const signOut = useSignOut();
  const selectHousehold = useSelectHousehold();
  const leaveHousehold = useLeaveHousehold();
  const isOwner = household.role === 'OWNER';

  function handleLeave() {
    Alert.alert(
      'Sair da casa',
      `Sair de ${household.name}? Voce pode voltar com um novo convite.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Sair',
          style: 'destructive',
          onPress: () => leaveHousehold.mutate(household.id),
        },
      ],
    );
  }

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.brandRow}>
        <BrandMark size={28} />
        <Text style={styles.eyebrow}>Sua casa</Text>
      </View>

      <Text style={styles.title}>{household.name}</Text>
      <Text style={styles.subtitle}>Fuso horário: {household.timezone}</Text>
      <Text style={styles.role}>Seu papel: {isOwner ? 'Owner' : 'Morador'}</Text>

      <HouseholdSelector
        households={households}
        activeHouseholdId={household.id}
        onSelect={(householdId) => selectHousehold.mutate(householdId)}
        disabled={selectHousehold.isPending}
        isError={selectHousehold.isError}
      />

      <HouseholdMembersPanel householdId={household.id} role={household.role} />

      {isOwner ? <HouseholdInvitesPanel householdId={household.id} /> : null}

      {!isOwner ? (
        <Pressable
          style={({ pressed }) => [
            styles.secondaryButton,
            pressed && !leaveHousehold.isPending && styles.secondaryButtonPressed,
            leaveHousehold.isPending && styles.buttonDisabled,
          ]}
          onPress={handleLeave}
          disabled={leaveHousehold.isPending}
          accessibilityRole="button"
          accessibilityLabel="Sair da casa"
          accessibilityState={{
            disabled: leaveHousehold.isPending,
            busy: leaveHousehold.isPending,
          }}
        >
          <Text style={styles.secondaryButtonLabel}>
            {leaveHousehold.isPending ? 'Saindo...' : 'Sair da casa'}
          </Text>
        </Pressable>
      ) : null}

      {leaveHousehold.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel sair da casa. Tente novamente.
        </Text>
      ) : null}

      <Pressable
        style={({ pressed }) => [
          styles.secondaryButton,
          pressed && !signOut.isPending && styles.secondaryButtonPressed,
          signOut.isPending && styles.buttonDisabled,
        ]}
        onPress={() => signOut.mutate()}
        disabled={signOut.isPending}
        accessibilityRole="button"
        accessibilityState={{ disabled: signOut.isPending, busy: signOut.isPending }}
      >
        <Text style={styles.secondaryButtonLabel}>{signOut.isPending ? 'Saindo...' : 'Sair'}</Text>
      </Pressable>
    </ScrollView>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    screen: { flex: 1, backgroundColor: theme.colors.background },
    container: {
      flexGrow: 1,
      padding: theme.spacing.xl,
      backgroundColor: theme.colors.background,
    },

    brandRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.xs },
    eyebrow: {
      ...theme.typography.label,
      color: theme.colors.textSecondary,
      textTransform: 'uppercase',
      letterSpacing: 0.6,
    },
    title: {
      ...theme.typography.title,
      marginTop: theme.spacing.xs,
      color: theme.colors.textPrimary,
    },
    subtitle: {
      ...theme.typography.body,
      marginTop: theme.spacing.xs,
      color: theme.colors.textSecondary,
    },
    role: {
      ...theme.typography.label,
      marginTop: theme.spacing.xxs,
      color: theme.colors.textMuted,
    },

    secondaryButton: {
      marginTop: theme.spacing.lg,
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
    buttonDisabled: { opacity: 0.6 },
    secondaryButtonLabel: { ...theme.typography.bodyStrong, color: theme.colors.primary },

    error: { ...theme.typography.label, marginTop: theme.spacing.sm, color: theme.colors.error },
  });
