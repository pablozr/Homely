import { useEffect, useRef } from 'react';

import { useSessionStore } from '@/stores/session';
import { runPendingInviteAcceptance } from './invite-coordinator';

export function useInviteCoordinator(): void {
  const status = useSessionStore((state) => state.status);
  const accessToken = useSessionStore((state) => state.accessToken);
  const attemptedFor = useRef<string | null>(null);

  useEffect(() => {
    if (status !== 'authenticated' || !accessToken) {
      attemptedFor.current = null;
      return;
    }

    if (attemptedFor.current === accessToken) {
      return;
    }

    attemptedFor.current = accessToken;

    void runPendingInviteAcceptance();
  }, [status, accessToken]);
}
