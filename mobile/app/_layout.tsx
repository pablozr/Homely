import { QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { useRestoreSession } from '@/features/auth/mutations';
import { useAuthDeepLink } from '@/features/auth/useAuthDeepLink';
import { queryClient } from '@/lib/query-client';

function SessionBootstrap() {
  const { mutate: restoreSession } = useRestoreSession();

  useAuthDeepLink();

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  return null;
}

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <SessionBootstrap />
      <Stack screenOptions={{ headerShown: false }} />
      <StatusBar style="dark" />
    </QueryClientProvider>
  );
}
