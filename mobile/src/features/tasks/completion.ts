/**
 * Client-side helpers for the one-tap completion flow.
 *
 * The backend owns the undo window: `completed_at + interval '10 seconds'` and
 * only the completing member may undo. The client never uses the device clock
 * to decide that a window closed (a slow or skewed clock would hide a still
 * valid undo), it only shows a best-effort affordance and switches to the
 * explicit correction action once the server has actually rejected an undo as
 * expired.
 */
import { ApiError } from '@/api/client';

import type { Task } from './types';

export type CompletionAction = 'undo' | 'correct';

type CompletionState = Pick<Task, 'occurrence_id' | 'completed_by'>;

/**
 * Best-effort affordance for a DONE task. Only the member who completed it may
 * undo, and only until the app has recorded a server expiry for that
 * occurrence. The backend remains the authority and will answer `409` when the
 * ten second window has actually closed.
 */
export function resolveCompletionAction(
  task: CompletionState,
  currentUserId: string | null,
  expiredOccurrenceIds: ReadonlySet<string>,
): CompletionAction {
  if (currentUserId === null || task.completed_by !== currentUserId) {
    return 'correct';
  }

  return expiredOccurrenceIds.has(task.occurrence_id) ? 'correct' : 'undo';
}

/**
 * True only for the server's `409 Undo window has expired` rejection. Unrelated
 * `409` conflicts (`Task is not completed`, stale status, ...) must not be
 * treated as window expiry.
 */
export function isUndoExpiredError(error: unknown): boolean {
  if (!(error instanceof ApiError) || error.status !== 409) {
    return false;
  }

  return /undo/i.test(error.message) && /expir/i.test(error.message);
}

export type TaskPartition = {
  pending: Task[];
  completed: Task[];
};

/**
 * Splits the household task list into the pending section and the completed
 * history, ignoring cancelled or unknown statuses so a stale row can never be
 * rendered without an action.
 */
export function partitionTasksByStatus(tasks: readonly Task[]): TaskPartition {
  const pending: Task[] = [];
  const completed: Task[] = [];

  for (const task of tasks) {
    if (task.status === 'PENDING') {
      pending.push(task);
    } else if (task.status === 'DONE') {
      completed.push(task);
    }
  }

  return { pending, completed };
}
