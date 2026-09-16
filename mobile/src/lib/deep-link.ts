import { z } from 'zod';

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
