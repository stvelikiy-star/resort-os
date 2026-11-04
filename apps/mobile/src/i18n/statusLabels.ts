import type { MobileCopy } from './mobileCopy';

type Translations = Pick<MobileCopy,
  'chatOpen' | 'chatWaitingGuest' | 'chatWaitingStaff' | 'chatResolved' | 'chatArchived' |
  'messageIncoming' | 'messageOutgoing' | 'messageInternal' |
  'messageSent' | 'messageDelivered' | 'messageRead' | 'messageFailed' |
  'orderNew' | 'orderAccepted' | 'orderCooking' | 'orderReady' | 'orderServed' | 'orderCancelled' |
  'tableAvailable' | 'tableOccupied' | 'tableReserved' | 'tableUnknown'
>;

/** Display-only mapping: never changes the server status or grants an operation. */
export function chatStatusLabel(code: string, c: Translations): string {
  switch (code) {
    case 'OPEN': return c.chatOpen;
    case 'WAITING_GUEST': return c.chatWaitingGuest;
    case 'WAITING_STAFF': return c.chatWaitingStaff;
    case 'RESOLVED': return c.chatResolved;
    case 'ARCHIVED': return c.chatArchived;
    default: return code;
  }
}
export function messageDirectionLabel(code: string, c: Translations): string {
  switch (code) {
    case 'INBOUND': return c.messageIncoming;
    case 'OUTBOUND': return c.messageOutgoing;
    case 'INTERNAL': return c.messageInternal;
    default: return code;
  }
}
export function deliveryStatusLabel(code: string, c: Translations): string {
  switch (code) {
    case 'SENT': return c.messageSent;
    case 'DELIVERED': return c.messageDelivered;
    case 'READ': return c.messageRead;
    case 'FAILED': return c.messageFailed;
    default: return code;
  }
}
export function orderStatusLabel(code: string, c: Translations): string {
  switch (code) {
    case 'NEW': return c.orderNew;
    case 'ACCEPTED': return c.orderAccepted;
    case 'COOKING': return c.orderCooking;
    case 'READY': return c.orderReady;
    case 'SERVED': return c.orderServed;
    case 'CANCELLED': return c.orderCancelled;
    default: return code;
  }
}
/** Table state comes from the server; unrecognized codes never mean an empty table. */
export function diningTableStatusLabel(code: string, copy: Translations): string {
  switch (code) {
    case 'AVAILABLE':
    case 'FREE': return copy.tableAvailable;
    case 'OCCUPIED': return copy.tableOccupied;
    case 'RESERVED': return copy.tableReserved;
    default: return copy.tableUnknown;
  }
}
export function contactInitials(name: string | null): string | null {
  const trimmed = name?.trim();
  if (!trimmed) return null;
  const pieces = trimmed.split(/\s+/);
  return (pieces.length > 1 ? pieces[0].slice(0, 1) + pieces[pieces.length - 1].slice(0, 1) : trimmed.slice(0, 2)).toLocaleUpperCase();
}
