import { useMemo } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import { formatDueAt } from '@/features/tasks/date-time';
import type { Task } from '@/features/tasks/types';

export type TaskCardCompletionAction = {
  /** Visible label, e.g. `Desfazer` or `Corrigir conclusão`. */
  label: string;
  /** Full spoken label, e.g. `Desfazer conclusão da tarefa Lavar louca`. */
  accessibilityLabel: string;
  onPress: (task: Task) => void;
};

type TaskCardProps = {
  task: Task;
  timezone: string;
  isOwnTask: boolean;
  busy: boolean;
  onComplete?: (task: Task) => void;
  onEdit?: (task: Task) => void;
  onCancel?: (task: Task) => void;
  /** Required for a DONE task; ignored for pending work. */
  completionAction?: TaskCardCompletionAction;
};

export function TaskCard({
  task,
  timezone,
  isOwnTask,
  busy,
  onComplete,
  onEdit,
  onCancel,
  completionAction,
}: TaskCardProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const isDone = task.status === 'DONE';
  const dueLabel = task.due_at
    ? `Prazo: ${formatDueAt(task.due_at, task.due_timezone ?? timezone)}`
    : 'Sem prazo';
  const hasPendingActions = Boolean(onComplete ?? onEdit ?? onCancel);
  const hasActions = isDone ? Boolean(completionAction) : hasPendingActions;
  const statusSuffix = isDone ? ', concluída' : '';

  return (
    <View
      style={[styles.card, isOwnTask && styles.cardOwn, isDone && styles.cardDone]}
      accessibilityLabel={`Tarefa ${task.title}${isOwnTask ? ', sua tarefa' : ''}${statusSuffix}`}
    >
      <View style={styles.header}>
        <Text style={[styles.title, isDone && styles.titleDone]}>{task.title}</Text>
        {isOwnTask ? <Text style={styles.ownBadge}>Sua tarefa</Text> : null}
      </View>

      <Text style={styles.meta}>
        {task.assignee ? `Responsável: ${task.assignee.fullname}` : 'Sem responsável'}
      </Text>
      <Text style={styles.meta}>{dueLabel}</Text>

      {isDone ? (
        <View style={styles.doneBadge}>
          <Text style={styles.doneLabel}>Concluída</Text>
        </View>
      ) : task.is_overdue ? (
        <View style={styles.overdueBadge}>
          <Text style={styles.overdueLabel}>Atrasada</Text>
        </View>
      ) : null}

      {hasActions ? (
        <View style={styles.actions}>
          {isDone ? (
            completionAction ? (
              <Pressable
                style={({ pressed }) => [styles.action, pressed && !busy && styles.actionPressed]}
                onPress={() => completionAction.onPress(task)}
                disabled={busy}
                accessibilityRole="button"
                accessibilityLabel={completionAction.accessibilityLabel}
                accessibilityState={{ disabled: busy }}
              >
                <Text style={styles.completionActionLabel}>{completionAction.label}</Text>
              </Pressable>
            ) : null
          ) : (
            <>
              {onComplete ? (
                <Pressable
                  style={({ pressed }) => [
                    styles.action,
                    pressed && !busy && styles.completePressed,
                  ]}
                  onPress={() => onComplete(task)}
                  disabled={busy}
                  accessibilityRole="button"
                  accessibilityLabel={`Concluir tarefa ${task.title}`}
                  accessibilityState={{ disabled: busy }}
                >
                  <Text style={styles.completeLabel}>Concluir</Text>
                </Pressable>
              ) : null}

              {onEdit ? (
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
              ) : null}

              {onCancel ? (
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
              ) : null}
            </>
          )}
        </View>
      ) : null}
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
    cardDone: {
      backgroundColor: theme.colors.surface,
      borderColor: theme.colors.outline,
    },

    header: {
      flexDirection: 'row',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: theme.spacing.xs,
    },
    title: { ...theme.typography.bodyStrong, flexShrink: 1, color: theme.colors.textPrimary },
    titleDone: { color: theme.colors.textSecondary },
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

    doneBadge: {
      alignSelf: 'flex-start',
      marginTop: theme.spacing.xs,
      paddingHorizontal: theme.spacing.xs,
      paddingVertical: theme.spacing.xxs,
      borderRadius: theme.radius.sm,
      backgroundColor: theme.colors.successSubtle,
    },
    doneLabel: { ...theme.typography.caption, color: theme.colors.success },

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
    completePressed: { backgroundColor: theme.colors.successSubtle },
    cancelPressed: { backgroundColor: theme.colors.errorSubtle },
    actionLabel: { ...theme.typography.label, color: theme.colors.primary },
    completeLabel: { ...theme.typography.label, color: theme.colors.success },
    cancelLabel: { ...theme.typography.label, color: theme.colors.error },
    completionActionLabel: { ...theme.typography.label, color: theme.colors.primary },
  });
