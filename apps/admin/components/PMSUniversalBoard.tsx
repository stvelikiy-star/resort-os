"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ReservationScheduleBuilder, { ScheduleIntent } from "./ReservationScheduleBuilder";
import RoomDetailModal from "./RoomDetailModal";

type Block = {
  id: string;
  type: "RESERVATION" | "MAINTENANCE" | "MANUAL";
  start: string;
  end: string;
  reason: string | null;
  reservation_id: string | null;
  booking_number: string | null;
  reservation_status: string | null;
  guest_name: string | null;
  guest_phone: string | null;
};

type Room = {
  id: string;
  code: string;
  name: string;
  room_type_code: string;
  room_type_name: string;
  building_or_zone: string | null;
  floor: string | null;
  operational_state: "UNKNOWN" | "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK";
  blocks: Block[];
};

type GridResponse = { property: string; start: string; end: string; rooms: Room[] };

type ReceptionItem = {
  id: string;
  bookingNumber: string;
  status: string;
  checkIn: string;
  checkOut: string;
  totalKgs: number;
  paidKgs: number;
  remainingKgs: number;
  firstName?: string | null;
  phone?: string | null;
  room_code?: string | null;
  room_type_name?: string | null;
  room_state?: string | null;
  schedule_segments: number;
  has_room_move: boolean;
};

type FinanceState = "loading" | "ready" | "partial" | "error";
type InteractionMode = "WHOLE" | "SEGMENT";
type Density = "COMPACT" | "COMFORTABLE";
type GroupMode = "NONE" | "BUILDING" | "FLOOR" | "CATEGORY";
type DailyMode = "ALL" | "ARRIVALS" | "DEPARTURES" | "IN_HOUSE" | "FREE" | "DEBT" | "ATTENTION";
type FinanceMode = "ALL" | "PAID" | "PARTIAL" | "UNPAID" | "DEBT";
type OccupancyMode = "ALL" | "FREE" | "OCCUPIED" | "BLOCKED";
type BlockMode = "ALL" | "RESERVATION" | "MAINTENANCE" | "MANUAL";

type Filters = {
  search: string;
  roomType: string;
  building: string;
  floor: string;
  state: string;
  reservationStatus: string;
  finance: FinanceMode;
  occupancy: OccupancyMode;
  blockType: BlockMode;
  daily: DailyMode;
};

type BuilderOpen = { reservationId: string; intent: ScheduleIntent };
type DragPayload = { mode: InteractionMode; reservationId: string; blockId: string; sourceRoomId: string; start: string; end: string };
type RealtimeMessage = { type: "pms.grid.snapshot" | "heartbeat"; data?: GridResponse };

type RenderRow = { kind: "group"; key: string; label: string; count: number } | { kind: "room"; key: string; room: Room };

const DEFAULT_FILTERS: Filters = { search: "", roomType: "ALL", building: "ALL", floor: "ALL", state: "ALL", reservationStatus: "ALL", finance: "ALL", occupancy: "ALL", blockType: "ALL", daily: "ALL" };
const ROOM_STATE: Record<Room["operational_state"], string> = { UNKNOWN: "Без статуса", CLEAN: "Готов", DIRTY: "Уборка", IN_INSPECTION: "Проверка", TECH_BLOCK: "Ремонт" };
const QUICK: Array<{ key: DailyMode; label: string }> = [
  { key: "ALL", label: "Все" }, { key: "ARRIVALS", label: "Заезды" }, { key: "DEPARTURES", label: "Выезды" }, { key: "IN_HOUSE", label: "Проживают" }, { key: "FREE", label: "Свободные" }, { key: "DEBT", label: "С долгом" }, { key: "ATTENTION", label: "Внимание" },
];

