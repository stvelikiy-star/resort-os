import fs from 'node:fs';

const runtime = fs.readFileSync('apps/web/components/GuestConciergeRuntime.tsx', 'utf8');
const guestLocale = fs.readFileSync('apps/web/lib/marinaGuestLocale.ts', 'utf8');
const page = fs.readFileSync('apps/web/app/g/[token]/page.tsx', 'utf8');
const css = fs.readFileSync('apps/web/app/guest-concierge.css', 'utf8');

function require(condition, message) {
  if (!condition) throw new Error(message);
}

require(page.includes('GuestConciergeRuntime'), 'Guest concierge route not mounted');
require(!page.includes('GuestRequestsPanel'), 'Duplicate legacy request panel is still mounted');
require(!page.includes('GuestOsRuntime'), 'Legacy Guest OS runtime is still mounted');
require(runtime.includes('useMarinaGuestLocale()'), 'Shared guest locale hook not mounted');
require(guestLocale.includes('marina-smart-guest-locale'), 'Guest locale persistence missing');
require(guestLocale.includes('marina-smart-site-language'), 'Guest locale continuity missing');
require(guestLocale.includes('window.localStorage.setItem(MARINA_GUEST_LOCALE_KEY, locale)'), 'Guest locale is not persisted');
require(guestLocale.includes('window.localStorage.setItem(MARINA_SITE_LOCALE_KEY, locale)'), 'Guest locale continuity is not persisted');
require(runtime.includes('setInterval(() => void loadRequests(), 15000)'), 'Request status polling missing');
require(runtime.includes('credentials: "include"'), 'Guest session cookie boundary missing');
require(runtime.includes('request_code: selected'), 'OperationalTask request code missing');
require(runtime.includes('service_date: serviceDate || null'), 'Service date payload missing');
require(runtime.includes('service_time: serviceTime || null'), 'Service time payload missing');
require(css.includes('@media(max-width:420px)'), 'Phone layout missing');
require(css.includes('.concierge-langs'), 'Compact language control missing');
console.log('PASS: Guest Concierge source/browser contract');
