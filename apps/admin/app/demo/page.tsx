"use client";

import { useMemo, useState } from "react";
import "./demo.css";

type State = "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK";
type View = "ALL" | "ARRIVALS" | "DEPARTURES" | "IN_HOUSE" | "FREE";

type Booking = { id:string; guest:string; phone:string; status:"GUARANTEED"|"CHECKED_IN"; start:number; span:number; amount:string; source:string; note?:string };
type Room = { code:string; type:string; state:State; floor:string; zone:string; booking?:Booking; tech?:{start:number;span:number;reason:string} };

const dates = ["26 авг","27 авг","28 авг","29 авг","30 авг","31 авг","1 сен","2 сен","3 сен","4 сен","5 сен","6 сен","7 сен","8 сен"];
const rooms:Room[] = [
  {code:"101",type:"Двухместный улучшенный",state:"CLEAN",floor:"1 этаж",zone:"Корпус A",booking:{id:"TK-260826-018",guest:"Айбек Т.",phone:"+996 555 34 18 02",status:"CHECKED_IN",start:0,span:4,amount:"28 000 сом",source:"WhatsApp"}},
  {code:"102",type:"Двухместный улучшенный",state:"DIRTY",floor:"1 этаж",zone:"Корпус A",booking:{id:"TK-260828-021",guest:"Марина С.",phone:"+7 921 440 12 82",status:"GUARANTEED",start:2,span:5,amount:"42 500 сом",source:"Сайт"}},
  {code:"103",type:"Люкс двухместный",state:"CLEAN",floor:"1 этаж",zone:"Корпус A",booking:{id:"TK-260827-023",guest:"Нурбек К.",phone:"+996 700 77 43 20",status:"GUARANTEED",start:1,span:3,amount:"33 000 сом",source:"Instagram"}},
  {code:"104",type:"Люкс трёхместный",state:"IN_INSPECTION",floor:"1 этаж",zone:"Корпус A"},
  {code:"201",type:"Двухкомнатный полулюкс",state:"CLEAN",floor:"2 этаж",zone:"Корпус A",booking:{id:"TK-260826-017",guest:"Елена П.",phone:"+7 916 213 02 44",status:"CHECKED_IN",start:0,span:6,amount:"66 000 сом",source:"Telegram"}},
  {code:"202",type:"Двухкомнатный стандарт",state:"CLEAN",floor:"2 этаж",zone:"Корпус A",booking:{id:"TK-260830-030",guest:"Алихан М.",phone:"+996 777 88 11 04",status:"GUARANTEED",start:4,span:4,amount:"36 000 сом",source:"Сайт"}},
  {code:"203",type:"Апартаменты",state:"DIRTY",floor:"2 этаж",zone:"Корпус A"},
  {code:"204",type:"Апартаменты с кухней",state:"TECH_BLOCK",floor:"2 этаж",zone:"Корпус A",tech:{start:0,span:3,reason:"Кондиционер · техник"}},
  {code:"C01",type:"Стандарт в коттеджном доме",state:"CLEAN",floor:"1 этаж",zone:"Коттедж 1",booking:{id:"TK-260829-027",guest:"Диана А.",phone:"+996 502 11 90 33",status:"GUARANTEED",start:3,span:5,amount:"40 000 сом",source:"WhatsApp"}},
  {code:"C02",type:"Стандарт в коттеджном доме",state:"CLEAN",floor:"1 этаж",zone:"Коттедж 1"},
  {code:"B01",type:"Одноместный, цоколь",state:"CLEAN",floor:"Цоколь",zone:"Корпус B",booking:{id:"TK-260826-016",guest:"Азамат Р.",phone:"+996 550 20 01 05",status:"CHECKED_IN",start:0,span:2,amount:"8 000 сом",source:"Ресепшен"}},
  {code:"B02",type:"Двухместный стандарт, цоколь",state:"IN_INSPECTION",floor:"Цоколь",zone:"Корпус B"},
  {code:"B03",type:"Полулюкс без балкона",state:"CLEAN",floor:"Цоколь",zone:"Корпус B",booking:{id:"TK-260831-032",guest:"Семья Орловых",phone:"+7 999 140 61 70",status:"GUARANTEED",start:5,span:6,amount:"54 000 сом",source:"Сайт"}},
  {code:"301",type:"Одноместный улучшенный",state:"CLEAN",floor:"3 этаж",zone:"Корпус A"},
  {code:"302",type:"Двухместный улучшенный",state:"CLEAN",floor:"3 этаж",zone:"Корпус A",booking:{id:"TK-260901-035",guest:"Бакыт Ж.",phone:"+996 707 41 10 62",status:"GUARANTEED",start:6,span:4,amount:"34 000 сом",source:"Telegram"}},
];

