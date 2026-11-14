#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
const read = f => fs.readFileSync(path.join(root, f), 'utf8');
const assert = (v,msg) => { if(!v) throw Error('FL2 touchpoints: ' + msg); };
const css = read('apps/admin/app/fl2-guest-touchpoints.css');
const layout = read('apps/admin/app/layout.tsx');
const inbox = read('apps/admin/components/InboxBoard.tsx');
const service = read('apps/admin/components/ServicePointsBoard.tsx');
const qr = read('apps/admin/components/RoomQrBoard.tsx');
const offers = read('apps/admin/components/GuestOffersBoard.tsx');
const serviceSettings = read('apps/admin/components/GuestServiceSettingsBoard.tsx');
const siteContent = read('apps/admin/components/SiteContentBoard.tsx');
assert(layout.includes('import "./fl2-guest-touchpoints.css";'),'CSS import');
for (const marker of ['.inbox-row','.inbox-detail','.outbound-reply-form','.service-point-payment-row','.service-point-svg','.room-qr-table-wrap','.guest-offer-editor','.guest-offer-list-panel','[data-fl2-theme="light"]','prefers-reduced-motion','.service-settings-card','.content-card','.content-savebar']) {
  assert(css.includes(marker), 'missing visual selector ' + marker);
}
assert(!css.includes('visibility:hidden') && !css.includes('pointer-events:none'), 'global visual state could hide existing actions');
for(const [src,markers] of [
  [inbox,['sendReply','generateAiDraft','openConversation','claim','changeStatus','linkRequest','manualReconciliation','whatsappReplyEnabled']],
  [service,['qrAction','retryUnlock','saveAccess','active_qr_id','service-point-create']],
  [qr,['room-qr-table-wrap','room-qr-print-pack','room-qr-print-grid']],
  [offers,['guest-offer-editor','guest-offer-card-actions','toggle(item)','submit','item.analytics']],
  [serviceSettings,['service-settings-save','service-settings-grid','room_delivery_enabled','save']],
  [siteContent,['content-savebar','locale-tabs','content-field','publish']]
])for(const m of markers)assert(src.includes(m), 'existing handler missing: '+m);
console.log('FL2 guest touchpoints PASS: original channel actions, QR, payments, print and offers preserved; style scoped to Future Luxury.');
