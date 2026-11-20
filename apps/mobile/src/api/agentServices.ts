import { ApiError } from './types';
import { safeRouteId } from './routeId';

export const AGENT_SERVICES = ['TRANSFER', 'MEALS', 'PARKING', 'SAUNA', 'BILLIARDS', 'EXCURSIONS'] as const;
export type AgentServiceCode = typeof AGENT_SERVICES[number];
export type AgentServiceDraft = { service_date?: string; service_time?: string; description?: string };
export type AgentServiceStatus = 'OPEN' | 'IN_PROGRESS' | 'DONE' | 'CANCELLED';
export interface AgentServiceRecord {
  id: string; reservation_id: string; service_code: AgentServiceCode; status: AgentServiceStatus;
  service_date: string | null; service_time: string | null; description: string | null;
}
export interface AgentServiceList {
  reservation_id: string; items: AgentServiceRecord[]; preview_limit: number; preview_truncated: boolean;
}
export function validServiceDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d = new Date(value + 'T00:00:00Z');
  return Number.isFinite(d.getTime()) && d.toISOString().slice(0, 10) === value;
}
export function agentServiceDraft(draft: AgentServiceDraft): AgentServiceDraft {
  const date = draft.service_date?.trim();
  const time = draft.service_time?.trim();
  const description = draft.description?.trim();
  if ((date && !validServiceDate(date)) || (time && (!date || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(time))) ||
      (description && description.length > 2000)) throw new ApiError('BAD_REQUEST', 'Invalid service schedule or note');
  return { ...(date ? { service_date: date } : {}), ...(time ? { service_time: time } : {}),
    ...(description ? { description } : {}) };
}
export function agentServiceList(value: unknown, reservation: string): AgentServiceList {
  const invalid = () => new ApiError('UNKNOWN', 'Unverified agent service list');
  if (!value || typeof value !== 'object') throw invalid();
  const list = value as Record<string, unknown>;
  if (list.reservation_id !== reservation || !Array.isArray(list.items) ||
      !Number.isInteger(list.preview_limit) || Number(list.preview_limit) < 1 || Number(list.preview_limit) > 500 ||
      typeof list.preview_truncated !== 'boolean' || list.items.length > Number(list.preview_limit)) throw invalid();
  const ids = new Set<string>();
  const items = list.items.map(value => {
    if (!value || typeof value !== 'object') throw invalid();
    const x = value as Record<string, unknown>;
    if (typeof x.id !== 'string' || x.reservation_id !== reservation ||
        !AGENT_SERVICES.includes(x.service_code as AgentServiceCode) ||
        !['OPEN', 'IN_PROGRESS', 'DONE', 'CANCELLED'].includes(String(x.status)) ||
        !(x.service_date === null || (typeof x.service_date === 'string' && validServiceDate(x.service_date))) ||
        !(x.service_time === null || (typeof x.service_time === 'string' && /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(x.service_time))) ||
        !(x.description === null || (typeof x.description === 'string' && x.description.length <= 2000)) || ids.has(x.id)) throw invalid();
    safeRouteId(x.id); ids.add(x.id);
    return { id: x.id, reservation_id: reservation, service_code: x.service_code, status: x.status,
      service_date: x.service_date, service_time: x.service_time, description: x.description } as AgentServiceRecord;
  });
  return { reservation_id: reservation, items, preview_limit: Number(list.preview_limit), preview_truncated: list.preview_truncated };
}
