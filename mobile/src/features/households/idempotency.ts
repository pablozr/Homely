export type IdempotencyAttempt = {
  key: string;
  signature: string;
};

export function createIdempotencyKey(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random()
    .toString(36)
    .slice(2)}`;
}

export function resolveIdempotencyAttempt(
  current: IdempotencyAttempt | null,
  signature: string,
  generate: () => string = createIdempotencyKey,
): IdempotencyAttempt {
  if (current !== null && current.signature === signature) {
    return current;
  }

  return { key: generate(), signature };
}
