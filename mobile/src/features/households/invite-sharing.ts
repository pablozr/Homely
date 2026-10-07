/**
 * Pure helpers for sharing a freshly created household invite.
 *
 * The secret invite URL is only ever returned by the create-invite response;
 * these helpers turn it into deterministic, human-readable copy and the
 * matching WhatsApp share URL.
 */
export type InviteMessageInput = {
  fullname: string;
  householdName: string;
  inviteUrl: string;
};

export function buildInviteMessage({
  fullname,
  householdName,
  inviteUrl,
}: InviteMessageInput): string {
  return `${fullname} convidou você para entrar em “${householdName}” no Homely.\n\n${inviteUrl}`;
}

export function buildWhatsAppShareUrl(message: string): string {
  return `https://wa.me/?text=${encodeURIComponent(message)}`;
}
