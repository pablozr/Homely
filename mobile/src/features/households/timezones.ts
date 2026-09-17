export type BrazilTimezoneOption = {
  id: string;
  city: string;
  label: string;
};

const SAO_PAULO: BrazilTimezoneOption = {
  id: 'America/Sao_Paulo',
  city: 'São Paulo',
  label: 'São Paulo, Brasil',
};

export const FALLBACK_TIMEZONE = SAO_PAULO.id;

export const BRAZIL_TIMEZONES: readonly BrazilTimezoneOption[] = [
  SAO_PAULO,
  { id: 'America/Noronha', city: 'Fernando de Noronha', label: 'Fernando de Noronha, Brasil' },
  { id: 'America/Manaus', city: 'Manaus', label: 'Manaus, Brasil' },
  { id: 'America/Cuiaba', city: 'Cuiabá', label: 'Cuiabá, Brasil' },
  { id: 'America/Rio_Branco', city: 'Rio Branco', label: 'Rio Branco, Brasil' },
];

function normalize(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

export function findBrazilTimezone(id: string): BrazilTimezoneOption | undefined {
  const trimmed = id.trim();

  return BRAZIL_TIMEZONES.find((option) => option.id === trimmed);
}

export function isBrazilTimezone(id: string): boolean {
  return findBrazilTimezone(id) !== undefined;
}

export function timezoneLabel(id: string): string {
  return findBrazilTimezone(id)?.label ?? id;
}

export function filterBrazilTimezones(query: string): BrazilTimezoneOption[] {
  const normalizedQuery = normalize(query);

  if (normalizedQuery.length === 0) {
    return [...BRAZIL_TIMEZONES];
  }

  return BRAZIL_TIMEZONES.filter((option) =>
    normalize(`${option.city} ${option.label} ${option.id}`).includes(normalizedQuery),
  );
}

export function resolveBrazilTimezone(
  resolvedTimezone: string | undefined | null,
): BrazilTimezoneOption {
  if (resolvedTimezone) {
    const matched = findBrazilTimezone(resolvedTimezone);

    if (matched) {
      return matched;
    }
  }

  return SAO_PAULO;
}

export function defaultTimezone(): string {
  return resolveBrazilTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone).id;
}