const stateLabels:Record<State,string>={CLEAN:"Готов",DIRTY:"Уборка",IN_INSPECTION:"Проверка",TECH_BLOCK:"Ремонт"};

export default function DemoPage(){
  const [query,setQuery]=useState("");
  const [type,setType]=useState("ALL");
  const [state,setState]=useState("ALL");
  const [view,setView]=useState<View>("ALL");
  const [selected,setSelected]=useState<Booking|null>(null);
  const types=useMemo(()=>Array.from(new Set(rooms.map(r=>r.type))).sort(),[]);
  const filtered=useMemo(()=>rooms.filter(room=>{
    const q=query.trim().toLowerCase();
    const matchQ=!q||`${room.code} ${room.type} ${room.zone}`.toLowerCase().includes(q);
    const matchType=type==="ALL"||room.type===type;
    const matchState=state==="ALL"||room.state===state;
    const arrival=room.booking?.status==="GUARANTEED"&&room.booking.start<=1;
    const departure=room.booking?.status==="CHECKED_IN"&&(room.booking.start+room.booking.span)<=2;
    const inHouse=room.booking?.status==="CHECKED_IN";
    const free=!room.booking&&!room.tech&&room.state!=="TECH_BLOCK";
    const matchView=view==="ALL"||(view==="ARRIVALS"&&!!arrival)||(view==="DEPARTURES"&&!!departure)||(view==="IN_HOUSE"&&!!inHouse)||(view==="FREE"&&free);
    return matchQ&&matchType&&matchState&&matchView;
  }),[query,type,state,view]);

  const occupied=rooms.filter(r=>r.booking).length;
  const ready=rooms.filter(r=>r.state==="CLEAN").length;
  const dirty=rooms.filter(r=>r.state==="DIRTY").length;
  const tech=rooms.filter(r=>r.state==="TECH_BLOCK").length;

  return <main className="demo-shell">
    <header className="demo-top">
      <div className="demo-brand"><strong>ТРИ КОРОНЫ · RESORT OS</strong><span>Клиентская демонстрация PMS</span></div>
      <nav className="demo-nav"><button>Главная</button><button className="active">Шахматка</button><button>Заявки</button><button>Брони</button><button>Финансы</button><button>Операции</button><button>Персонал</button><button>NFC</button></nav>
      <div className="demo-badge">DEMO · 26.08.2026</div>
    </header>

    <section className="demo-main">
      <div className="demo-head"><div><h1>Шахматка номерного фонда</h1><p>84 номера · realtime PMS · бронирования, уборка, ремонт и загрузка в одном экране</p></div><div className="demo-actions"><button className="demo-btn">Сегодня</button><button className="demo-btn primary">+ Новая бронь</button></div></div>

      <div className="demo-kpis">
        <article className="demo-kpi"><span>Загрузка сегодня</span><strong>72%</strong><small>+8% к прошлой неделе</small></article>
        <article className="demo-kpi"><span>Проживают</span><strong>{occupied}</strong><small>гостей в демо-срезе</small></article>
        <article className="demo-kpi"><span>Готовы</span><strong>{ready}</strong><small>можно заселять</small></article>
        <article className="demo-kpi"><span>На уборке</span><strong>{dirty}</strong><small>2 приоритетных</small></article>
        <article className="demo-kpi"><span>Ремонт</span><strong>{tech}</strong><small>1 техблок</small></article>
        <article className="demo-kpi"><span>Выручка сегодня</span><strong>186 500</strong><small>сом · оплачено 81%</small></article>
      </div>

      <section className="demo-board">
        <div className="demo-filters">
          <input className="demo-search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Номер, категория, корпус…" />
          <select className="demo-select" value={type} onChange={e=>setType(e.target.value)}><option value="ALL">Все категории</option>{types.map(t=><option key={t}>{t}</option>)}</select>
          <select className="demo-select" value={state} onChange={e=>setState(e.target.value)}><option value="ALL">Все статусы</option><option value="CLEAN">Готов</option><option value="DIRTY">Уборка</option><option value="IN_INSPECTION">Проверка</option><option value="TECH_BLOCK">Ремонт</option></select>
          <div className="view-tabs"><button className={view==="ALL"?"active":""} onClick={()=>setView("ALL")}>Все</button><button className={view==="ARRIVALS"?"active":""} onClick={()=>setView("ARRIVALS")}>Заезды</button><button className={view==="DEPARTURES"?"active":""} onClick={()=>setView("DEPARTURES")}>Выезды</button><button className={view==="IN_HOUSE"?"active":""} onClick={()=>setView("IN_HOUSE")}>Проживают</button><button className={view==="FREE"?"active":""} onClick={()=>setView("FREE")}>Свободны</button></div>
        </div>
        <div className="legend"><span className="clean"><i/>Готов</span><span className="dirty"><i/>Уборка</span><span className="inspect"><i/>Проверка</span><span className="tech"><i/>Ремонт</span><span>Синий — подтверждённая бронь</span><span>Зелёный — проживает</span></div>
        <div className="grid-wrap"><div className="pms-grid">
          <div className="grid-head"><div className="left">Номер / категория</div><div>Статус</div>{dates.map((d,i)=><div key={d} className={i===0?"today-cell":""}>{d}</div>)}</div>
          {filtered.map(room=><div className="room-row" key={room.code}>
            <div className="room-meta"><div><strong>{room.code} · {room.type}</strong><small>{room.zone} · {room.floor}</small></div></div>
            <div className="room-state"><span className={`state-pill state-${room.state}`}>{stateLabels[room.state]}</span></div>
            {dates.map((d,i)=><div className={`day-cell ${i===0?"today-cell":""}`} key={d} style={{gridColumn:3+i}} />)}
            {room.booking&&<button onClick={()=>setSelected(room.booking!)} className={`booking ${room.booking.status==="CHECKED_IN"?"inhouse":room.booking.start<=1?"arrival":"guaranteed"}`} style={{gridColumn:`${3+room.booking.start} / ${3+room.booking.start+room.booking.span}`}}><strong>{room.booking.guest}</strong><small>{room.booking.id}</small></button>}
            {room.tech&&<div className="booking tech" style={{gridColumn:`${3+room.tech.start} / ${3+room.tech.start+room.tech.span}`}}><strong>{room.tech.reason}</strong><small>TECH_BLOCK</small></div>}
          </div>)}
          {!filtered.length&&<div className="empty-state">По этим фильтрам номеров нет.</div>}
        </div></div>
      </section>

      <div className="demo-panels">
        <section className="demo-panel"><h3>Сегодня на ресепшене</h3><div className="queue"><div className="queue-item"><div><strong>14:00 · Заезд · Марина С.</strong><span>102 · Двухместный улучшенный · предоплата подтверждена</span></div><b>ГОТОВО</b></div><div className="queue-item"><div><strong>12:00 · Выезд · Азамат Р.</strong><span>B01 · после выезда автоматически → DIRTY</span></div><b>ВЫЕЗД</b></div><div className="queue-item"><div><strong>До 13:30 · Проверка комнаты 104</strong><span>горничная завершила чек-лист, ожидает менеджера</span></div><b>INSPECTION</b></div></div></section>
        <section className="demo-panel"><h3>Продажи</h3><div className="metric-line"><span>Новые заявки</span><strong>18</strong></div><div className="metric-line"><span>Конверсия в бронь</span><strong>41%</strong></div><div className="metric-line"><span>Средний чек</span><strong>31 800 сом</strong></div><div className="metric-line"><span>Источники</span><strong>Сайт · WA · TG · IG</strong></div></section>
        <section className="demo-panel"><h3>Операции & NFC</h3><div className="metric-line"><span>Активных браслетов</span><strong>67</strong></div><div className="metric-line"><span>Оборот NFC сегодня</span><strong>48 350 сом</strong></div><div className="metric-line"><span>Комиссия пляжа</span><strong>2 417 сом</strong></div><div className="metric-line"><span>Тикеты техников</span><strong>3</strong></div></section>
      </div>
      <div className="demo-note">Демонстрационный экран использует безопасные тестовые данные. Производственная админка работает через Resort Core, PostgreSQL и защищённую авторизацию.</div>
    </section>

    {selected&&<div className="modal-backdrop" onClick={()=>setSelected(null)}><div className="demo-modal" onClick={e=>e.stopPropagation()}><h2>{selected.guest}</h2><p>{selected.id} · {selected.status==="CHECKED_IN"?"Гость проживает":"Бронь подтверждена"}</p><div className="modal-grid"><div><span>Телефон</span><strong>{selected.phone}</strong></div><div><span>Источник</span><strong>{selected.source}</strong></div><div><span>Проживание</span><strong>{selected.span} ноч.</strong></div><div><span>Сумма</span><strong>{selected.amount}</strong></div><div><span>Статус оплаты</span><strong>Предоплата подтверждена</strong></div><div><span>Действия</span><strong>Переселить · Продлить · Выезд</strong></div></div><div className="modal-actions"><button className="demo-btn" onClick={()=>setSelected(null)}>Закрыть</button><button className="demo-btn primary">Открыть бронь</button></div></div></div>}
  </main>;
}
