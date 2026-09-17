import { MagicLinkForm } from '@/features/auth/components/MagicLinkForm';
import { RestoringSession } from '@/features/auth/components/RestoringSession';
import { HouseholdGate } from '@/features/households/components/HouseholdGate';
import { ProfileSetup } from '@/features/profile/components/ProfileSetup';
import { useSessionStore } from '@/stores/session';

export default function HomeScreen() {
  const status = useSessionStore((state) => state.status);
  const profileCompleted = useSessionStore((state) => state.user?.profile_completed ?? false);

  if (status === 'restoring') {
    return <RestoringSession />;
  }

  if (status === 'authenticated') {
    return profileCompleted ? <HouseholdGate /> : <ProfileSetup />;
  }

  return <MagicLinkForm />;
}
