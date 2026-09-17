import { useMutation } from '@tanstack/react-query';

import { refreshTokenStorage } from '@/lib/secure-store';
import { authApi } from './api';
import { establishSessionFromCode, restoreSession, signOut } from './session';

export function useRequestMagicLink() {
  return useMutation({
    mutationFn: (email: string) => authApi.requestMagicLink({ email }),
  });
}

export function useExchangeMagicLink() {
  return useMutation({
    mutationFn: (authCode: string) => establishSessionFromCode(authCode, refreshTokenStorage),
  });
}

export function useRestoreSession() {
  return useMutation({
    mutationFn: () => restoreSession(refreshTokenStorage),
  });
}

export function useSignOut() {
  return useMutation({
    mutationFn: () => signOut(refreshTokenStorage),
  });
}
