import { useMutation } from '@tanstack/react-query';

import { updateProfile } from './update-profile';

export function useUpdateProfile() {
  return useMutation({
    mutationFn: (fullname: string) => updateProfile(fullname),
  });
}
