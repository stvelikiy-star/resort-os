"use client";

import { FormEvent, useEffect, useState } from "react";

type TaskType = "HOUSEKEEPING" | "MAINTENANCE" | "GUEST_REQUEST";
type TaskStatus = "OPEN" | "IN_PROGRESS" | "IN_INSPECTION" | "DONE" | "CANCELLED";
type OpsTask = {
  id:string; type:TaskType; status:TaskStatus; priority:string; title:string;
  room_id:string|null; room_code:string|null; room_state:string|null;
  assigned_to_id:string|null; assigned_to_name:string|null;
  description:string|null; source:string;
};
type Room = {id:string;code:string;name:string};
type Staff = {id:string;display_name:string;role:string;active:boolean};

const uuid = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
const management = new Set(["OWNER","MANAGER"]);
const types:TaskType[]=["HOUSEKEEPING","MAINTENANCE","GUEST_REQUEST"];
const statuses:TaskStatus[]=["OPEN","IN_PROGRESS","IN_INSPECTION","DONE","CANCELLED"];

function taskTypeFor(role:string,type:string){
  return management.has(role) && types.includes(type as TaskType) ||
    role==="MAID" && type==="HOUSEKEEPING" ||
    role==="TECHNICIAN" && type==="MAINTENANCE";
}
function localDate(delta:number){
  const now=new Date();now.setDate(now.getDate()+delta);
  const pad=(x:number)=>String(x).padStart(2,"0");
  return now.getFullYear()+"-"+pad(now.getMonth()+1)+"-"+pad(now.getDate());
}

