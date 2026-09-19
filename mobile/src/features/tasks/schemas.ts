import { z } from 'zod';

import { composeDueLocal, isValidDateText, isValidTimeText, splitDueLocal } from './date-time';
import type { Task, TaskCreateRequest, TaskUpdateRequest } from './types';

export const taskTitleSchema = z
  .string()
  .trim()
  .min(1, 'Informe um titulo para a tarefa.')
  .max(255, 'O titulo deve ter no maximo 255 caracteres.');

export const taskFormSchema = z
  .object({
    title: taskTitleSchema,
    assignee_membership_id: z.string().trim().min(1).nullable(),
    due_date: z.string().trim(),
    due_time: z.string().trim(),
  })
  .superRefine((value, context) => {
    const hasDate = value.due_date.length > 0;
    const hasTime = value.due_time.length > 0;

    if (hasDate && !isValidDateText(value.due_date)) {
      context.addIssue({
        code: 'custom',
        path: ['due_date'],
        message: 'Use uma data no formato DD/MM/AAAA.',
      });
    }

    if (hasTime && !isValidTimeText(value.due_time)) {
      context.addIssue({
        code: 'custom',
        path: ['due_time'],
        message: 'Use um horario no formato HH:MM.',
      });
    }

    if (hasDate && !hasTime) {
      context.addIssue({
        code: 'custom',
        path: ['due_time'],
        message: 'Informe o horario do prazo.',
      });
    }

    if (!hasDate && hasTime) {
      context.addIssue({
        code: 'custom',
        path: ['due_date'],
        message: 'Informe a data do prazo.',
      });
    }
  });

export type TaskFormValues = z.infer<typeof taskFormSchema>;

export function taskFormFromTask(task: Task): TaskFormValues {
  const { date, time } = splitDueLocal(task.due_local);

  return {
    title: task.title,
    assignee_membership_id: task.assignee?.membership_id ?? null,
    due_date: date,
    due_time: time,
  };
}

export function toTaskRequestBody(values: TaskFormValues): TaskCreateRequest {
  return {
    title: values.title,
    assignee_membership_id: values.assignee_membership_id,
    due_local: composeDueLocal(values.due_date, values.due_time),
  };
}

/**
 * Builds a PATCH body with only the fields that actually changed against the
 * original task. Fields intentionally cleared are sent as `null`; unchanged
 * fields are omitted so an overdue task can have its title edited without the
 * server re-validating an old (past) due, and an inactive assignee does not
 * block unrelated edits. Returns `undefined` when nothing changed.
 */
export function toTaskUpdateRequest(
  values: TaskFormValues,
  original: Task,
): TaskUpdateRequest | undefined {
  const body: TaskUpdateRequest = {};
  const originalAssigneeId = original.assignee?.membership_id ?? null;
  const originalDueLocal = original.due_local ?? null;
  const nextDueLocal = composeDueLocal(values.due_date, values.due_time);

  if (values.title !== original.title) {
    body.title = values.title;
  }

  if (values.assignee_membership_id !== originalAssigneeId) {
    body.assignee_membership_id = values.assignee_membership_id;
  }

  if (nextDueLocal !== originalDueLocal) {
    body.due_local = nextDueLocal;
  }

  return Object.keys(body).length === 0 ? undefined : body;
}
