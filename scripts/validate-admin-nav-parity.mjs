import fs from 'node:fs';

const source = fs.readFileSync(new URL('../apps/admin/components/AdminShell.tsx', import.meta.url), 'utf8');
const failures = [];

const expectedTabs = [
  'DASHBOARD', 'PMS', 'RATES', 'GROUPS', 'REQUESTS', 'AGENTS', 'RESERVATIONS',
  'SERVICES', 'DINING', 'SERVICE_SETTINGS', 'GUESTS', 'OFFERS', 'MARKETING',
  'GROWTH', 'FINANCE', 'REPORTS', 'CONTENT', 'ROOM_QR', 'POINT_QR', 'INBOX',
  'WHATSAPP', 'OPS', 'STAFF', 'SETTINGS', 'HOTEL_RULES', 'CHANNELS',
];

const tabDeclaration = source.match(/type Tab\s*=\s*([^;]+);/);
if (!tabDeclaration) {
  failures.push('Tab union declaration is missing');
} else {
  const actualTabs = [...tabDeclaration[1].matchAll(/"([A-Z_]+)"/g)].map((match) => match[1]);
  if (actualTabs.length !== 26) failures.push(`expected 26 Tab values, found ${actualTabs.length}`);
  if (new Set(actualTabs).size !== actualTabs.length) failures.push('Tab union contains duplicates');
  if (actualTabs.join('|') !== expectedTabs.join('|')) failures.push('Tab union differs from the approved 26-value baseline');
}

const navContracts = [
  ['WHATSAPP', 'canAccess("WHATSAPP")', 'WhatsApp / AI'],
  ['PMS', 'canAccess("PMS")', '{isAgent ? "Шахматка / Брони" : "Шахматка"}'],
  ['RESERVATIONS', 'canAccess("RESERVATIONS")', 'Ресепшен'],
  ['REQUESTS', 'canAccess("REQUESTS")', 'Заявки'],
  ['RATES', 'canAccess("RATES")', 'Цены / Сезоны'],
  ['SERVICES', 'canAccess("SERVICES")', 'Сервис гостя'],
  ['OPS', 'canUseOps', 'Уборка / Ремонт'],
  ['DASHBOARD', 'canAccess("DASHBOARD")', 'Главная'],
  ['FINANCE', 'canAccess("FINANCE")', 'Финансы'],
  ['GROUPS', 'canAccess("GROUPS") && moduleEnabled("GROUPS")', 'Групповая бронь'],
  ['CHANNELS', 'canAccess("CHANNELS")', 'Booking / Каналы продаж'],
  ['AGENTS', 'canAccess("AGENTS") && moduleEnabled("AGENTS")', 'Агентства'],
  ['INBOX', 'canAccess("INBOX") && moduleEnabled("INBOX")', 'Все сообщения'],
  ['GUESTS', 'canAccess("GUESTS")', 'Гости / История'],
  ['MARKETING', 'canAccess("MARKETING") && moduleEnabled("MARKETING")', 'Маркетинг'],
  ['OFFERS', 'canAccess("OFFERS") && moduleEnabled("OFFERS")', 'Предложения гостям'],
  ['GROWTH', 'canAccess("GROWTH") && moduleEnabled("GROWTH")', 'Отзывы / Рост'],
  ['DINING', 'canAccess("DINING") && moduleEnabled("DINING")', 'Питание / Ресторан'],
  ['ROOM_QR', 'canManageRoomQr && moduleEnabled("ROOM_QR")', 'QR номеров'],
  ['POINT_QR', 'canAccess("POINT_QR") && moduleEnabled("POINT_QR")', 'QR зон'],
  ['REPORTS', 'canAccess("REPORTS")', 'Отчёты / Аналитика'],
  ['STAFF', 'canAccess("STAFF")', 'Персонал'],
  ['HOTEL_RULES', 'canAccess("HOTEL_RULES")', 'Знания отеля / MARINA AI'],
  ['SERVICE_SETTINGS', 'canAccess("SERVICE_SETTINGS")', 'Настройки услуг'],
  ['CONTENT', 'canAccess("CONTENT") && moduleEnabled("CONTENT")', 'Сайт / Контент'],
  ['SETTINGS', 'canAccess("SETTINGS")', 'Настройки гостиницы'],
];

for (const [tab, gate, label] of navContracts) {
  const gateIndex = source.indexOf(`{${gate} && <button className={tab === "${tab}"`);
  if (gateIndex < 0) {
    failures.push(`${tab}: permission/module condition changed or button is missing`);
    continue;
  }
  const buttonEnd = source.indexOf('</button>}', gateIndex);
  const buttonSource = source.slice(gateIndex, buttonEnd + 10);
  if (!buttonSource.includes(`setTab("${tab}")`)) failures.push(`${tab}: navigation target changed`);
  if (!buttonSource.includes(`>${label}</button>`)) failures.push(`${tab}: label changed from baseline`);
}

if (!source.includes('{user.module_permissions.length > 0 && <details className="admin-more-menu">')) {
  failures.push('All sections permission condition changed or menu is missing');
}

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}

console.log(`Admin nav parity OK: ${expectedTabs.length} Tab values and ${navContracts.length} permission-gated nav buttons retained.`);
