import { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';
import type { MemberSummary } from '@/features/households/types';
import { normalizeDefaultDueTime } from '@/features/tasks/date-time';
import { taskFormFromTask, taskFormSchema, type TaskFormValues } from '@/features/tasks/schemas';
import type { Task } from '@/features/tasks/types';

type TaskFormProps = {
  members: MemberSummary[];
  defaultDueTime: string;
  initialTask: Task | null;
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (values: TaskFormValues) => void;
  onCancel: () => void;
};

const EMPTY_VALUES: TaskFormValues = {
  title: '',
  assignee_membership_id: null,
  due_date: '',
  due_time: '',
};

export function TaskForm({
  members,
  defaultDueTime,
  initialTask,
  isSubmitting,
  errorMessage,
  onSubmit,
  onCancel,
}: TaskFormProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const initialValues = useMemo(
    () => (initialTask ? taskFormFromTask(initialTask) : EMPTY_VALUES),
    [initialTask],
  );
  const [title, setTitle] = useState(initialValues.title);
  const [assigneeId, setAssigneeId] = useState<string | null>(initialValues.assignee_membership_id);
  const [dueDate, setDueDate] = useState(initialValues.due_date);
  const [dueTime, setDueTime] = useState(initialValues.due_time);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const defaultTime = normalizeDefaultDueTime(defaultDueTime);

  function handleDateChange(value: string) {
    setDueDate(value);
    setDueTime((current) => {
      if (value.trim().length === 0) {
        return '';
      }

      return current.trim().length > 0 ? current : defaultTime;
    });
  }

  function handleSubmit() {
    const parsed = taskFormSchema.safeParse({
      title,
      assignee_membership_id: assigneeId,
      due_date: dueDate,
      due_time: dueTime,
    });

    if (!parsed.success) {
      const nextErrors: Record<string, string> = {};

      for (const issue of parsed.error.issues) {
        const key = String(issue.path[0] ?? 'form');

        if (!nextErrors[key]) {
          nextErrors[key] = issue.message;
        }
      }

      setErrors(nextErrors);
      return;
    }

    setErrors({});
    onSubmit(parsed.data);
  }

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Titulo</Text>
      <TextInput
        style={styles.input}
        value={title}
        onChangeText={setTitle}
        placeholder="Ex.: Lavar louca"
        placeholderTextColor={theme.colors.placeholder}
        editable={!isSubmitting}
        maxLength={255}
        accessibilityLabel="Titulo da tarefa"
      />
      {errors.title ? (
        <Text style={styles.fieldError} accessibilityLiveRegion="polite">
          {errors.title}
        </Text>
      ) : null}

      <Text style={styles.label}>Responsavel</Text>
      <Pressable
        style={({ pressed }) => [
          styles.assignee,
          assigneeId === null && styles.assigneeSelected,
          pressed && !isSubmitting && styles.assigneePressed,
        ]}
        onPress={() => setAssigneeId(null)}
        disabled={isSubmitting}
        accessibilityRole="button"
        accessibilityLabel="Sem responsavel"
        accessibilityState={{ selected: assigneeId === null, disabled: isSubmitting }}
      >
        <Text style={styles.assigneeLabel}>Sem responsável</Text>
      </Pressable>

      {members.map((member) => {
        const selected = member.id === assigneeId;

        return (
          <Pressable
            key={member.id}
            style={({ pressed }) => [
              styles.assignee,
              selected && styles.assigneeSelected,
              pressed && !isSubmitting && styles.assigneePressed,
            ]}
            onPress={() => setAssigneeId(member.id)}
            disabled={isSubmitting}
            accessibilityRole="button"
            accessibilityLabel={`Responsavel ${member.fullname}`}
            accessibilityState={{ selected, disabled: isSubmitting }}
          >
            <Text style={styles.assigneeLabel}>{member.fullname}</Text>
          </Pressable>
        );
      })}

      <Text style={styles.label}>Prazo (opcional)</Text>
      <View style={styles.dueRow}>
        <TextInput
          style={[styles.input, styles.dueInput, styles.dueDateInput]}
          value={dueDate}
          onChangeText={handleDateChange}
          placeholder="DD/MM/AAAA"
          placeholderTextColor={theme.colors.placeholder}
          editable={!isSubmitting}
          keyboardType="numbers-and-punctuation"
          maxLength={10}
          accessibilityLabel="Data do prazo"
        />
        <TextInput
          style={[styles.input, styles.dueInput]}
          value={dueTime}
          onChangeText={setDueTime}
          placeholder="HH:MM"
          placeholderTextColor={theme.colors.placeholder}
          editable={!isSubmitting}
          keyboardType="numbers-and-punctuation"
          maxLength={5}
          accessibilityLabel="Horario do prazo"
        />
      </View>
      {errors.due_date ? (
        <Text style={styles.fieldError} accessibilityLiveRegion="polite">
          {errors.due_date}
        </Text>
      ) : null}
      {errors.due_time ? (
        <Text style={styles.fieldError} accessibilityLiveRegion="polite">
          {errors.due_time}
        </Text>
      ) : null}

      {errorMessage ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {errorMessage}
        </Text>
      ) : null}

      <Pressable
        style={({ pressed }) => [
          styles.submit,
          pressed && !isSubmitting && styles.submitPressed,
          isSubmitting && styles.disabled,
        ]}
        onPress={handleSubmit}
        disabled={isSubmitting}
        accessibilityRole="button"
        accessibilityLabel={initialTask ? 'Salvar tarefa' : 'Criar tarefa'}
        accessibilityState={{ disabled: isSubmitting, busy: isSubmitting }}
      >
        {isSubmitting ? (
          <ActivityIndicator color={theme.colors.textOnPrimary} />
        ) : (
          <Text style={styles.submitLabel}>{initialTask ? 'Salvar' : 'Criar tarefa'}</Text>
        )}
      </Pressable>

      <Pressable
        style={({ pressed }) => [
          styles.cancel,
          pressed && !isSubmitting && styles.cancelPressed,
          isSubmitting && styles.disabled,
        ]}
        onPress={onCancel}
        disabled={isSubmitting}
        accessibilityRole="button"
        accessibilityLabel="Fechar formulario de tarefa"
        accessibilityState={{ disabled: isSubmitting }}
      >
        <Text style={styles.cancelLabel}>Cancelar</Text>
      </Pressable>
    </View>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    container: {
      marginTop: theme.spacing.sm,
      padding: theme.spacing.md,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outlineStrong,
      backgroundColor: theme.colors.surfaceElevated,
    },

    label: {
      ...theme.typography.caption,
      marginTop: theme.spacing.sm,
      color: theme.colors.textSecondary,
      textTransform: 'uppercase',
      letterSpacing: 0.6,
    },

    input: {
      ...theme.typography.body,
      marginTop: theme.spacing.xs,
      minHeight: 48,
      paddingHorizontal: theme.spacing.md,
      paddingVertical: theme.spacing.sm,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outline,
      backgroundColor: theme.colors.surface,
      color: theme.colors.textPrimary,
    },

    assignee: {
      marginTop: theme.spacing.xs,
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.md,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outline,
      backgroundColor: theme.colors.surface,
    },
    assigneeSelected: {
      borderColor: theme.colors.primary,
      backgroundColor: theme.colors.primarySubtle,
    },
    assigneePressed: { backgroundColor: theme.colors.surfaceAccent },
    assigneeLabel: { ...theme.typography.label, color: theme.colors.textPrimary },

    dueRow: { flexDirection: 'row', gap: theme.spacing.xs },
    dueInput: { flex: 1 },
    dueDateInput: { flex: 1.4 },

    fieldError: {
      ...theme.typography.label,
      marginTop: theme.spacing.xs,
      color: theme.colors.error,
    },
    error: { ...theme.typography.label, marginTop: theme.spacing.sm, color: theme.colors.error },

    submit: {
      marginTop: theme.spacing.md,
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.lg,
      borderRadius: theme.radius.md,
      backgroundColor: theme.colors.primary,
    },
    submitPressed: { backgroundColor: theme.colors.primaryPressed },
    submitLabel: { ...theme.typography.bodyStrong, color: theme.colors.textOnPrimary },

    cancel: {
      marginTop: theme.spacing.xs,
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.lg,
      borderRadius: theme.radius.md,
      borderWidth: 1,
      borderColor: theme.colors.outlineStrong,
      backgroundColor: theme.colors.surface,
    },
    cancelPressed: { backgroundColor: theme.colors.surfaceAccent },
    cancelLabel: { ...theme.typography.bodyStrong, color: theme.colors.primary },

    disabled: { opacity: 0.6 },
  });
