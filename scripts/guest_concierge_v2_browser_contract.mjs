import fs from 'node:fs';

const runtime = fs.readFileSync('apps/web/components/GuestConciergeRuntime.tsx', 'utf8');
const page = fs.readFileSync('apps/web/app/g/[token]/page.tsx', 'utf8');
const css = fs.readFileSync('apps/web/app/guest-concierge.css', 'utf8');

function require(condition, message) {
  if (!condition) throw new Error(message);
}

require(page.includes('GuestConciergeRuntime'), 'Guest concierge route not mounted');
require(!page.includes('GuestRequestsPanel'), 'Duplicate legacy request panel is still mounted');
require(!page.includes('GuestOsRuntime'), 'Legacy Guest OS runtime is still mounted');
require(runtime.includes('three-crowns-guest-language'), 'Guest locale persistence missing');
require(runtime.includes('three-crowns-site-language'), 'Public-site locale continuity missing');
require(runtime.includes('setInterval(() => void loadRequests(), 15000)'), 'Request status polling missing');
require(runtime.includes('credentials: "include"'), 'Guest session cookie boundary missing');
require(runtime.includes('request_code: selected'), 'OperationalTask request code missing');
require(runtime.includes('service_date: serviceDate || null'), 'Service date payload missing');
require(runtime.includes('service_time: serviceTime || null'), 'Service time payload missing');
require(css.includes('@media(max-width:420px)'), 'Phone layout missing');
require(css.includes('.concierge-langs'), 'Compact language control missing');
console.log('PASS: Guest Concierge source/browser contract');