function localDate(value = new Date()) { const y=value.getFullYear(); const m=String(value.getMonth()+1).padStart(2,"0"); const d=String(value.getDate()).padStart(2,"0"); return `${y}-${m}-${d}`; }
function addDays(value:Date, amount:number){ const next=new Date(value.getFullYear(),value.getMonth(),value.getDate()); next.setDate(next.getDate()+amount); return next; }
function shiftDate(value:string, amount:number){ const [y,m,d]=value.split("-").map(Number); return new Date(Date.UTC(y,m-1,d+amount)).toISOString().slice(0,10); }
function ordinal(value:string){ const [y,m,d]=value.split("-").map(Number); return Math.floor(Date.UTC(y,m-1,d)/86400000); }
function daysBetween(a:string,b:string){ return ordinal(b)-ordinal(a); }
function range(start:Date,count:number){ return Array.from({length:count},(_,i)=>addDays(start,i)); }
function money(value:number){ return new Intl.NumberFormat("ru-RU").format(value); }
function covers(block:Block,day:string){ return block.start<=day&&day<block.end; }
function websocketBase(){ const configured=process.env.NEXT_PUBLIC_CORE_WS_URL?.replace(/\/$/,""); if(configured)return configured; if(typeof window==="undefined")return ""; const protocol=window.location.protocol==="https:"?"wss:":"ws:"; const host=window.location.hostname; const port=window.location.port==="3001"?"8000":window.location.port; return `${protocol}//${host}${port?`:${port}`:""}`; }
function paymentClass(item?:ReceptionItem){ if(!item)return "unknown"; if(item.remainingKgs<=0)return "paid"; if(item.paidKgs>0)return "partial"; return "unpaid"; }
function groupValue(room:Room,mode:GroupMode){ if(mode==="BUILDING")return room.building_or_zone||"Без корпуса"; if(mode==="FLOOR")return room.floor?`${room.floor} этаж`:"Этаж не указан"; if(mode==="CATEGORY")return room.room_type_name; return ""; }

