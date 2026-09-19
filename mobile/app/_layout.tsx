import { QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { useTheme } from '@/design/useTheme';
import { useRestoreSession } from '@/features/auth/mutations';
import { useAuthDeepLink } from '@/features/auth/useAuthDeepLink';
import { hydratePendingInvite } from '@/features/households/invite-coordinator';
import { useInviteCoordinator } from '@/features/households/useInviteCoordinator';
import { useInviteDeepLink } from '@/features/households/useInviteDeepLink';
import { queryClient } from '@/lib/query-client';

function SessionBootstrap() {
  const { mutate: restoreSession } = useRestoreSession();

  useAuthDeepLink();
  useInviteDeepLink();
  useInviteCoordinator();

  useEffect(() => {
    void hydratePendingInvite();
    restoreSession();
  }, [restoreSession]);

  return null;
}

export default function RootLayout() {
  const theme = useTheme();

  return (
    <QueryClientProvider client={queryClient}>
      <SessionBootstrap />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: theme.colors.background },
        }}
      />
      <StatusBar style="auto" />
    </QueryClientProvider>
  );
}
