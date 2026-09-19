import assert from 'node:assert/strict';
import test from 'node:test';

import {
  taskFormFromTask,
  taskFormSchema,
  toTaskRequestBody,
  toTaskUpdateRequest,
} from './schemas';
import type { Task } from './types';

const baseForm = {
  title: 'Lavar louca',
  assignee_membership_id: null as string | null,
  due_date: '',
  due_time: '',
};

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'o1',
    occurrence_id: 'o1',
    task_id: 't1',
    household_id: 'h1',
    title: 'Lavar louca',
    status: 'PENDING',
    assignee: null,
    due_at: null,
    due_timezone: null,
    due_local: null,
    is_overdue: false,
    created_by: 'u1',
    created_at: 'x',
    updated_at: 'x',
    cancelled_at: null,
    cancelled_by: null,
    ...overrides,
  };
}

test('accepts a valid task form and trims the title', () => {
  const parsed = taskFormSchema.safeParse({ ...baseForm, title: '  Lavar louca  ' });

  assert.equal(parsed.success, true);
  if (parsed.success) {
    assert.equal(parsed.data.title, 'Lavar louca');
  }
});

test('rejects a blank title', () => {
  assert.equal(taskFormSchema.safeParse({ ...baseForm, title: '   ' }).success, false);
});

test('rejects a date without time and a time without date', () => {
  assert.equal(
    taskFormSchema.safeParse({ ...baseForm, due_date: '20/01/2026', due_time: '' }).success,
    false,
  );
  assert.equal(
    taskFormSchema.safeParse({ ...baseForm, due_date: '', due_time: '20:00' }).success,
    false,
  );
});

test('rejects malformed date and time values', () => {
  assert.equal(
    taskFormSchema.safeParse({ ...baseForm, due_date: '31/02/2026', due_time: '20:00' }).success,
    false,
  );
  assert.equal(
    taskFormSchema.safeParse({ ...baseForm, due_date: '20/01/2026', due_time: '99:99' }).success,
    false,
  );
});

test('builds a create body with a civil due_local and optional assignee', () => {
  const parsed = taskFormSchema.parse({
    title: 'Lavar louca',
    assignee_membership_id: 'm1',
    due_date: '20/01/2026',
    due_time: '20:00',
  });

  assert.deepEqual(toTaskRequestBody(parsed), {
    title: 'Lavar louca',
    assignee_membership_id: 'm1',
    due_local: '2026-01-20T20:00',
  });

  const withoutDue = toTaskRequestBody({ ...baseForm });

  assert.deepEqual(withoutDue, {
    title: 'Lavar louca',
    assignee_membership_id: null,
    due_local: null,
  });
});

test('omits unchanged fields when editing an overdue task title', () => {
  const original = makeTask({
    assignee: { membership_id: 'm1', user_id: 'u1', fullname: 'Ada' },
    due_at: '2026-01-10T23:00:00+00:00',
    due_timezone: 'America/Sao_Paulo',
    due_local: '2026-01-10T20:00',
    is_overdue: true,
  });

  const body = toTaskUpdateRequest(
    {
      title: 'Lavar e guardar',
      assignee_membership_id: 'm1',
      due_date: '10/01/2026',
      due_time: '20:00',
    },
    original,
  );

  assert.deepEqual(body, { title: 'Lavar e guardar' });
});

test('omits an unchanged inactive assignee while editing the title', () => {
  const original = makeTask({
    assignee: { membership_id: 'm-inactive', user_id: 'u9', fullname: 'Bia' },
  });

  const body = toTaskUpdateRequest(
    {
      title: 'Nova tarefa',
      assignee_membership_id: 'm-inactive',
      due_date: '',
      due_time: '',
    },
    original,
  );

  assert.deepEqual(body, { title: 'Nova tarefa' });
});

test('sends null when clearing due and assignee', () => {
  const original = makeTask({
    assignee: { membership_id: 'm1', user_id: 'u1', fullname: 'Ada' },
    due_at: '2026-01-20T23:00:00+00:00',
    due_timezone: 'America/Sao_Paulo',
    due_local: '2026-01-20T20:00',
  });

  const body = toTaskUpdateRequest(
    {
      title: 'Lavar louca',
      assignee_membership_id: null,
      due_date: '',
      due_time: '',
    },
    original,
  );

  assert.deepEqual(body, { assignee_membership_id: null, due_local: null });
});

test('returns undefined when the edit changes nothing', () => {
  const original = makeTask({
    assignee: { membership_id: 'm1', user_id: 'u1', fullname: 'Ada' },
    due_at: '2026-01-20T23:00:00+00:00',
    due_timezone: 'America/Sao_Paulo',
    due_local: '2026-01-20T20:00',
  });

  const body = toTaskUpdateRequest(
    {
      title: 'Lavar louca',
      assignee_membership_id: 'm1',
      due_date: '20/01/2026',
      due_time: '20:00',
    },
    original,
  );

  assert.equal(body, undefined);
});

test('prefills the form from an existing task', () => {
  const task = {
    id: 'o1',
    occurrence_id: 'o1',
    task_id: 't1',
    household_id: 'h1',
    title: 'Lavar louca',
    status: 'PENDING',
    assignee: { membership_id: 'm1', user_id: 'u1', fullname: 'Ada' },
    due_at: '2026-01-20T23:00:00+00:00',
    due_timezone: 'America/Sao_Paulo',
    due_local: '2026-01-20T20:00',
    is_overdue: false,
    created_by: 'u1',
    created_at: 'x',
    updated_at: 'x',
    cancelled_at: null,
    cancelled_by: null,
  } as Task;

  assert.deepEqual(taskFormFromTask(task), {
    title: 'Lavar louca',
    assignee_membership_id: 'm1',
    due_date: '20/01/2026',
    due_time: '20:00',
  });
});
