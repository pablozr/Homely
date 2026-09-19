import { useMemo } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import { formatDueAt } from '@/features/tasks/date-time';
import type { Task } from '@/features/tasks/types';

type TaskCardProps = {
  task: Task;
  timezone: string;
  isOwnTask: boolean;
  busy: boolean;
  onEdit: (task: Task) => void;
  onCancel: (task: Task) => void;
};

export function TaskCard({ task, timezone, isOwnTask, busy, onEdit, onCancel }: TaskCardProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const dueLabel = task.due_at
    ? `Prazo: ${formatDueAt(task.due_at, task.due_timezone ?? timezone)}`
    : 'Sem prazo';

  return (
    <View
      style={[styles.card, isOwnTask && styles.cardOwn]}
      accessibilityLabel={`Tarefa ${task.title}${isOwnTask ? ', sua tarefa' : ''}`}
    >
      <View style={styles.header}>
        <Text style={styles.title}>{task.title}</Text>
        {isOwnTask ? <Text style={styles.ownBadge}>Sua tarefa</Text> : null}
      </View>

      <Text style={styles.meta}>
        {task.assignee ? `Responsável: ${task.assignee.fullname}` : 'Sem responsável'}
      </Text>
      <Text style={styles.meta}>{dueLabel}</Text>

      {task.is_overdue ? (
        <View style={styles.overdueBadge}>
          <Text style={styles.overdueLabel}>Atrasada</Text>
        </View>
      ) : null}

      <View style={styles.actions}>
        <Pressable
          style={({ pressed }) => [styles.action, pressed && !busy && styles.actionPressed]}
          onPress={() => onEdit(task)}
          disabled={busy}
          accessibilityRole="button"
          accessibilityLabel={`Editar tarefa ${task.title}`}
          accessibilityState={{ disabled: busy }}
        >
          <Text style={styles.actionLabel}>Editar</Text>
        </Pressable>

        <Pressable
          style={({ pressed }) => [styles.action, pressed && !busy && styles.cancelPressed]}
          onPress={() => onCancel(task)}
          disabled={busy}
          accessibilityRole="button"
          accessibilityLabel={`Cancelar tarefa ${task.title}`}
          accessibilityState={{ disabled: busy }}
        >
          <Text style={styles.cancelLabel}>Cancelar</Text>
        </Pressable>
      </View>
    </View>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    card: {
      marginTop: theme.spacing.sm,
      padding: theme.spacing.md,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outline,
      backgroundColor: theme.colors.surface,
    },
    cardOwn: {
      backgroundColor: theme.colors.primarySubtle,
      borderColor: theme.colors.primary,
    },

    header: {
      flexDirection: 'row',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: theme.spacing.xs,
    },
    title: { ...theme.typography.bodyStrong, flexShrink: 1, color: theme.colors.textPrimary },
    ownBadge: { ...theme.typography.caption, color: theme.colors.primary },

    meta: {
      ...theme.typography.caption,
      marginTop: theme.spacing.xxs,
      color: theme.colors.textSecondary,
    },

    overdueBadge: {
      alignSelf: 'flex-start',
      marginTop: theme.spacing.xs,
      paddingHorizontal: theme.spacing.xs,
      paddingVertical: theme.spacing.xxs,
      borderRadius: theme.radius.sm,
      backgroundColor: theme.colors.errorSubtle,
    },
    overdueLabel: { ...theme.typography.caption, color: theme.colors.error },

    actions: {
      flexDirection: 'row',
      justifyContent: 'flex-end',
      gap: theme.spacing.xs,
      marginTop: theme.spacing.xs,
    },
    action: {
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.sm,
      borderRadius: theme.radius.sm,
    },
    actionPressed: { backgroundColor: theme.colors.surfaceSunken },
    cancelPressed: { backgroundColor: theme.colors.errorSubtle },
    actionLabel: { ...theme.typography.label, color: theme.colors.primary },
    cancelLabel: { ...theme.typography.label, color: theme.colors.error },
  });
