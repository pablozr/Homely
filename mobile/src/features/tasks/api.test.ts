import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { API_URL } from '@/api/config';
import { tasksApi } from './api';

type CapturedRequest = {
  url: string;
  init?: RequestInit;
};

function mockFetch(context: TestContext, body: unknown, status = 200) {
  const calls: CapturedRequest[] = [];

  context.mock.method(globalThis, 'fetch', async (...args: Parameters<typeof fetch>) => {
    calls.push({ url: String(args[0]), init: args[1] });
    return new Response(JSON.stringify(body), { status });
  });

  return calls;
}

const task = {
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
};

test('creates a task with the access token and idempotency key', async (context) => {
  const calls = mockFetch(context, { message: 'Task created', data: { task } }, 201);

  const body = {
    title: 'Lavar louca',
    assignee_membership_id: 'm1',
    due_local: '2026-01-20T20:00',
  };

  const response = await tasksApi.createTask('access-1', 'h1', body, 'idem-1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/tasks`);
  assert.equal(calls[0].init?.method, 'POST');

  const headers = calls[0].init?.headers as Record<string, string>;
  assert.equal(headers.Authorization, 'Bearer access-1');
  assert.equal(headers['Idempotency-Key'], 'idem-1');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), body);
  assert.equal(response.data.task.title, 'Lavar louca');
});

test('lists pending tasks for a household', async (context) => {
  const calls = mockFetch(context, { message: 'Tasks retrieved', data: { tasks: [task] } });

  const response = await tasksApi.listTasks('access-1', 'h1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/tasks`);
  assert.equal(calls[0].init?.method, 'GET');
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.equal(response.data.tasks[0].occurrence_id, 'o1');
});

test('updates a task with a PATCH body', async (context) => {
  const calls = mockFetch(context, {
    message: 'Task updated',
    data: { task: { ...task, title: 'Lavar e guardar' } },
  });

  const response = await tasksApi.updateTask('access-1', 'h1', 'o1', {
    title: 'Lavar e guardar',
    assignee_membership_id: null,
    due_local: null,
  });

  assert.equal(calls[0].url, `${API_URL}/households/h1/tasks/o1`);
  assert.equal(calls[0].init?.method, 'PATCH');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
    title: 'Lavar e guardar',
    assignee_membership_id: null,
    due_local: null,
  });
  assert.equal(response.data.task.title, 'Lavar e guardar');
});

test('cancels a task with a bodyless POST', async (context) => {
  const calls = mockFetch(context, {
    message: 'Task cancelled',
    data: { task: { ...task, status: 'CANCELLED' } },
  });

  const response = await tasksApi.cancelTask('access-1', 'h1', 'o1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/tasks/o1/cancel`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.equal(calls[0].init?.body, undefined);
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.equal(response.data.task.status, 'CANCELLED');
});

test('completes a task with a bodyless POST', async (context) => {
  const calls = mockFetch(context, {
    message: 'Task completed',
    data: {
      task: { ...task, status: 'DONE', completed_by: 'u1', completed_at: '2026-01-20T20:00:00Z' },
    },
  });

  const response = await tasksApi.completeTask('access-1', 'h1', 'o1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/tasks/o1/complete`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.equal(calls[0].init?.body, undefined);
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.equal(response.data.task.completed_by, 'u1');
});

test('undoes a task completion with a bodyless POST', async (context) => {
  const calls = mockFetch(context, {
    message: 'Task completion undone',
    data: { task },
  });

  const response = await tasksApi.undoTaskCompletion('access-1', 'h1', 'o1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/tasks/o1/undo-completion`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.equal(calls[0].init?.body, undefined);
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.equal(response.data.task.status, 'PENDING');
});

test('corrects a task completion with a bodyless POST', async (context) => {
  const calls = mockFetch(context, {
    message: 'Task completion corrected',
    data: { task },
  });

  const response = await tasksApi.correctTaskCompletion('access-1', 'h1', 'o1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/tasks/o1/correct-completion`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.equal(calls[0].init?.body, undefined);
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.equal(response.data.task.status, 'PENDING');
});