export default function PMSUniversalBoard(){
  const [start,setStart]=useState(()=>{const n=new Date();return new Date(n.getFullYear(),n.getMonth(),n.getDate())});
  const [windowDays,setWindowDays]=useState(14); const [density,setDensity]=useState<Density>("COMFORTABLE"); const [groupMode,setGroupMode]=useState<GroupMode>("BUILDING");
  const [interaction,setInteraction]=useState<InteractionMode>("SEGMENT"); const [cutMode,setCutMode]=useState(false); const [filtersOpen,setFiltersOpen]=useState(true); const [filters,setFilters]=useState<Filters>(DEFAULT_FILTERS);
  const [data,setData]=useState<GridResponse|null>(null); const [finance,setFinance]=useState<ReceptionItem[]>([]); const [financeState,setFinanceState]=useState<FinanceState>("loading"); const [loading,setLoading]=useState(true); const [error,setError]=useState<string|null>(null); const [notice,setNotice]=useState<string|null>(null); const [realtime,setRealtime]=useState<"connecting"|"live"|"offline">("connecting");
  const [builder,setBuilder]=useState<BuilderOpen|null>(null); const [roomId,setRoomId]=useState<string|null>(null); const [dragging,setDragging]=useState<DragPayload|null>(null); const [targetRoomId,setTargetRoomId]=useState<string|null>(null); const [targetDate,setTargetDate]=useState<string|null>(null);
  const days=useMemo(()=>range(start,windowDays),[start,windowDays]); const end=useMemo(()=>addDays(start,windowDays),[start,windowDays]); const startIso=localDate(start); const endIso=localDate(end); const today=localDate();
  const dayWidth=density==="COMPACT"?58:74; const roomWidth=density==="COMPACT"?190:220; const stateWidth=density==="COMPACT"?96:116; const fixedWidth=roomWidth+stateWidth; const template=`${roomWidth}px ${stateWidth}px repeat(${windowDays}, ${dayWidth}px)`;

  const load=useCallback(async()=>{ setLoading(true);setError(null); try{ const params=new URLSearchParams({start:localDate(start),end:localDate(end)}); const [gr,fr]=await Promise.all([fetch(`/core/api/v1/pms/grid?${params}`,{cache:"no-store"}),fetch("/core/api/v1/admin/reception/reservations?limit=500",{cache:"no-store"})]); const gb=await gr.json().catch(()=>({})); if(!gr.ok)throw new Error(typeof gb.detail==="string"?gb.detail:`Grid HTTP ${gr.status}`); setData(gb as GridResponse); const fb=await fr.json().catch(()=>({})); if(fr.ok&&Array.isArray(fb.items)){const items=fb.items as ReceptionItem[];setFinance(items);setFinanceState(items.length>=500?"partial":"ready")}else{setFinance([]);setFinanceState("error")}}catch(e){setData(null);setFinance([]);setFinanceState("error");setError(e instanceof Error?e.message:"Не удалось загрузить Universal Board")}finally{setLoading(false)} },[start,end]);
  useEffect(()=>{void load()},[load]);
  useEffect(()=>{const t=window.setInterval(()=>void load(),60000);return()=>window.clearInterval(t)},[load]);
  useEffect(()=>{const base=websocketBase();if(!base)return;let socket:WebSocket|null=null;let stopped=false;let timer:number|undefined;const params=new URLSearchParams({start:startIso,end:endIso});const connect=()=>{if(stopped)return;setRealtime("connecting");socket=new WebSocket(`${base}/ws/pms/grid?${params}`);socket.onopen=()=>setRealtime("live");socket.onmessage=(event)=>{try{const msg=JSON.parse(event.data) as RealtimeMessage;if(msg.type==="pms.grid.snapshot"&&msg.data){setData(msg.data);setRealtime("live")}}catch{}};socket.onerror=()=>socket?.close();socket.onclose=()=>{if(stopped)return;setRealtime("offline");timer=window.setTimeout(connect,3000)}};connect();return()=>{stopped=true;if(timer)window.clearTimeout(timer);socket?.close()}},[startIso,endIso]);

  const financeById=useMemo(()=>new Map(finance.map(item=>[item.id,item])),[finance]);
  const reservationBounds=useMemo(()=>{const map=new Map<string,{start:string;end:string}>();data?.rooms.forEach(room=>room.blocks.forEach(block=>{if(!block.reservation_id||block.type!=="RESERVATION")return;const x=map.get(block.reservation_id);if(!x)map.set(block.reservation_id,{start:block.start,end:block.end});else{if(block.start<x.start)x.start=block.start;if(block.end>x.end)x.end=block.end}}));return map},[data]);
  const roomTypes=useMemo(()=>Array.from(new Map((data?.rooms||[]).map(room=>[room.room_type_code,room.room_type_name])).entries()).sort((a,b)=>a[1].localeCompare(b[1],"ru")),[data]);
  const buildings=useMemo(()=>Array.from(new Set((data?.rooms||[]).map(room=>room.building_or_zone).filter((x):x is string=>Boolean(x)))).sort(),[data]);
  const floors=useMemo(()=>Array.from(new Set((data?.rooms||[]).map(room=>room.floor).filter((x):x is string=>Boolean(x)))).sort(),[data]);

  const roomHasToday=(room:Room)=>room.blocks.some(block=>covers(block,today));
  const roomReservations=(room:Room)=>room.blocks.filter(block=>block.type==="RESERVATION"&&block.reservation_id).map(block=>financeById.get(block.reservation_id!)).filter((item):item is ReceptionItem=>Boolean(item));
  const quickMatch=(room:Room)=>{const mode=filters.daily;if(mode==="ALL")return true;if(mode==="FREE")return room.operational_state!=="TECH_BLOCK"&&!roomHasToday(room);if(mode==="ATTENTION")return ["DIRTY","IN_INSPECTION","TECH_BLOCK"].includes(room.operational_state);if(mode==="DEBT")return financeState==="ready"&&roomReservations(room).some(item=>item.remainingKgs>0&&["GUARANTEED","CHECKED_IN"].includes(item.status));return room.blocks.some(block=>{if(block.type!=="RESERVATION"||!block.reservation_id)return false;const bounds=reservationBounds.get(block.reservation_id);if(!bounds)return false;if(mode==="ARRIVALS")return block.reservation_status==="GUARANTEED"&&bounds.start===today;if(mode==="DEPARTURES")return block.reservation_status==="CHECKED_IN"&&bounds.end===today;return mode==="IN_HOUSE"&&block.reservation_status==="CHECKED_IN"&&covers(block,today)})};
  const filterRoom=(room:Room)=>{const q=filters.search.trim().toLowerCase();const financeItems=roomReservations(room);const hay=[room.code,room.name,room.room_type_name,room.building_or_zone,room.floor,...room.blocks.flatMap(block=>[block.guest_name,block.guest_phone,block.booking_number,block.reason])].filter(Boolean).join(" ").toLowerCase();if(q&&!hay.includes(q))return false;if(filters.roomType!=="ALL"&&room.room_type_code!==filters.roomType)return false;if(filters.building!=="ALL"&&room.building_or_zone!==filters.building)return false;if(filters.floor!=="ALL"&&room.floor!==filters.floor)return false;if(filters.state!=="ALL"&&room.operational_state!==filters.state)return false;if(filters.reservationStatus!=="ALL"&&!room.blocks.some(block=>block.reservation_status===filters.reservationStatus))return false;if(filters.blockType!=="ALL"&&!room.blocks.some(block=>block.type===filters.blockType))return false;if(filters.occupancy==="FREE"&&roomHasToday(room))return false;if(filters.occupancy==="OCCUPIED"&&!room.blocks.some(block=>block.type==="RESERVATION"&&covers(block,today)))return false;if(filters.occupancy==="BLOCKED"&&!room.blocks.some(block=>block.type!=="RESERVATION"&&covers(block,today))&&room.operational_state!=="TECH_BLOCK")return false;if(filters.finance!=="ALL"){if(financeState!=="ready")return false;const ok=financeItems.some(item=>filters.finance==="PAID"?item.remainingKgs<=0:filters.finance==="PARTIAL"?item.paidKgs>0&&item.remainingKgs>0:filters.finance==="UNPAID"?item.paidKgs<=0&&item.remainingKgs>0:item.remainingKgs>0);if(!ok)return false}return quickMatch(room)};
  const filteredRooms=useMemo(()=>{const list=(data?.rooms||[]).filter(filterRoom);return list.sort((a,b)=>{const ga=groupValue(a,groupMode),gb=groupValue(b,groupMode);return ga.localeCompare(gb,"ru")||a.code.localeCompare(b.code,"ru",{numeric:true})})},[data,filters,financeState,financeById,reservationBounds,groupMode,today]);
  const rows=useMemo(()=>{const out:RenderRow[]=[];let last="";filteredRooms.forEach(room=>{const group=groupValue(room,groupMode);if(groupMode!=="NONE"&&group!==last){const count=filteredRooms.filter(item=>groupValue(item,groupMode)===group).length;out.push({kind:"group",key:`group-${group}`,label:group,count});last=group}out.push({kind:"room",key:room.id,room})});return out},[filteredRooms,groupMode]);

  const occupancy=useMemo(()=>days.map(day=>{const key=localDate(day);const rooms=data?.rooms||[];const unavailable=rooms.filter(room=>room.operational_state==="TECH_BLOCK"||room.blocks.some(block=>covers(block,key))).length;return rooms.length?Math.round(unavailable/rooms.length*100):0}),[days,data]);
  const unassigned=useMemo(()=>financeState==="ready"?finance.filter(item=>item.status==="GUARANTEED"&&!item.room_code):[],[finance,financeState]);

  function blockPlacement(block:Block){const visibleStart=block.start>startIso?block.start:startIso;const visibleEnd=block.end<endIso?block.end:endIso;if(visibleEnd<=visibleStart)return null;const startIndex=daysBetween(startIso,visibleStart);const span=Math.max(1,daysBetween(visibleStart,visibleEnd));return{column:`${3+startIndex} / span ${span}`,visibleStart,visibleEnd,span}};
  function dateFromRow(event:React.DragEvent<HTMLDivElement>){const rect=event.currentTarget.getBoundingClientRect();const x=event.clientX-rect.left-fixedWidth;const index=Math.floor(x/dayWidth);if(index<0||index>=windowDays)return null;return shiftDate(startIso,index)}
  function splitDateFromClick(event:React.MouseEvent<HTMLButtonElement>,block:Block,place:{visibleStart:string;visibleEnd:string;span:number}){if(place.span<=1)return null;const rect=event.currentTarget.getBoundingClientRect();const ratio=Math.max(0,Math.min(.999,(event.clientX-rect.left)/Math.max(1,rect.width)));const offset=Math.max(1,Math.min(place.span-1,Math.round(ratio*place.span)));const date=shiftDate(place.visibleStart,offset);return date>block.start&&date<block.end?date:null}
  function dragStart(event:React.DragEvent<HTMLButtonElement>,room:Room,block:Block){if(!block.reservation_id){event.preventDefault();return}if(!["GUARANTEED","CHECKED_IN"].includes(block.reservation_status||"")){event.preventDefault();setNotice("Завершённые/отменённые брони только для чтения.");return}if(interaction==="WHOLE"&&block.reservation_status==="CHECKED_IN"){event.preventDefault();setNotice("Проживающего гостя переносите в режиме «Кусок»: история прошлых ночей защищена.");return}const payload:DragPayload={mode:interaction,reservationId:block.reservation_id,blockId:block.id,sourceRoomId:room.id,start:block.start,end:block.end};setDragging(payload);setNotice(null);event.dataTransfer.effectAllowed="move";event.dataTransfer.setData("application/x-resort-segment",JSON.stringify(payload))}
  function drop(room:Room,event:React.DragEvent<HTMLDivElement>){event.preventDefault();const date=dateFromRow(event);let payload=dragging;try{const raw=event.dataTransfer.getData("application/x-resort-segment");if(raw)payload=JSON.parse(raw) as DragPayload}catch{}setDragging(null);setTargetRoomId(null);setTargetDate(null);if(!payload||!date)return;if(room.operational_state==="TECH_BLOCK"){setNotice(`№ ${room.code} находится в ремонте.`);return}const intent:ScheduleIntent=payload.mode==="WHOLE"?{kind:"MOVE_STAY",targetRoomId:room.id,targetStart:date}:{kind:"MOVE_SEGMENT",segmentBlockId:payload.blockId,sourceRoomId:payload.sourceRoomId,segmentStart:payload.start,segmentEnd:payload.end,targetRoomId:room.id};setBuilder({reservationId:payload.reservationId,intent})}
  function openBlock(event:React.MouseEvent<HTMLButtonElement>,room:Room,block:Block,place:{visibleStart:string;visibleEnd:string;span:number}){if(!block.reservation_id)return;if(cutMode){const date=splitDateFromClick(event,block,place);if(!date){setNotice("Для разреза нужен сегмент минимум на 2 ночи. Кликните ближе к нужной границе дня.");return}setBuilder({reservationId:block.reservation_id,intent:{kind:"SPLIT",segmentBlockId:block.id,sourceRoomId:room.id,segmentStart:block.start,segmentEnd:block.end,splitDate:date}});return}setBuilder({reservationId:block.reservation_id,intent:{kind:"OPEN",segmentBlockId:block.id,sourceRoomId:room.id,segmentStart:block.start,segmentEnd:block.end}})}
  function refresh(){void load()}

  return <section className={`v8-board density-${density.toLowerCase()} ${cutMode?"cut-mode":""}`}>
    <header className="v8-board-head"><div><p className="eyebrow">Universal Tape Chart · V8</p><h2>Шахматка без ограничений</h2><span>Вся бронь, отдельный кусок, ножницы, переселения и полный schedule preview в Resort Core.</span></div><div className="v8-live"><i className={realtime}/>{realtime==="live"?"Realtime":realtime==="connecting"?"Подключение":"HTTP fallback"}</div></header>

    <div className="v8-command">
      <label className="v8-search"><span>⌕</span><input value={filters.search} onChange={event=>setFilters(current=>({...current,search:event.target.value}))} placeholder="Гость, телефон, бронь, номер, категория, корпус…" /></label>
      <div className="v8-date-nav"><button onClick={()=>setStart(addDays(start,-7))}>← 7</button><button onClick={()=>setStart(new Date())}>Сегодня</button><button onClick={()=>setStart(addDays(start,7))}>7 →</button></div>
      <select value={windowDays} onChange={event=>setWindowDays(Number(event.target.value))}><option value={7}>7 дней</option><option value={14}>14 дней</option><option value={21}>21 день</option><option value={31}>31 день</option></select>
      <select value={groupMode} onChange={event=>setGroupMode(event.target.value as GroupMode)}><option value="NONE">Без групп</option><option value="BUILDING">По корпусам</option><option value="FLOOR">По этажам</option><option value="CATEGORY">По категориям</option></select>
      <div className="v8-mode"><button className={interaction==="WHOLE"?"active":""} onClick={()=>{setInteraction("WHOLE");setCutMode(false)}}>⇄ Вся бронь</button><button className={interaction==="SEGMENT"?"active":""} onClick={()=>setInteraction("SEGMENT")}>↪ Кусок</button><button className={cutMode?"active scissors":"scissors"} onClick={()=>setCutMode(value=>!value)}>✂ Ножницы</button></div>
      <div className="v8-density"><button className={density==="COMPACT"?"active":""} onClick={()=>setDensity("COMPACT")}>Плотно</button><button className={density==="COMFORTABLE"?"active":""} onClick={()=>setDensity("COMFORTABLE")}>Комфорт</button></div>
      <button className="v8-filter-toggle" onClick={()=>setFiltersOpen(value=>!value)}>Супер-фильтр {filtersOpen?"↑":"↓"}</button>
      <button className="v8-refresh" onClick={refresh}>↻</button>
    </div>

    <div className="v8-quick">{QUICK.map(item=><button key={item.key} className={filters.daily===item.key?"active":""} onClick={()=>setFilters(current=>({...current,daily:item.key}))}>{item.label}</button>)}</div>

    {filtersOpen&&<div className="v8-filters">
      <label><span>Категория</span><select value={filters.roomType} onChange={event=>setFilters(current=>({...current,roomType:event.target.value}))}><option value="ALL">Все</option>{roomTypes.map(([code,name])=><option key={code} value={code}>{name}</option>)}</select></label>
      <label><span>Корпус</span><select value={filters.building} onChange={event=>setFilters(current=>({...current,building:event.target.value}))}><option value="ALL">Все</option>{buildings.map(value=><option key={value}>{value}</option>)}</select></label>
      <label><span>Этаж</span><select value={filters.floor} onChange={event=>setFilters(current=>({...current,floor:event.target.value}))}><option value="ALL">Все</option>{floors.map(value=><option key={value}>{value}</option>)}</select></label>
      <label><span>Статус номера</span><select value={filters.state} onChange={event=>setFilters(current=>({...current,state:event.target.value}))}><option value="ALL">Любой</option><option value="CLEAN">Готов</option><option value="DIRTY">Уборка</option><option value="IN_INSPECTION">Проверка</option><option value="TECH_BLOCK">Ремонт</option><option value="UNKNOWN">Без статуса</option></select></label>
      <label><span>Статус брони</span><select value={filters.reservationStatus} onChange={event=>setFilters(current=>({...current,reservationStatus:event.target.value}))}><option value="ALL">Любой</option><option value="GUARANTEED">Ожидает</option><option value="CHECKED_IN">Проживает</option><option value="CHECKED_OUT">Выехал</option></select></label>
      <label><span>Оплата</span><select value={filters.finance} disabled={financeState!=="ready"} onChange={event=>setFilters(current=>({...current,finance:event.target.value as FinanceMode}))}><option value="ALL">Любая</option><option value="PAID">Оплачено</option><option value="PARTIAL">Частично</option><option value="UNPAID">Без оплаты</option><option value="DEBT">Есть остаток</option></select></label>
      <label><span>Занятость сегодня</span><select value={filters.occupancy} onChange={event=>setFilters(current=>({...current,occupancy:event.target.value as OccupancyMode}))}><option value="ALL">Любая</option><option value="FREE">Свободно</option><option value="OCCUPIED">Гость</option><option value="BLOCKED">Служебный блок</option></select></label>
      <label><span>Тип блока</span><select value={filters.blockType} onChange={event=>setFilters(current=>({...current,blockType:event.target.value as BlockMode}))}><option value="ALL">Все</option><option value="RESERVATION">Бронь</option><option value="MAINTENANCE">Ремонт</option><option value="MANUAL">Ручной блок</option></select></label>
      <button onClick={()=>setFilters(DEFAULT_FILTERS)}>Сбросить всё</button>
    </div>}

    <div className="v8-instruction"><strong>{cutMode?"✂ Ножницы активны":"Как двигать"}</strong><span>{cutMode?"Кликните внутри сегмента на нужной границе дня — откроется preview разреза. После commit каждый кусок становится отдельным draggable-сегментом.":interaction==="WHOLE"?"Тяните бронь в новый номер/дату — весь stay сдвигается и назначается на целевой номер после server preview.":"Тяните конкретный кусок вертикально в другой номер — его даты сохраняются. Для CHECKED_IN кусок, пересекающий сегодня, автоматически отделяется с сегодняшней даты."}</span></div>
    {notice&&<div className="v8-notice" onClick={()=>setNotice(null)}>{notice}<b>×</b></div>}
    {error&&<div className="v8-error">{error}</div>}
    {financeState!=="ready"&&<div className="v8-finance-warning">Финансовый read model {financeState==="partial"?"неполный (лимит 500)":"недоступен"}; debt-фильтры fail-closed.</div>}

    {unassigned.length>0&&<div className="v8-unassigned"><div><strong>Без номера</strong><span>Перетащите будущую бронь на свободную ячейку.</span></div>{unassigned.slice(0,20).map(item=><button key={item.id} draggable onDragStart={event=>{const payload:DragPayload={mode:"WHOLE",reservationId:item.id,blockId:"unassigned",sourceRoomId:"",start:item.checkIn,end:item.checkOut};setDragging(payload);event.dataTransfer.setData("application/x-resort-segment",JSON.stringify(payload))}}><strong>{item.firstName||item.bookingNumber}</strong><span>{item.checkIn} → {item.checkOut}</span></button>)}</div>}

    <div className="v8-board-shell">
      <div className="v8-scroll">
        <div className="v8-grid-head" style={{gridTemplateColumns:template}}><div className="v8-room-head">Номер <small>{filteredRooms.length}</small></div><div className="v8-state-head">Статус</div>{days.map((day,index)=>{const key=localDate(day);const weekend=day.getDay()===0||day.getDay()===6;return <div key={key} className={`v8-date-head ${weekend?"weekend":""} ${key===today?"today":""}`}><strong>{day.getDate()}</strong><span>{new Intl.DateTimeFormat("ru-RU",{weekday:"short"}).format(day)}</span><em>{occupancy[index]}%</em></div>})}</div>
        {loading&&!data?<div className="v8-loading">Загрузка шахматки…</div>:rows.map(row=>row.kind==="group"?<div key={row.key} className="v8-group-row" style={{gridTemplateColumns:template}}><div style={{gridColumn:"1 / -1"}}><strong>{row.label}</strong><span>{row.count} номеров</span></div></div>:<div key={row.key} className={`v8-room-row state-${row.room.operational_state.toLowerCase()} ${targetRoomId===row.room.id?"drop-target":""}`} style={{gridTemplateColumns:template}} onDragOver={event=>{if(!dragging||row.room.operational_state==="TECH_BLOCK")return;event.preventDefault();setTargetRoomId(row.room.id);setTargetDate(dateFromRow(event))}} onDragLeave={event=>{if(event.currentTarget.contains(event.relatedTarget as Node|null))return;if(targetRoomId===row.room.id){setTargetRoomId(null);setTargetDate(null)}} onDrop={event=>drop(row.room,event)}>
          <button className="v8-room-cell" onClick={()=>setRoomId(row.room.id)}><strong>№ {row.room.code}</strong><span>{row.room.room_type_name}</span><small>{[row.room.building_or_zone,row.room.floor].filter(Boolean).join(" · ")||"—"}</small></button>
          <div className="v8-state-cell"><span className={`state ${row.room.operational_state}`}>{ROOM_STATE[row.room.operational_state]}</span></div>
          {days.map((day,index)=>{const key=localDate(day);const targeted=targetRoomId===row.room.id&&targetDate===key;return <div key={key} className={`v8-day-bg ${key===today?"today":""} ${day.getDay()===0||day.getDay()===6?"weekend":""} ${targeted?"targeted":""}`} style={{gridColumn:`${3+index} / ${4+index}`}}/>})}
          {row.room.blocks.map(block=>{const place=blockPlacement(block);if(!place)return null;const fin=block.reservation_id?financeById.get(block.reservation_id):undefined;const payment=paymentClass(fin);const interactive=block.type==="RESERVATION"&&Boolean(block.reservation_id);const multi=fin?.schedule_segments&&fin.schedule_segments>1;const title=block.type==="RESERVATION"?(block.guest_name||block.booking_number||"Бронь"):(block.reason||(block.type==="MAINTENANCE"?"Ремонт":"Блок"));return <button key={block.id} draggable={interactive&&!cutMode} className={`v8-block type-${block.type.toLowerCase()} status-${(block.reservation_status||"none").toLowerCase()} payment-${payment} ${multi?"multi-segment":""}`} style={{gridColumn:place.column}} onDragStart={event=>dragStart(event,row.room,block)} onDragEnd={()=>{setDragging(null);setTargetRoomId(null);setTargetDate(null)}} onClick={event=>openBlock(event,row.room,block,place)} title={`${title} · ${block.start} → ${block.end}${multi?` · ${fin?.schedule_segments} сегм.`:""}`}><span className="v8-block-title">{cutMode&&interactive?"✂ ":multi?"⛓ ":""}{title}</span><span className="v8-block-meta">{block.booking_number||block.type}{fin&&<b className={`money-${payment}`}>{fin.remainingKgs<=0?"✓":`${money(fin.remainingKgs)} сом`}</b>}</span>{interactive&&<i className="v8-grip">⋮⋮</i>}</button>})}
        </div>)}
      </div>
      <footer className="v8-legend"><span><i className="guaranteed"/>Ожидает</span><span><i className="checked"/>Проживает</span><span><i className="maintenance"/>Ремонт</span><span>⛓ несколько сегментов</span><span>✂ разрез по границе дня</span><span>Все изменения: preview → подтверждение → commit.</span></footer>
    </div>

    {builder&&<ReservationScheduleBuilder reservationId={builder.reservationId} rooms={(data?.rooms||[]).map(room=>({id:room.id,code:room.code,room_type_code:room.room_type_code,room_type_name:room.room_type_name,operational_state:room.operational_state,building_or_zone:room.building_or_zone,floor:room.floor}))} intent={builder.intent} onClose={()=>setBuilder(null)} onUpdated={refresh}/>} 
    {roomId&&<RoomDetailModal roomId={roomId} onClose={()=>setRoomId(null)} onUpdated={refresh}/>} 
  </section>;
}
