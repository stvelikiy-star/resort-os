export default function StaffShiftVisualFixture() {
  return <main className="shift-shell" data-staff-qa-fixture="true">
    <header className="shift-head">
      <div><img src="/marina-smart-approved.png" alt="MARINA SMART" width={44} height={44} style={{objectFit:"contain",display:"block"}}/><p className="shift-eyebrow">MARINA SMART · Моя смена</p><h1>Очень длинное имя сотрудника для проверки переноса</h1><span>Ресепшен · Кыргызская Республика</span></div>
      <button className="shift-ghost">Выйти</button>
    </header>
    <section className="shift-kpis" aria-label="Сводка смены">
      <button className="active"><strong>7</strong><span>мои сейчас</span></button>
      <button><strong>12</strong><span>можно взять</span></button>
      <button><strong>4</strong><span>завершено</span></button>
    </section>
    <section className="shift-stack" aria-label="Задачи">
      <article className="shift-task priority-HIGH">
        <div className="shift-task-meta"><span>Приоритет</span><b>В работе</b></div>
        <div className="shift-room"><strong>№ 307</strong><span>Уборка номера</span></div>
        <h2>Подготовить помещение к заезду</h2>
        <p>Проверка длинного описания заявки на узком экране без горизонтальной прокрутки.</p>
        <div className="shift-actions"><button className="shift-primary">Взять в работу</button></div>
      </article>
    </section>
    <section className="shift-modal" role="dialog" aria-modal="false" aria-label="Отчёт по задаче" style={{ marginTop: 20, borderRadius: 24 }}>
      <div className="shift-modal-head"><h2>Контроль выполнения задачи</h2><button className="shift-ghost" aria-label="Закрыть">×</button></div>
      <div className="shift-checklist"><label><input type="checkbox" defaultChecked /><span>Проверка номера и состояния</span></label></div>
      <label className="shift-field"><span>Комментарий сотрудника</span><textarea defaultValue="Смена проверена" /></label>
      <button className="shift-primary shift-submit">Сохранить отчёт</button>
    </section>
  </main>;
}
