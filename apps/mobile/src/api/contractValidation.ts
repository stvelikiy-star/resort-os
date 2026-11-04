import { ApiError } from './types';
import type { Dashboard, Grid, ReceptionList, Conversation, ConversationDetail, BookingPreview, KitchenOrder, DiningFloor, AssistantCapabilities, AssistantAnswer, Hold } from './liveModules';
import type { AuthUser } from './types';
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

/** `{items: [...]}` envelope; a bare array is accepted only where the server contract allows it. */
export function itemsEnvelope(v:unknown,k:string,allowBareArray=false):unknown[]{
  if(allowBareArray&&Array.isArray(v))return v;
  return arr(obj(v,k).items,k+'.items');
}
/** /auth/login and /auth/me: the identity and permissions drive every role gate in the app. */
export function authUserResponse(v:unknown):AuthUser {
  const x=obj(v,'auth');
  for(const k of ['id','username','display_name','role','property_code'])str(x[k],'auth.'+k);
  arr(x.module_permissions,'auth.module_permissions').forEach((p,i)=>str(p,'auth.module_permissions'+i));
  return v as AuthUser;
}
export function kitchenOrdersResponse(v:unknown):KitchenOrder[] {
  const items=itemsEnvelope(v,'kitchen');
  items.forEach((r,i)=>{const o=obj(r,'kitchen.order'+i);str(o.id,'kitchen.id');str(o.order_number,'kitchen.order_number');str(o.status,'kitchen.status');if(!Array.isArray(o.items))invalid('kitchen.items');});
  return items as KitchenOrder[];
}
export function diningFloorResponse(v:unknown):DiningFloor {
  const x=obj(v,'dining');
  arr(x.tables,'dining.tables').forEach((t,i)=>{const o=obj(t,'dining.table'+i);str(o.id,'dining.table.id');str(o.code,'dining.table.code');});
  arr(x.orders,'dining.orders').forEach((t,i)=>{const o=obj(t,'dining.order'+i);str(o.id,'dining.order.id');str(o.order_number,'dining.order.number');str(o.status,'dining.order.status');});
  return v as DiningFloor;
}
export function assistantCapabilitiesResponse(v:unknown):AssistantCapabilities {
  const x=obj(v,'assistant.capabilities');
  for(const k of ['configured','read_only','can_mutate','live_read_only'])bool(x[k],'assistant.'+k);
  str(x.role,'assistant.role');str(x.property_code,'assistant.property_code');
  return v as AssistantCapabilities;
}
export function assistantAnswerResponse(v:unknown):AssistantAnswer {
  const x=obj(v,'assistant.answer');str(x.answer,'assistant.answer');
  if(x.read_only!==true)invalid('assistant.read_only');
  return v as AssistantAnswer;
}
/** Matches the actual pms_holds.py quoted SQL projection: camelCase list keys.
 * This is a SOURCE-only adapter; the mobile HOLD feature gate remains CLOSED.
 */
const uuid=(v:unknown,k:string):string=>{
  const value=str(v,k);
  return /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(value)?value:invalid(k);
};
const dateOnly=(v:unknown,k:string):string=>{
  const value=str(v,k);
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value)) invalid(k);
  const candidate=new Date(value+'T12:00:00Z');
  return !Number.isNaN(candidate.getTime())&&candidate.toISOString().slice(0,10)===value?value:invalid(k);
};
const timestamp=(v:unknown,k:string):string=>{
  const value=str(v,k);
  // Server returns Python datetime.isoformat() with explicit timezone offset.
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value)&&
    !Number.isNaN(Date.parse(value))?value:invalid(k);
};
export function holdListResponse(v:unknown):Hold[] {
  const rows=arr(obj(v,'hold.list').holds,'hold.list.holds');
  return rows.map((row,i)=>{
    const h=obj(row,'hold.list.'+i);
    const id=uuid(h.id,'hold.id');
    const roomId=uuid(h.roomId,'hold.roomId');
    const checkIn=dateOnly(h.checkIn,'hold.checkIn');
    const checkOut=dateOnly(h.checkOut,'hold.checkOut');
    if(checkOut<=checkIn) invalid('hold.dates');
    const guestName=str(h.guestName,'hold.guestName');
    const expiresAt=timestamp(h.expiresAt,'hold.expiresAt');
    return {id,roomId,checkIn,checkOut,guestName,expiresAt};
  });
}
export interface HoldCreatedAck {
  id:string; status:'HELD'; expires_at:string; duration_minutes:60;
}
export function holdCreateResponse(v:unknown):HoldCreatedAck {
  const result=obj(v,'hold.create');
  const id=uuid(result.id,'hold.create.id');
  if(result.status!=='HELD'||result.duration_minutes!==60) invalid('hold.create.ack');
  const expires_at=timestamp(result.expires_at,'hold.create.expires_at');
  return {id,status:'HELD',expires_at,duration_minutes:60};
}
export function holdReleaseResponse(v:unknown,expectedId:string):{id:string;status:'RELEASED'} {
  const result=obj(v,'hold.release');
  const id=uuid(result.id,'hold.release.id');
  if(id!==expectedId||result.status!=='RELEASED') invalid('hold.release.ack');
  return {id,status:'RELEASED'};
}

/** Detail payloads whose fields are rendered defensively: only the envelope shape is enforced. */
export function objectResponse(v:unknown,k:string):Record<string,unknown>{return obj(v,k);}

/**
 * Mutation acknowledgments must echo the record the app addressed (and, where the
 * server returns it, the resulting state). A mismatch is a contract violation, and
 * because the write may already be committed it surfaces as UNKNOWN (fail closed).
 */
function ack(v:unknown,k:string,idKey:string,id:string,state?:{key:string;value:string}):Record<string,unknown>{
  const x=obj(v,k);
  if(str(x[idKey],k+'.'+idKey)!==id)invalid(k+'.'+idKey+' mismatch');
  if(state&&x[state.key]!==state.value)invalid(k+'.'+state.key);
  return x;
}
export const stayAck=(v:unknown,reservationId:string,status:'CHECKED_IN'|'CHECKED_OUT')=>ack(v,'stay','reservation_id',reservationId,{key:'status',value:status});
export const kitchenStatusAck=(v:unknown,orderId:string,status:string)=>ack(v,'kitchen.status','id',orderId,{key:'status',value:status});
export const conversationStatusAck=(v:unknown,id:string,status:string)=>ack(v,'conversation.status','id',id,{key:'status',value:status});
export const conversationClaimAck=(v:unknown,id:string)=>ack(v,'conversation.claim','id',id);
export const noteAck=(v:unknown,id:string)=>{const x=ack(v,'note','conversation_id',id);str(x.id,'note.id');return x;};
export function waiterClaimAck(v:unknown,orderId:string,waiterId:string){
  const x=ack(v,'waiter.claim','id',orderId);
  if(x.waiter_id!==waiterId)invalid('waiter.claim.waiter_id');
  return x;
}
