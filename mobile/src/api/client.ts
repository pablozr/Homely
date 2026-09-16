import { API_URL } from './config';
import type { components, operations } from './types.generated';

type HealthResponse = operations['health_check_health_get']['responses'][200]['content']['application/json'];
type MagicLinkRequest = components['schemas']['MagicLinkRequestModel'];
type ExchangeRequest = components['schemas']['ExchangeRequestModel'];
type RefreshTokenRequest = components['schemas']['RefreshTokenRequestModel'];

export type AuthUser = {
  id: string;
  fullname: string;
  email: string;
  role: string;
  created_at: string | null;
};

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
};

export type MessageResponse = {
  message: string;
  data: Record<string, never>;
};

export type ExchangeResponse = {
  message: string;
  data: AuthTokens & { user: AuthUser };
};

export type RefreshResponse = {
  message: string;
  data: AuthTokens;
};

export type MeResponse = {
  data: { user: AuthUser };
};

type RequestOptions = {
  method?: 'GET' | 'POST';
  body?: unknown;
  token?: string;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, token } = options;
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token === undefined ? {} : { Authorization: `Bearer ${token}` }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  health(): Promise<HealthResponse> {
    return request<HealthResponse>('/health');
  },
  requestMagicLink(body: MagicLinkRequest): Promise<MessageResponse> {
    return request<MessageResponse>('/auth/magic-link', { method: 'POST', body });
  },
  exchange(body: ExchangeRequest): Promise<ExchangeResponse> {
    return request<ExchangeResponse>('/auth/exchange', { method: 'POST', body });
  },
  refresh(body: RefreshTokenRequest): Promise<RefreshResponse> {
    return request<RefreshResponse>('/auth/refresh', { method: 'POST', body });
  },
  logout(body: RefreshTokenRequest): Promise<MessageResponse> {
    return request<MessageResponse>('/auth/logout', { method: 'POST', body });
  },
  me(token: string): Promise<MeResponse> {
    return request<MeResponse>('/auth/me', { token });
  },
};
