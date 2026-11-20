/**
 * Dependency-free contract for a future web icon adapter.
 * Values are Lucide names, not rendered components; current screens stay unchanged.
 */
export const WEB_MODULE_ICON_MANIFEST = {
  overview: { name: 'LayoutDashboard', role: 'dashboard' },
  reception: { name: 'ConciergeBell', role: 'front-desk' },
  pms: { name: 'CalendarDays', role: 'calendar' },
  inbox: { name: 'MessageCircle', role: 'communications' },
  dining: { name: 'UtensilsCrossed', role: 'dining' },
  kitchen: { name: 'ChefHat', role: 'kitchen' },
  tasks: { name: 'ClipboardCheck', role: 'operations' },
  rooms: { name: 'BedDouble', role: 'rooms' },
  requests: { name: 'Wrench', role: 'maintenance' },
  admin: { name: 'UsersRound', role: 'staff-admin' },
  profile: { name: 'CircleUserRound', role: 'profile' },
} as const;

export type WebModuleIconKey = keyof typeof WEB_MODULE_ICON_MANIFEST;
export type WebModuleIconName = (typeof WEB_MODULE_ICON_MANIFEST)[WebModuleIconKey]['name'];
export type WebModuleIconRole = (typeof WEB_MODULE_ICON_MANIFEST)[WebModuleIconKey]['role'];
