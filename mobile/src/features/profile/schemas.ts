import { z } from 'zod';

export const fullnameSchema = z
  .string()
  .trim()
  .min(1, 'Informe um nome.')
  .max(255, 'O nome deve ter no maximo 255 caracteres.');
