import { AuthenticatedHome } from '@/features/auth/components/AuthenticatedHome';
import { MagicLinkForm } from '@/features/auth/components/MagicLinkForm';
import { RestoringSession } from '@/features/auth/components/RestoringSession';
import { useSessionStore } from '@/stores/session';

export default function HomeScreen() {
  const status = useSessionStore((state) => state.status);

  if (status === 'restoring') {
    return <RestoringSession />;
  }

  if (status === 'authenticated') {
    return <AuthenticatedHome />;
  }

  return <MagicLinkForm />;
}
