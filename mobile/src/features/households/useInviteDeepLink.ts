import * as Linking from 'expo-linking';
import { useEffect, useRef } from 'react';

import { inviteTokenFromUrl } from '@/lib/deep-link';
import { useSessionStore } from '@/stores/session';
import { runPendingInviteAcceptance, storePendingInvite } from './invite-coordinator';

export function useInviteDeepLink(): void {
  const url = Linking.useURL();
  const handledToken = useRef<string | null>(null);
  const inviteToken = inviteTokenFromUrl(url);

  useEffect(() => {
    if (!inviteToken || handledToken.current === inviteToken) {
      return;
    }

    handledToken.current = inviteToken;

    void (async () => {
      await storePendingInvite(inviteToken);

      if (useSessionStore.getState().status === 'authenticated') {
        await runPendingInviteAcceptance();
      }
    })();
  }, [inviteToken]);
}
