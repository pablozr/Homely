/**
 * Civil date/time helpers for the tasks feature.
 *
 * The backend expects `due_local` as a local civil string (`YYYY-MM-DDTHH:mm`,
 * no offset) in the household timezone. These helpers work purely on strings so
 * the UI never routes a civil value through `new Date('YYYY-MM-DD...')`, which
 * would reinterpret it as UTC and shift the wall-clock time.
 */

export const DEFAULT_DUE_TIME = '20:00';

const DATE_TEXT_PATTERN = /^(\d{2})\/(\d{2})\/(\d{4})$/;
const TIME_TEXT_PATTERN = /^(\d{2}):(\d{2})$/;
const DUE_LOCAL_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/;

const DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

function isLeapYear(year: number): boolean {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

export function isValidDateText(value: string): boolean {
  const match = DATE_TEXT_PATTERN.exec(value.trim());

  if (!match) {
    return false;
  }

  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = Number(match[3]);

  if (month < 1 || month > 12 || day < 1) {
    return false;
  }

  const maxDay = month === 2 && isLeapYear(year) ? 29 : DAYS_IN_MONTH[month - 1];

  return day <= maxDay;
}

export function isValidTimeText(value: string): boolean {
  const match = TIME_TEXT_PATTERN.exec(value.trim());

  if (!match) {
    return false;
  }

  const hours = Number(match[1]);
  const minutes = Number(match[2]);

  return hours >= 0 && hours <= 23 && minutes >= 0 && minutes <= 59;
}

export function isValidDueLocal(value: string): boolean {
  return DUE_LOCAL_PATTERN.test(value.trim());
}

/**
 * Builds the backend civil string from the display date/time inputs. Returns
 * `null` when there is no date (no due), and `null` when either input is
 * malformed so callers can rely on schema validation to surface the error.
 */
export function composeDueLocal(dateText: string, timeText: string): string | null {
  const date = dateText.trim();
  const time = timeText.trim();

  if (date.length === 0) {
    return null;
  }

  const dateMatch = DATE_TEXT_PATTERN.exec(date);
  const timeMatch = TIME_TEXT_PATTERN.exec(time);

  if (!dateMatch || !timeMatch) {
    return null;
  }

  if (!isValidDateText(date) || !isValidTimeText(time)) {
    return null;
  }

  return `${dateMatch[3]}-${dateMatch[2]}-${dateMatch[1]}T${timeMatch[1]}:${timeMatch[2]}`;
}

/** Splits a civil `due_local` value back into display inputs. */
export function splitDueLocal(dueLocal: string | null | undefined): { date: string; time: string } {
  if (!dueLocal) {
    return { date: '', time: '' };
  }

  const match = DUE_LOCAL_PATTERN.exec(dueLocal.trim());

  if (!match) {
    return { date: '', time: '' };
  }

  const [, year, month, day, hours, minutes] = match;

  return { date: `${day}/${month}/${year}`, time: `${hours}:${minutes}` };
}

/** Normalizes a household `default_due_time` (`HH:MM:SS`) into `HH:MM`. */
export function normalizeDefaultDueTime(value: string | null | undefined): string {
  if (!value) {
    return DEFAULT_DUE_TIME;
  }

  const match = /^(\d{2}):(\d{2})/.exec(value.trim());

  if (!match) {
    return DEFAULT_DUE_TIME;
  }

  const candidate = `${match[1]}:${match[2]}`;

  return isValidTimeText(candidate) ? candidate : DEFAULT_DUE_TIME;
}

/** Formats a UTC instant (`due_at`) in pt-BR within the household timezone. */
export function formatDueAt(dueAt: string, timezone: string): string {
  const instant = new Date(dueAt);

  if (Number.isNaN(instant.getTime())) {
    return '';
  }

  try {
    return new Intl.DateTimeFormat('pt-BR', {
      timeZone: timezone,
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(instant);
  } catch {
    return instant.toISOString();
  }
}
