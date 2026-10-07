/**
 * Canonical, user-facing labels for household membership roles.
 *
 * Authorization keeps comparing the raw API roles (`OWNER` / `MEMBER`); this
 * module only translates them into the calm, friendly copy shown in the app.
 */
export function membershipRoleLabel(role: string): string {
  return role === 'OWNER' ? 'Responsável' : 'Morador';
}
