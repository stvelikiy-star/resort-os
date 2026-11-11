import {
  BedDouble,
  CalendarDays,
  ChefHat,
  CircleUserRound,
  ClipboardCheck,
  ConciergeBell,
  LayoutDashboard,
  MessageCircle,
  UsersRound,
  UtensilsCrossed,
  Wrench,
} from 'lucide-react-native';
import type { LucideIcon } from 'lucide-react-native';
import type { TabKey } from '../roles/registry';

/** Visual vocabulary only. Tab visibility remains owned by the role registry. */
export const moduleIcons = {
  overview: LayoutDashboard,
  reception: ConciergeBell,
  pms: CalendarDays,
  inbox: MessageCircle,
  dining: UtensilsCrossed,
  kitchen: ChefHat,
  tasks: ClipboardCheck,
  rooms: BedDouble,
  requests: Wrench,
  admin: UsersRound,
  profile: CircleUserRound,
} as const satisfies Record<TabKey, LucideIcon>;
