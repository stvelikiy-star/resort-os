import { ApiError } from './types';
import type { Dashboard, Grid, ReceptionList, Conversation, ConversationDetail, BookingPreview } from './liveModules';
const invalid=(where:string):never=>{ throw new ApiError('UNKNOWN','Hotel response contract mismatch: '+where); };
const obj=(v:unknown,k:string):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:invalid(k);
const str=(v:unknown,k:string)=>typeof v==='string'&&v.trim()?v:invalid(k);
const num=(v:unknown,k:string)=>typeof v==='number'&&Number.isFinite(v)?v:invalid(k);
const bool=(v:unknown,k:string)=>typeof v==='boolean'?v:invalid(k);
const arr=(v:unknown,k:string):unknown[]=>Array.isArray(v)?v:invalid(k);
export function receptionResponse(v:unknown):ReceptionList {
  const x=obj(v,'reception');str(x.local_date,'reception.date');
  arr(x.items,'reception.items').forEach((r,i)=>{const a=obj(r,'reception.item'+i);str(a.id,'reception.id');str(a.bookingNumber,'reception.bookingNumber');str(a.status,'reception.status');str(a.checkIn,'reception.checkIn');str(a.checkOut,'reception.checkOut');num(a.remainingKgs,'reception.remainingKgs');});
  return v as ReceptionList;
}
export function dashboardResponse(v:unknown):Dashboard {
  const x=obj(v,'dashboard');const prop=obj(x.property,'dashboard.property');str(prop.name,'dashboard.name');str(prop.local_date,'dashboard.date');
  const rooms=obj(x.rooms,'dashboard.rooms');num(rooms.total,'dashboard.rooms.total');num(rooms.dirty,'dashboard.rooms.dirty');
  const stays=obj(x.stays,'dashboard.stays');for(const k of ['occupancy_percent','occupied_rooms','arrivals_today','departures_today'])num(stays[k],'dashboard.stays.'+k);
  const finance=obj(x.finance,'dashboard.finance');for(const k of ['confirmed_payments_today_kgs','active_reservations_remaining_kgs'])num(finance[k],'dashboard.finance.'+k);
  num(obj(x.communications,'dashboard.communications').needs_reply,'dashboard.needs_reply');
  num(obj(x.tasks,'dashboard.tasks').urgent_active,'dashboard.urgent');
  const today=obj(x.today,'dashboard.today');arr(today.arrivals,'dashboard.arrivals');arr(today.departures,'dashboard.departures');
  arr(x.attention_tasks,'dashboard.attention_tasks').forEach((t,i)=>{const a=obj(t,'attention_task'+i);str(a.id,'attention_task.id');str(a.title,'attention_task.title');});
  return v as Dashboard;
}
export function gridResponse(v:unknown):Grid {
  const x=obj(v,'pms.grid');str(x.property,'pms.property');
  arr(x.rooms,'pms.rooms').forEach((r,i)=>{const a=obj(r,'pms.room'+i);str(a.id,'pms.room.id');str(a.code,'pms.room.code');str(a.operational_state,'pms.room.state');
    arr(a.blocks,'pms.blocks').forEach((b,j)=>{const o=obj(b,'pms.block'+j);for(const k of ['id','type','start','end'])str(o[k],'pms.block.'+k);});
  });
  return v as Grid;
}
export function inboxListResponse(v:unknown):Conversation[] {
  const a=arr(obj(v,'inbox').items,'inbox.items');a.forEach((c,i)=>{const o=obj(c,'inbox.row'+i);str(o.id,'inbox.id');str(o.channel_kind,'inbox.channel_kind');str(o.status,'inbox.status');bool(o.needs_reply,'inbox.needs_reply');});
  return a as Conversation[];
}
export function conversationResponse(v:unknown):ConversationDetail {
  const x=obj(v,'conversation'),c=obj(x.conversation,'conversation.summary');
  str(c.id,'conversation.id');str(c.channel_kind,'conversation.kind');
  arr(x.messages,'conversation.messages').forEach((m,i)=>{const a=obj(m,'message'+i);str(a.id,'message.id');str(a.direction,'message.direction');str(a.created_at,'message.date');});
  return v as ConversationDetail;
}
export function bookingPreviewResponse(v:unknown):BookingPreview {
  const x=obj(v,'preview'),r=obj(x.room,'preview.room');str(r.id,'preview.room.id');str(r.code,'preview.room.code');
  str(x.check_in,'preview.start');str(x.check_out,'preview.end');num(x.nights,'preview.nights');bool(x.can_commit,'preview.can_commit');
  arr(x.conflicts,'preview.conflicts');const p=obj(x.pricing,'preview.pricing');str(p.source,'preview.pricing.source');bool(p.sellable,'preview.pricing.sellable');if(p.total_kgs!==null)num(p.total_kgs,'preview.total');
  return v as BookingPreview;
}
export function bookingCommitResponse(v:unknown):{reservation_id:string;booking_number:string;total_kgs:number;price_adjusted_at_commit:boolean} {
  const x=obj(v,'commit');str(x.reservation_id,'commit.id');str(x.booking_number,'commit.number');num(x.total_kgs,'commit.total');bool(x.price_adjusted_at_commit,'commit.price_changed');return v as {reservation_id:string;booking_number:string;total_kgs:number;price_adjusted_at_commit:boolean};
}
