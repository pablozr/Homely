import { useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { getErrorMessage } from '@/api/client';
import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import type { IdempotencyAttempt } from '@/features/households/idempotency';
import { resolveIdempotencyAttempt } from '@/features/households/idempotency';
import { useHouseholdMembers } from '@/features/households/queries';
import type { HouseholdSummary } from '@/features/households/types';
import { useSessionStore } from '@/stores/session';

import { useCancelTask, useCreateTask, useUpdateTask } from '../mutations';
import { usePendingTasks } from '../queries';
import { toTaskRequestBody, toTaskUpdateRequest, type TaskFormValues } from '../schemas';
import type { Task } from '../types';
import { TaskCard } from './TaskCard';
import { TaskForm } from './TaskForm';

type TaskListPanelProps = {
  household: HouseholdSummary;
};

type TaskFormMode = { kind: 'closed' } | { kind: 'create' } | { kind: 'edit'; task: Task };

export function TaskListPanel({ household }: TaskListPanelProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const currentUserId = useSessionStore((state) => state.user?.id ?? null);
  const tasksQuery = usePendingTasks(household.id);
  const membersQuery = useHouseholdMembers(household.id);
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const cancelTask = useCancelTask();
  const attemptRef = useRef<IdempotencyAttempt | null>(null);
  const [mode, setMode] = useState<TaskFormMode>({ kind: 'closed' });

  const members = (membersQuery.data?.data.memberships ?? []).filter(
    (member) => member.status === 'ACTIVE',
  );
  const tasks = tasksQuery.data?.data.tasks ?? [];
  const isSubmitting = createTask.isPending || updateTask.isPending;
  const formError =
    mode.kind === 'edit'
      ? updateTask.isError
        ? getErrorMessage(updateTask.error, 'Nao foi possivel salvar a tarefa. Tente novamente.')
        : null
      : createTask.isError
        ? getErrorMessage(createTask.error, 'Nao foi possivel criar a tarefa. Tente novamente.')
        : null;

  function closeForm() {
    attemptRef.current = null;
    setMode({ kind: 'closed' });
  }

  function handleSubmit(values: TaskFormValues) {
    if (mode.kind === 'edit') {
      const body = toTaskUpdateRequest(values, mode.task);

      if (body === undefined) {
        closeForm();
        return;
      }

      updateTask.mutate(
        {
          householdId: household.id,
          occurrenceId: mode.task.occurrence_id,
          body,
        },
        { onSuccess: closeForm },
      );
      return;
    }

    const body = toTaskRequestBody(values);
    attemptRef.current = resolveIdempotencyAttempt(attemptRef.current, JSON.stringify(body));

    createTask.mutate(
      { householdId: household.id, body, idempotencyKey: attemptRef.current.key },
      { onSuccess: closeForm },
    );
  }

  function handleCancel(task: Task) {
    Alert.alert('Cancelar tarefa', `Cancelar "${task.title}"?`, [
      { text: 'Voltar', style: 'cancel' },
      {
        text: 'Cancelar tarefa',
        style: 'destructive',
        onPress: () =>
          cancelTask.mutate({ householdId: household.id, occurrenceId: task.occurrence_id }),
      },
    ]);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.heading}>Tarefas</Text>
        {mode.kind === 'closed' ? (
          <Pressable
            style={({ pressed }) => [styles.newButton, pressed && styles.newButtonPressed]}
            onPress={() => setMode({ kind: 'create' })}
            disabled={isSubmitting}
            accessibilityRole="button"
            accessibilityLabel="Nova tarefa"
            accessibilityState={{ disabled: isSubmitting }}
          >
            <Text style={styles.newLabel}>Nova tarefa</Text>
          </Pressable>
        ) : null}
      </View>

      {mode.kind !== 'closed' ? (
        <TaskForm
          key={mode.kind === 'edit' ? mode.task.id : 'new'}
          members={members}
          defaultDueTime={household.default_due_time}
          initialTask={mode.kind === 'edit' ? mode.task : null}
          isSubmitting={isSubmitting}
          errorMessage={formError}
          onSubmit={handleSubmit}
          onCancel={closeForm}
        />
      ) : null}

      {tasksQuery.isPending ? (
        <ActivityIndicator color={theme.colors.primary} style={styles.loading} />
      ) : null}

      {!tasksQuery.isPending && tasksQuery.isError ? (
        <View style={styles.stateBox}>
          <Text style={styles.error} accessibilityLiveRegion="polite">
            Nao foi possivel carregar as tarefas.
          </Text>
          <Pressable
            style={({ pressed }) => [styles.retry, pressed && styles.retryPressed]}
            onPress={() => {
              void tasksQuery.refetch();
            }}
            accessibilityRole="button"
            accessibilityLabel="Tentar carregar as tarefas novamente"
          >
            <Text style={styles.retryLabel}>Tentar novamente</Text>
          </Pressable>
        </View>
      ) : null}

      {!tasksQuery.isPending && !tasksQuery.isError && tasks.length === 0 ? (
        <Text style={styles.empty}>Nenhuma tarefa pendente.</Text>
      ) : null}

      {tasks.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          timezone={household.timezone}
          isOwnTask={currentUserId !== null && task.assignee?.user_id === currentUserId}
          busy={isSubmitting || cancelTask.isPending}
          onEdit={(selected) => setMode({ kind: 'edit', task: selected })}
          onCancel={handleCancel}
        />
      ))}

      {cancelTask.isError ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          Nao foi possivel cancelar a tarefa. Tente novamente.
        </Text>
      ) : null}
    </View>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    container: { marginTop: theme.spacing.xl },

    header: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: theme.spacing.xs,
    },
    heading: {
      ...theme.typography.label,
      color: theme.colors.textSecondary,
      textTransform: 'uppercase',
      letterSpacing: 0.6,
    },
    newButton: {
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.sm,
      borderRadius: theme.radius.sm,
    },
    newButtonPressed: { backgroundColor: theme.colors.surfaceAccent },
    newLabel: { ...theme.typography.label, color: theme.colors.primary },

    loading: { marginTop: theme.spacing.sm },

    stateBox: { marginTop: theme.spacing.sm },
    retry: {
      alignSelf: 'flex-start',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      marginTop: theme.spacing.xs,
      paddingHorizontal: theme.spacing.sm,
      borderRadius: theme.radius.sm,
      borderWidth: 1,
      borderColor: theme.colors.outlineStrong,
      backgroundColor: theme.colors.surface,
    },
    retryPressed: { backgroundColor: theme.colors.surfaceAccent },
    retryLabel: { ...theme.typography.label, color: theme.colors.primary },

    empty: {
      ...theme.typography.label,
      marginTop: theme.spacing.sm,
      color: theme.colors.textMuted,
    },
    error: { ...theme.typography.label, marginTop: theme.spacing.sm, color: theme.colors.error },
  });
