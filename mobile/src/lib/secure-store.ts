import * as SecureStore from 'expo-secure-store';

const REFRESH_TOKEN_KEY = 'homely.refresh_token';

export type TokenStore = {
  get(): Promise<string | null>;
  set(refreshToken: string): Promise<void>;
  clear(): Promise<void>;
};

export const refreshTokenStorage: TokenStore = {
  get() {
    return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  },
  set(refreshToken) {
    return SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
  },
  clear() {
    return SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  },
};
