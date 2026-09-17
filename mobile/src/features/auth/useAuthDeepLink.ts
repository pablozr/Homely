import * as Linking from 'expo-linking';
import { useRouter } from 'expo-router';
import { useEffect, useRef } from 'react';

import { authCodeFromUrl } from '@/lib/deep-link';
import { useExchangeMagicLink } from './mutations';

export function useAuthDeepLink(): void {
  const url = Linking.useURL();
  const router = useRouter();
  const { mutate: exchange } = useExchangeMagicLink();
  const handledCode = useRef<string | null>(null);

  const authCode = authCodeFromUrl(url);

  useEffect(() => {
    if (!authCode || handledCode.current === authCode) {
      return;
    }

    exchange(authCode, {
      onSuccess: () => {
        handledCode.current = authCode;
        router.replace('/');
      },
    });
  }, [authCode, exchange, router]);
}
