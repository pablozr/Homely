import { API_URL } from './config';

export type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH';
  body?: unknown;
  token?: string;
  headers?: Record<string, string>;
};

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function extractDetailMessage(detail: unknown): string | null {
  if (typeof detail === 'string') {
    const message = detail.trim();
    return message.length > 0 ? message : null;
  }

  if (!Array.isArray(detail)) {
    return null;
  }

  for (const item of detail) {
    if (typeof item === 'string' && item.trim().length > 0) {
      return item;
    }

    if (typeof item === 'object' && item !== null) {
      const message = (item as { msg?: unknown }).msg;

      if (typeof message === 'string' && message.trim().length > 0) {
        return message;
      }
    }
  }

  return null;
}

function extractErrorMessage(body: unknown, status: number): string {
  const fallback = `API request failed: ${status}`;

  if (typeof body !== 'object' || body === null) {
    return fallback;
  }

  return extractDetailMessage((body as { detail?: unknown }).detail) ?? fallback;
}

async function readErrorBody(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error) {
    const message = error.message.trim();

    if (message.length > 0) {
      return message;
    }
  }

  return fallback;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, token, headers } = options;
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token === undefined ? {} : { Authorization: `Bearer ${token}` }),
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    const errorBody = await readErrorBody(response);

    throw new ApiError(response.status, extractErrorMessage(errorBody, response.status));
  }

  return response.json() as Promise<T>;
}
