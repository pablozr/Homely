import { z } from 'zod';

import { parseInviteToken } from '@/lib/pending-invite';

const authCodeSchema = z.string().trim().min(1);

export function authCodeFromUrl(url: string | null): string | null {
  if (!url) {
    return null;
  }

  try {
    const parsed = authCodeSchema.safeParse(new URL(url).searchParams.get('auth_code'));

    return parsed.success ? parsed.data : null;
  } catch {
    return null;
  }
}

export function inviteTokenFromUrl(url: string | null): string | null {
  if (!url) {
    return null;
  }

  try {
    return parseInviteToken(new URL(url).searchParams.get('invite_token'));
  } catch {
    return null;
  }
}

function looksLikeInviteUrl(value: string): boolean {
  return value.includes('://') || value.includes('invite_token=');
}

export function inviteTokenFromInput(input: string): string | null {
  const trimmed = input.trim();

  if (trimmed.length === 0) {
    return null;
  }

  if (looksLikeInviteUrl(trimmed)) {
    return inviteTokenFromUrl(trimmed);
  }

  return parseInviteToken(trimmed);
}
