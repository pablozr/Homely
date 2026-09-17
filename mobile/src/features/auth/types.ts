import type { components } from '@/api/types.generated';

export type MagicLinkRequest = components['schemas']['MagicLinkRequestModel'];
export type ExchangeRequest = components['schemas']['ExchangeRequestModel'];
export type RefreshTokenRequest = components['schemas']['RefreshTokenRequestModel'];

export type AuthUser = {
  id: string;
  fullname: string;
  email: string;
  role: string;
  profile_completed: boolean;
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
