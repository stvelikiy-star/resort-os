import { ApiError } from './types';
import type { FinanceSummary, Dashboard, Grid, ReceptionList, Conversation, ConversationDetail, BookingPreview, KitchenOrder, DiningFloor, DiningProductionSnapshots, DiningStays, DiningStayEntitlements, MealPlanDraft, MealPlanAck, AssistantCapabilities, AssistantAnswer, Hold } from './liveModules';
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
/** Only render confirmed finance aggregates, never a guessed payment or profit. */
export function financeSummaryResponse(v:unknown):FinanceSummary {
  const x=obj(v,'finance.summary'),range=obj(x.range,'finance.range');
  str(range.from,'finance.from');str(range.to,'finance.to');str(range.currency,'finance.currency');
  const period=obj(x.period_payments,'finance.period');
  const receivables=obj(x.receivables_snapshot,'finance.receivables');
  const active=obj(x.active_reservations_snapshot,'finance.active');
  for(const [value,key] of [
    [period.received_kgs,'received_kgs'],[period.pending_created_kgs,'pending_created_kgs'],
    [period.received_count,'received_count'],[receivables.outstanding_kgs,'outstanding_kgs'],
    [receivables.debtor_count,'debtor_count'],[active.reservation_count,'reservation_count'],
    [active.outstanding_kgs,'active.outstanding_kgs'],
  ] as const) {
    const n=num(value,'finance.'+key);
    if(!Number.isSafeInteger(n)||n<0) invalid('finance.'+key);
  }
  // RC409 exposes deeper owner finance; never render partial or malformed
  // extended rows as authoritative money. Older contracts may omit the set.
  const nonnegative = (value: unknown, path: string) => {
    const n = num(value, path);
    if (!Number.isSafeInteger(n) || n < 0) invalid(path);
  };
  for (const field of ['pending_created_count', 'failed_count', 'cancelled_count']) {
    if (period[field] !== undefined) nonnegative(period[field], 'finance.period.' + field);
  }
  for (const field of ['checked_out_count','checked_out_kgs','in_house_count','in_house_kgs',
    'pre_arrival_count','pre_arrival_kgs']) {
    if (receivables[field] !== undefined) nonnegative(receivables[field], 'finance.receivables.' + field);
  }
  for (const field of ['booked_total_kgs','received_kgs']) {
    if (active[field] !== undefined) nonnegative(active[field], 'finance.active.' + field);
  }
  for (const key of ['received_by_method','received_by_day']) {
    if (x[key] !== undefined) arr(x[key], 'finance.' + key).forEach((entry,i) => {
      const row = obj(entry,'finance.'+key+i);
      str(row[key === 'received_by_method' ? 'method' : 'local_date'], 'finance.'+key+'.key');
      nonnegative(row.amount_kgs,'finance.'+key+'.amount');
      nonnegative(row.payment_count,'finance.'+key+'.count');
    });
  }
  if (x.awaiting_prepayment_snapshot !== undefined) {
    const row = obj(x.awaiting_prepayment_snapshot,'finance.prepayment');
    for (const k of ['request_count','required_kgs','received_kgs','remaining_kgs'])
      nonnegative(row[k],'finance.prepayment.'+k);
  }
  if (x.refunded_snapshot_all_time !== undefined) {
    const row = obj(x.refunded_snapshot_all_time,'finance.refunded');
    nonnegative(row.amount_kgs,'finance.refunded.amount');nonnegative(row.payment_count,'finance.refunded.count');
  }
  if (x.finance_exceptions !== undefined) {
    const row = obj(obj(x.finance_exceptions,'finance.exceptions').snapshot,'finance.exceptions.snapshot');
    for (const k of ['overpaid_count','overpaid_kgs','cancelled_with_received_count','cancelled_with_received_kgs'])
      nonnegative(row[k],'finance.exceptions.'+k);
  }
  if (x.debtors !== undefined) arr(x.debtors,'finance.debtors').forEach((v,i) => {
    const row=obj(v,'finance.debtor.'+i);
    str(row.reservation_id,'finance.debtor.id');str(row.booking_number,'finance.debtor.booking');
    str(row.status,'finance.debtor.status');nonnegative(row.remaining_kgs,'finance.debtor.remaining');
  });
  if (x.recent_payments !== undefined) arr(x.recent_payments,'finance.recent').forEach((v,i) => {
    const row=obj(v,'finance.recent.'+i);
    str(row.id,'finance.recent.id');str(row.method,'finance.recent.method');
    str(row.status,'finance.recent.status');nonnegative(row.amount_kgs,'finance.recent.amount');
  });
  return v as FinanceSummary;
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
/** Explicit included-meal production totals returned to OWNER/MANAGER/RECEPTION/COOK.
 * These must NEVER be added directly to paid à-la-carte dish quantities. */
export function diningStaysResponse(v: unknown): DiningStays {
  const x = obj(v,'dining.stays'); str(x.local_date,'dining.stays.date');
  arr(x.items,'dining.stays.items').forEach((value,i)=>{
    const row=obj(value,'dining.stays.'+i);
    for(const k of ['stay_id','reservation_id','booking_number','check_in','check_out','guest_name'])
      str(row[k],'dining.stays.'+k);
    for(const k of ['adults','children','entitlement_count']) {
      const n=num(row[k],'dining.stays.'+k);
      if(!Number.isSafeInteger(n)||n<0) invalid('dining.stays.'+k);
    }
  });
  return v as DiningStays;
}
export function diningStayEntitlementsResponse(v: unknown, stayId: string): DiningStayEntitlements {
  const x = obj(v,'dining.entitlements');
  const stay=obj(x.stay,'dining.stay');
  if(str(stay.id,'dining.stay.id')!==stayId) invalid('dining.stay mismatch');
  arr(x.items,'dining.entitlements.items').forEach((value,i)=>{
    const row=obj(value,'dining.entitlement.'+i);
    str(row.id,'dining.entitlement.id');
    if(str(row.stay_id,'dining.entitlement.stay_id')!==stayId) invalid('dining.entitlement.stay mismatch');
    str(row.service_date,'dining.entitlement.date');
    const meal=str(row.meal_type,'dining.entitlement.meal');
    if(!['BREAKFAST','LUNCH','DINNER'].includes(meal)) invalid('dining.entitlement.meal');
    if(!['ACTIVE','CANCELLED'].includes(str(row.status,'dining.entitlement.status'))) invalid('dining.entitlement.status');
    for(const k of ['adult_portions','child_portions']) {
      const n=num(row[k],'dining.entitlement.'+k);
      if(!Number.isSafeInteger(n)||n<0) invalid('dining.entitlement.'+k);
    }
  });
  return v as DiningStayEntitlements;
}
/** Response echo and post-write readback are mandatory for meal-plan mutations. */
export function diningMealPlanAck(v:unknown, stayId:string, draft:MealPlanDraft):MealPlanAck {
  const x=obj(v,'dining.meal-plan.ack');
  if(str(x.stay_id,'dining.meal-plan.stay_id')!==stayId) invalid('dining.meal-plan.stay mismatch');
  if(str(x.from_date,'dining.meal-plan.from')!==draft.from_date ||
      str(x.through_date,'dining.meal-plan.through')!==draft.through_date) invalid('dining.meal-plan.dates mismatch');
  const count=num(x.updated_items,'dining.meal-plan.updated_items');
  if(!Number.isSafeInteger(count)||count<1) invalid('dining.meal-plan.updated_items');
  if(num(x.adult_portions,'dining.meal-plan.adults')!==draft.adult_portions ||
     num(x.child_portions,'dining.meal-plan.children')!==draft.child_portions)
    invalid('dining.meal-plan.portions mismatch');
  const meals=arr(x.meals,'dining.meal-plan.meals');
  if(meals.length!==draft.meals.length||meals.some(m=>!draft.meals.includes(m as 'BREAKFAST'|'LUNCH'|'DINNER')))
    invalid('dining.meal-plan.meals mismatch');
  return v as MealPlanAck;
}

export function diningProductionSnapshotsResponse(v: unknown): DiningProductionSnapshots {
  const x = obj(v, 'dining.production-snapshots');
  str(x.from_date, 'production.from_date'); str(x.through_date, 'production.through_date');
  arr(x.days, 'production.days').forEach((value, dayIndex) => {
    const day = obj(value, 'production.day.' + dayIndex);
    str(day.service_date, 'production.day.date');
    const seen = new Set<string>();
    arr(day.meals, 'production.day.meals').forEach((value, mealIndex) => {
      const row = obj(value, 'production.meal.' + mealIndex);
      const type = str(row.meal_type, 'production.meal.type');
      if (!['BREAKFAST', 'LUNCH', 'DINNER'].includes(type) || seen.has(type)) invalid('production.meal.type');
      seen.add(type);
      str(row.service_date, 'production.meal.date');
      if (row.service_date !== day.service_date) invalid('production.meal.date mismatch');
      const state = str(row.state, 'production.state');
      if (!['OPEN','FROZEN'].includes(state)) invalid('production.state');
      const cutoff = str(row.cutoff_status, 'production.cutoff');
      if (!['UNCONFIGURED','BEFORE_CUTOFF','CUTOFF_REACHED'].includes(cutoff)) invalid('production.cutoff');
      for (const k of ['current_adult_portions','current_child_portions','current_total_portions','current_entitlement_count']) {
        const amount = num(row[k], 'production.' + k);
        if (!Number.isSafeInteger(amount) || amount < 0) invalid('production.' + k);
      }
      if (row.current_total_portions !== Number(row.current_adult_portions) + Number(row.current_child_portions))
        invalid('production.total mismatch');
      if (row.current_checked_in_total_portions !== undefined || row.current_expected_arrival_total_portions !== undefined) {
        for (const prefix of ['current_checked_in','current_expected_arrival']) {
          for (const suffix of ['adult_portions','child_portions','total_portions','stay_count']) {
            const key = prefix+'_'+suffix;
            const amount=num(row[key],'production.'+key);
            if (!Number.isSafeInteger(amount)||amount<0) invalid('production.'+key);
          }
          if (Number(row[prefix+'_total_portions']) !==
              Number(row[prefix+'_adult_portions']) + Number(row[prefix+'_child_portions']))
            invalid('production.'+prefix+'.total mismatch');
        }
        if (Number(row.current_checked_in_total_portions) + Number(row.current_expected_arrival_total_portions)
          !== Number(row.current_total_portions)) invalid('production.stage totals mismatch');
      }
      if (row.changed_since_snapshot !== undefined && typeof row.changed_since_snapshot !== 'boolean')
        invalid('production.changed_since_snapshot');
      if (state === 'FROZEN') {
        if (typeof row.frozen_total_portions !== 'number' || !Number.isSafeInteger(row.frozen_total_portions) ||
            row.frozen_total_portions < 0) invalid('production.frozen_total_portions');
        if (typeof row.delta_total_portions !== 'number' || !Number.isSafeInteger(row.delta_total_portions) ||
            Number(row.delta_total_portions) !== Number(row.current_total_portions) - Number(row.frozen_total_portions))
          invalid('production.delta_total_portions');
      }
    });
    if (seen.size !== 3) invalid('production.three_meals');
    // Checked-in and pending-arrival STAY counts are distinct bookings, not
    // number of persons. Both must come from the hotel server or neither.
    if (day.checked_in_stays_with_meals !== undefined || day.expected_arrival_stays_with_meals !== undefined) {
      for (const key of ['checked_in_stays_with_meals','expected_arrival_stays_with_meals']) {
        const n=num(day[key],'production.day.'+key);
        if (!Number.isSafeInteger(n) || n < 0) invalid('production.day.'+key);
      }
    }
  });
  return v as DiningProductionSnapshots;
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