import { create } from 'zustand';

type ActiveHouseholdState = {
  activeHouseholdId: string | null;

  setActiveHouseholdId: (householdId: string) => void;
  clearActiveHousehold: () => void;
};

export const useActiveHouseholdStore = create<ActiveHouseholdState>((set) => ({
  activeHouseholdId: null,

  setActiveHouseholdId: (activeHouseholdId) => set({ activeHouseholdId }),

  clearActiveHousehold: () => set({ activeHouseholdId: null }),
}));
