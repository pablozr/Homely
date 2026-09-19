import assert from 'node:assert/strict';
import test from 'node:test';

import { ApiError } from '@/api/client';

import { tasksApi } from './api';
import { isUndoExpiredError, partitionTasksByStatus, resolveCompletionAction } from './completion';
import type { Task } from './types';

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
    completed_by: null,
    completed_at: null,
    ...overrides,
  };
}

test('offers undo to the completing member until an expiry is recorded', () => {
  const task = { occurrence_id: 'o1', completed_by: 'u1' };
  const none = new Set<string>();
  const expired = new Set(['o1']);

  assert.equal(resolveCompletionAction(task, 'u1', none), 'undo');
  assert.equal(resolveCompletionAction(task, 'u1', expired), 'correct');
});

test('offers correction to everyone else', () => {
  const task = { occurrence_id: 'o1', completed_by: 'u1' };
  const none = new Set<string>();

  assert.equal(resolveCompletionAction(task, 'u2', none), 'correct');
  assert.equal(resolveCompletionAction(task, null, none), 'correct');
});

test('does not hide an undo based on the missing completion instant', () => {
  const task = { occurrence_id: 'o1', completed_by: 'u1' };

  assert.equal(resolveCompletionAction(task, 'u1', new Set()), 'undo');
});

test('detects the undo window expiry conflict only', () => {
  assert.equal(isUndoExpiredError(new ApiError(409, 'Undo window has expired')), true);
  assert.equal(isUndoExpiredError(new ApiError(409, 'undo window expired')), true);
  assert.equal(isUndoExpiredError(new ApiError(409, 'Task is not completed')), false);
  assert.equal(isUndoExpiredError(new ApiError(409, 'Undo window is still open')), false);
  assert.equal(isUndoExpiredError(new ApiError(409, 'Expired')), false);
  assert.equal(isUndoExpiredError(new ApiError(500, 'Undo window has expired')), false);
  assert.equal(isUndoExpiredError(new Error('Undo window has expired')), false);
  assert.equal(isUndoExpiredError(null), false);
});

async function captureUndoError(): Promise<unknown> {
  try {
    await tasksApi.undoTaskCompletion('access-1', 'h1', 'o1');
  } catch (error) {
    return error;
  }

  return null;
}

test('detects the backend envelope 409 as an expired undo window', async (context) => {
  context.mock.method(
    globalThis,
    'fetch',
    async () =>
      new Response(JSON.stringify({ message: 'Undo window has expired', data: {} }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' },
      }),
  );

  assert.equal(isUndoExpiredError(await captureUndoError()), true);
});

test('does not treat an unrelated backend envelope 409 as expiry', async (context) => {
  context.mock.method(
    globalThis,
    'fetch',
    async () =>
      new Response(JSON.stringify({ message: 'Task is not completed', data: {} }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' },
      }),
  );

  assert.equal(isUndoExpiredError(await captureUndoError()), false);
});

test('partitions pending work from completed history in order', () => {
  const pendingFirst = makeTask({ id: 'a', occurrence_id: 'a', status: 'PENDING' });
  const done = makeTask({
    id: 'b',
    occurrence_id: 'b',
    status: 'DONE',
    completed_by: 'u1',
    completed_at: '2026-01-20T20:00:00+00:00',
  });
  const pendingSecond = makeTask({ id: 'c', occurrence_id: 'c', status: 'PENDING' });
  const cancelled = makeTask({ id: 'd', occurrence_id: 'd', status: 'CANCELLED' });
  const unknown = makeTask({ id: 'e', occurrence_id: 'e', status: 'WEIRD' });

  const partition = partitionTasksByStatus([pendingFirst, done, pendingSecond, cancelled, unknown]);

  assert.deepEqual(
    partition.pending.map((task) => task.id),
    ['a', 'c'],
  );
  assert.deepEqual(
    partition.completed.map((task) => task.id),
    ['b'],
  );
});

test('returns empty sections when there are no tasks', () => {
  const partition = partitionTasksByStatus([]);

  assert.deepEqual(partition, { pending: [], completed: [] });
});
