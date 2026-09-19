import { z } from 'zod';

export const INVITE_TOKEN_MAX_LENGTH = 255;
export const PENDING_INVITE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

const inviteTokenSchema = z.string().trim().min(1).max(INVITE_TOKEN_MAX_LENGTH);

export function parseInviteToken(value: unknown): string | null {
  const parsed = inviteTokenSchema.safeParse(value);

  return parsed.success ? parsed.data : null;
}

export type PendingInvite = {
  token: string;
  savedAt: number;
};

const pendingInviteSchema = z.object({
  token: inviteTokenSchema,
  savedAt: z.number().int().nonnegative(),
});

export function createPendingInvite(token: string, now: number = Date.now()): PendingInvite {
  return { token, savedAt: now };
}

export function isPendingInviteExpired(invite: PendingInvite, now: number = Date.now()): boolean {
  return now - invite.savedAt >= PENDING_INVITE_TTL_MS;
}

export function parsePendingInvite(
  raw: string | null,
  now: number = Date.now(),
): PendingInvite | null {
  if (raw === null) {
    return null;
  }

  let value: unknown;

  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }

  const parsed = pendingInviteSchema.safeParse(value);

  if (!parsed.success || isPendingInviteExpired(parsed.data, now)) {
    return null;
  }

  return parsed.data;
}

export type PendingInviteStore = {
  get(now?: number): Promise<PendingInvite | null>;
  save(token: string, now?: number): Promise<PendingInvite>;
  clear(): Promise<void>;
};
