import { z } from 'zod';

import { isBrazilTimezone } from '@/features/households/timezones';

export const householdNameSchema = z
  .string()
  .trim()
  .min(1, 'Informe um nome para a casa.')
  .max(255, 'O nome deve ter no maximo 255 caracteres.');

export const timezoneSchema = z
  .string()
  .trim()
  .min(1, 'Informe o fuso horario.')
  .max(64, 'O fuso horario deve ter no maximo 64 caracteres.')
  .refine(isBrazilTimezone, 'Escolha um fuso horario do Brasil.');

export const householdFormSchema = z.object({
  name: householdNameSchema,
  timezone: timezoneSchema,
});

export type HouseholdForm = z.infer<typeof householdFormSchema>;