/** Thin UI: backend is authoritative for role, state, hotel and assignee. */
export default function SharedOperationsPanel({role,userId,propertyCode,onExpired}:{
  role:string;userId:string;propertyCode:string;onExpired:()=>void;
}){
  const [tasks,setTasks]=useState<OpsTask[]|null>(null);
  const [rooms,setRooms]=useState<Room[]>([]);
  const [staff,setStaff]=useState<Staff[]>([]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [kind,setKind]=useState<TaskType>("HOUSEKEEPING");
  const [title,setTitle]=useState("");
  const [roomId,setRoomId]=useState("");
  const [assignee,setAssignee]=useState("");
  const [priority,setPriority]=useState("NORMAL");

  async function checked(path:string, options?:RequestInit){
    const res=await fetch("/core"+path,{cache:"no-store",...options});
    if(res.status===401){onExpired();throw new Error("expired");}
    return res;
  }
  async function refresh(){
    const res=await checked("/api/v1/ops/tasks");
    if(!res.ok)throw new Error("task list unavailable");
    const data=await res.json() as {items?:OpsTask[]};
    if(!Array.isArray(data.items) || data.items.some(task=>
      !uuid.test(task.id) || !types.includes(task.type) || !statuses.includes(task.status) ||
      !taskTypeFor(role,task.type))) throw new Error("task role/scope contract failed");
    setTasks(data.items);
  }

  useEffect(()=>{
    let alive=true;
    void (async ()=>{
      try {
        const res=await fetch("/core/api/v1/ops/tasks",{cache:"no-store"});
        if(res.status===401){if(alive)onExpired();return;}
        if(!res.ok)throw new Error("list");
        const data=await res.json() as {items?:OpsTask[]};
        if(!Array.isArray(data.items) || data.items.some(task=>
          !uuid.test(task.id) || !types.includes(task.type) || !statuses.includes(task.status) ||
          !taskTypeFor(role,task.type))) throw new Error("role-bound list");
        if(alive)setTasks(data.items);
        if(!alive || !management.has(role))return;
        // Optional hotel-local selectors; failures cannot grant extra roles.
        const [gridResponse,staffResponse]=await Promise.all([
          fetch("/core/api/v1/pms/grid?start="+localDate(0)+"&end="+localDate(1),{cache:"no-store"}),
          fetch("/core/api/v1/admin/staff/overview",{cache:"no-store"}),
        ]);
        if(gridResponse.ok){
          const grid=await gridResponse.json();
          if(grid.property!==propertyCode || !Array.isArray(grid.rooms))
            throw new Error("foreign room data");
          if(alive)setRooms(grid.rooms.filter((room:Room)=>uuid.test(room.id)));
        }
        if(staffResponse.ok){
          const body=await staffResponse.json();
          if(!Array.isArray(body.staff))throw new Error("invalid staff list");
          if(alive)setStaff(body.staff.filter((member:Staff)=>
            uuid.test(member.id) && member.active &&
            (member.role==="MAID" || member.role==="TECHNICIAN")));
        }
      }catch{if(alive)setError("Операционные данные не подтверждены или недоступны для роли.");}
    })();
    return ()=>{alive=false;};
  },[role,propertyCode]);

  async function create(e:FormEvent){
    e.preventDefault();
    if(busy || !management.has(role) || !title.trim() || !types.includes(kind))return;
    if(roomId && !rooms.some(r=>r.id===roomId)){setError("Номер не подтверждён.");return;}
    if(assignee && !staff.some(s=>s.id===assignee &&
        (kind==="HOUSEKEEPING" && s.role==="MAID" ||
         kind==="MAINTENANCE" && s.role==="TECHNICIAN"))){
      setError("Исполнитель не подходит для выбранной задачи.");return;
    }
    if(!window.confirm("Создать задачу "+kind+" для этой гостиницы?"))return;
    setBusy(true);setError("");setNotice("");
    try{
      const response=await checked("/api/v1/ops/tasks",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({type:kind,title:title.trim(),priority,
          room_id:roomId||null,assigned_to_id:assignee||null,source:"PMS"}),
      });
      if(response.status!==201)throw new Error("unconfirmed");
      const data=await response.json();
      if(!uuid.test(data.id)||data.status!=="OPEN")throw new Error("bad receipt");
      setNotice("Задача подтверждена сервером: "+data.id);
      setTitle("");setRoomId("");setAssignee("");
      try{await refresh();}
      catch{setError("Задача создана, но список не обновился. Обновите список.");}
    }catch{setError("Результат создания не подтверждён. Проверьте список перед повтором.");}
    finally{setBusy(false);}
  }
  async function act(task:OpsTask,action:"claim"|"IN_INSPECTION"|"IN_PROGRESS"|"DONE"){
    if(busy || !taskTypeFor(role,task.type))return;
    if(action==="DONE" && !window.confirm("Подтвердить завершение задачи "+task.title+"?"))return;
    setBusy(true);setError("");setNotice("");
    try{
      const path="/api/v1/ops/tasks/"+task.id+
        (action==="claim"?"/claim":"/status");
      const res=await checked(path,action==="claim"?
        {method:"POST"}:
        {method:"PATCH",headers:{"Content-Type":"application/json"},
          body:JSON.stringify({status:action})});
      if(res.status===409){setError("Состояние задачи изменилось. Обновите список.");return;}
      if(!res.ok)throw new Error("unconfirmed");
      const data=await res.json();
      if(data.id!==task.id || data.status!==(action==="claim"?"IN_PROGRESS":action))
        throw new Error("unverified status");
      setNotice("Задача "+task.title+": "+data.status+" — подтверждено сервером.");
      try{await refresh();}
      catch{setError("Изменение принято, но список не обновился. Обновите данные.");}
    }catch{setError("Результат действия не подтверждён. Проверьте список перед повтором.");}
    finally{setBusy(false);}
  }
  function allowedActions(task:OpsTask):Array<{action:"claim"|"IN_INSPECTION"|"IN_PROGRESS"|"DONE";label:string}>{
    const mine=task.assigned_to_id===userId;
    const free=task.assigned_to_id===null;
    const manager=management.has(role);
    if(task.status==="OPEN"){
      if(!manager && free)return [{action:"claim",label:"Взять задачу"}];
      if(!manager && mine)return [{action:"claim",label:"Начать"}];
      if(manager)return [{action:"IN_PROGRESS",label:"Начать"}];
    }
    if(task.type==="HOUSEKEEPING" && task.status==="IN_PROGRESS" && (mine||manager))
      return [{action:"IN_INSPECTION",label:"На проверку"}];
    if(task.type==="HOUSEKEEPING" && task.status==="IN_INSPECTION" && manager)
      return [{action:"DONE",label:"Принять уборку"},{action:"IN_PROGRESS",label:"Вернуть на доработку"}];
    if(task.type==="MAINTENANCE" && task.status==="IN_PROGRESS" && (mine||manager))
      return [{action:"DONE",label:"Ремонт выполнен"}];
    if(task.type==="GUEST_REQUEST" && task.status==="IN_PROGRESS" && manager)
      return [{action:"DONE",label:"Заявка выполнена"}];
    return [];
  }
  const assigned=staff.filter(item=>kind==="HOUSEKEEPING"?
    item.role==="MAID":kind==="MAINTENANCE"?item.role==="TECHNICIAN":false);
  return <section aria-label="Операционные задачи гостиницы">
    <h2>Задачи · своя гостиница</h2>
    <p>Горничная — уборка, техник — ремонт. Проверку уборки и изменения прав выполняет руководство.</p>
    <button className="btn" type="button" disabled={busy} onClick={()=>{
      setBusy(true);setError("");setNotice("");
      void refresh().catch(()=>setError("Список задач не подтверждён.")).finally(()=>setBusy(false));
    }}>Обновить задачи</button>
    {management.has(role) && <form aria-label="Создать операционную задачу" onSubmit={e=>void create(e)}>
      <h3>Новая задача</h3>
      <label>Вид задачи<select value={kind} disabled={busy} onChange={e=>{
        setKind(e.target.value as TaskType);setAssignee("");
      }}>
        <option value="HOUSEKEEPING">Уборка</option>
        <option value="MAINTENANCE">Ремонт</option>
        <option value="GUEST_REQUEST">Заявка гостя</option>
      </select></label>
      <label>Название<input required minLength={2} maxLength={180}
        disabled={busy} value={title} onChange={e=>setTitle(e.target.value)}/></label>
      <label>Приоритет<select disabled={busy} value={priority}
        onChange={e=>setPriority(e.target.value)}>
        <option value="LOW">Низкий</option><option value="NORMAL">Обычный</option>
        <option value="HIGH">Высокий</option><option value="URGENT">Срочный</option>
      </select></label>
      <label>Номер<select value={roomId} disabled={busy} onChange={e=>setRoomId(e.target.value)}>
        <option value="">Без номера</option>
        {rooms.map(room=><option key={room.id} value={room.id}>{room.code} · {room.name}</option>)}
      </select></label>
      <label>Исполнитель<select value={assignee} disabled={busy} onChange={e=>setAssignee(e.target.value)}>
        <option value="">Без назначения</option>
        {assigned.map(person=><option key={person.id} value={person.id}>{person.display_name}</option>)}
      </select></label>
      <button className="btn primary" type="submit" disabled={busy}>Создать задачу</button>
    </form>}
    {tasks===null ? <p role="status">Загружаю задачи…</p>:
      tasks.length===0 ? <p>Для этой роли открытых и исторических задач нет.</p>:
      <div aria-label="Список задач гостиницы">
        {tasks.map(task=><article key={task.id} aria-label={"Задача "+task.title}
          style={{borderTop:"1px solid #aaa",padding:"12px 0"}}>
          <p><strong>{task.title}</strong> · {task.type} · {task.status}</p>
          <p>{task.room_code || "Без номера"} · {task.priority}
            {task.assigned_to_name ? " · "+task.assigned_to_name:" · Не назначено"}</p>
          {task.description && <p>{task.description}</p>}
          {allowedActions(task).map(a=><button className="btn" disabled={busy} type="button"
            key={a.action} onClick={()=>void act(task,a.action)}>{a.label}</button>)}
        </article>)}
      </div>}
    {notice&&<p role="status">{notice}</p>}
    {error&&<p role="alert">{error}</p>}
  </section>;
}
