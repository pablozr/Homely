import { request } from '@/api/client';

import type {
  ExchangeRequest,
  ExchangeResponse,
  MagicLinkRequest,
  MeResponse,
  MessageResponse,
  RefreshResponse,
  RefreshTokenRequest,
} from './types';

export const authApi = {
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
