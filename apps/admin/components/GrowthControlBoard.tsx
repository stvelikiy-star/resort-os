"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Summary = {
  local_date: string;
  queue: { active: number; overdue: number; feedback_open: number; return_open: number };
  feedback: {
    engagements: number;
    scored: number;
    average_score: number | null;
    promoters: number;
    passives: number;
    detractors: number;
    recovery_open: number;
    nps: number | null;
    nps_sample_size: number;
  };
  candidates: { post_stay_14d: number; reactivation: number; reactivation_min_days: number };
  truth: Record<string, string>;
};

type Engagement = {
  id: string;
  kind: "POST_STAY_FEEDBACK" | "RETURN_GUEST" | "MANAGER_FOLLOWUP";
  status: "OPEN" | "IN_PROGRESS" | "DONE" | "CANCELLED";
  guest: { id: string; name: string; phone?: string | null; email?: string | null };
  reservation?: null | { id: string; booking_number: string; status: string; check_in: string; check_out: string };
  due_date?: string | null;
  channel_hint?: string | null;
  title: string;
  notes?: string | null;
  score?: number | null;
  nps_class?: "PROMOTER" | "PASSIVE" | "DETRACTOR" | null;
  feedback_text?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  outbound_authority: string;
};

type PostStayCandidate = {
  reservation_id: string;
  booking_number: string;
  guest_id: string;
  guest_name: string;
  phone?: string | null;
  email?: string | null;
  check_in: string;
  check_out: string;
  days_since_checkout: number;
};

type ReactivationCandidate = {
  guest_id: string;
  guest_name: string;
  phone?: string | null;
  email?: string | null;
  completed_stays: number;
  last_checkout: string;
  days_since_checkout: number;
  completed_booked_value_kgs: number;
};

const kindLabel: Record<Engagement["kind"], string> = {
  POST_STAY_FEEDBACK: "Post-stay / отзыв",
  RETURN_GUEST: "Возврат гостя",
  MANAGER_FOLLOWUP: "Follow-up менеджера",
};

const statusLabel: Record<Engagement["status"], string> = {
  OPEN: "Открыто",
  IN_PROGRESS: "В работе",
  DONE: "Готово",
  CANCELLED: "Отменено",
};

const npsLabel = { PROMOTER: "Промоутер", PASSIVE: "Нейтральный", DETRACTOR: "Требует recovery" } as const;
const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(Math.round(value || 0))} сом`;
const fmtDate = (value?: string | null) => value ? new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(`${value}T12:00:00`)) : "—";

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", ...init });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : detail?.message || detail?.code || "Ошибка Resort Core";
    throw new Error(message);
  }
  return body as T;
}

export default function GrowthControlBoard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [postStay, setPostStay] = useState<PostStayCandidate[]>([]);
  const [reactivation, setReactivation] = useState<ReactivationCandidate[]>([]);
  const [statusFilter, setStatusFilter] = useState("ACTIVE");
  const [kindFilter, setKindFilter] = useState("ALL");
  const [reactivationDays, setReactivationDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [feedbackTarget, setFeedbackTarget] = useState<Engagement | null>(null);
  const [score, setScore] = useState(10);
  const [feedbackText, setFeedbackText] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const engagementQuery = new URLSearchParams();
      if (kindFilter !== "ALL") engagementQuery.set("kind", kindFilter);
      if (!["ALL", "ACTIVE"].includes(statusFilter)) engagementQuery.set("status", statusFilter);
      engagementQuery.set("limit", "200");
      const [summaryBody, engagementBody, postBody, reactBody] = await Promise.all([
        api<Summary>(`/core/api/v1/admin/growth/summary?min_days_since_checkout=${reactivationDays}`),
        api<{ items: Engagement[] }>(`/core/api/v1/admin/growth/engagements?${engagementQuery}`),
        api<{ items: PostStayCandidate[] }>("/core/api/v1/admin/growth/candidates/post-stay?lookback_days=14&limit=100"),
        api<{ items: ReactivationCandidate[] }>(`/core/api/v1/admin/growth/candidates/reactivation?min_days_since_checkout=${reactivationDays}&limit=100`),
      ]);
      setSummary(summaryBody);
      setEngagements(statusFilter === "ACTIVE" ? engagementBody.items.filter((item) => ["OPEN", "IN_PROGRESS"].includes(item.status)) : engagementBody.items);
      setPostStay(postBody.items);
      setReactivation(reactBody.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка Growth Control");
    } finally {
      setLoading(false);
    }
  }, [kindFilter, statusFilter, reactivationDays]);

  useEffect(() => { void load(); }, [load]);

  async function createFromCandidate(candidate: PostStayCandidate | ReactivationCandidate, kind: "POST_STAY_FEEDBACK" | "RETURN_GUEST") {
    const key = kind === "POST_STAY_FEEDBACK" ? (candidate as PostStayCandidate).reservation_id : candidate.guest_id;
    setBusyId(key);
    setError(null);
    setNotice(null);
    try {
      const dueDate = new Date();
      dueDate.setDate(dueDate.getDate() + (kind === "POST_STAY_FEEDBACK" ? 1 : 3));
      const body = kind === "POST_STAY_FEEDBACK"
        ? {
            guest_id: candidate.guest_id,
            reservation_id: (candidate as PostStayCandidate).reservation_id,
            kind,
            due_date: dueDate.toISOString().slice(0, 10),
            title: `Получить обратную связь · ${(candidate as PostStayCandidate).booking_number}`,
            channel_hint: candidate.phone ? "PHONE_OR_MESSENGER" : "EMAIL",
            notes: "Внутренняя задача менеджера. Автоматическая отправка не разрешена.",
          }
        : {
            guest_id: candidate.guest_id,
            kind,
            due_date: dueDate.toISOString().slice(0, 10),
            title: `Возврат гостя · ${candidate.guest_name}`,
            channel_hint: candidate.phone ? "PHONE_OR_MESSENGER" : "EMAIL",
            notes: "Проверить актуальность контакта и допустимость коммуникации до любого outbound-действия.",
          };
      await api("/core/api/v1/admin/growth/engagements", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setNotice(kind === "POST_STAY_FEEDBACK" ? "Post-stay задача создана." : "Задача возврата гостя создана.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать задачу");
    } finally {
      setBusyId(null);
    }
  }

  async function patchStatus(item: Engagement, next: Engagement["status"]) {
    setBusyId(item.id);
    setError(null);
    try {
      await api(`/core/api/v1/admin/growth/engagements/${item.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: next }),
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось изменить статус");
    } finally {
      setBusyId(null);
    }
  }

  async function submitFeedback(event: FormEvent) {
    event.preventDefault();
    if (!feedbackTarget) return;
    setBusyId(feedbackTarget.id);
    setError(null);
    try {
      await api(`/core/api/v1/admin/growth/engagements/${feedbackTarget.id}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ score, feedback_text: feedbackText || null }),
      });
      setFeedbackTarget(null);
      setFeedbackText("");
      setScore(10);
      setNotice(score <= 6 ? "Оценка записана. Задача оставлена в recovery." : "Оценка записана.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось записать feedback");
    } finally {
      setBusyId(null);
    }
  }

  const activeRecovery = useMemo(() => engagements.filter((item) => item.nps_class === "DETRACTOR" && item.status === "IN_PROGRESS").length, [engagements]);

  return (
    <main className="growth-shell">
      <header className="growth-hero">
        <div>
          <p className="eyebrow">OWNER GROWTH CONTROL · MANAGER REVIEW ONLY</p>
          <h1>Рост, отзывы и возврат гостей</h1>
          <p>Post-stay обратная связь, NPS с реальным размером выборки, recovery недовольных гостей и фактическая очередь возврата — без автоматической рассылки и без AI-пропенсити.</p>
        </div>
        <button className="btn primary" onClick={load} disabled={loading}>{loading ? "Обновляю…" : "Обновить"}</button>
      </header>

      <section className="growth-policy">
        <strong>Outbound authority: NONE_AUTOMATIC</strong>
        <span>Этот раздел создаёт только внутреннюю работу менеджера. Кандидат в очередь ≠ согласие на маркетинг ≠ отправленное сообщение.</span>
      </section>

      {error && <div className="error-box">{error}</div>}
      {notice && <div className="growth-notice">{notice}</div>}

      {summary && (
        <>
          <section className="growth-kpis">
            <article><span>Активная очередь</span><strong>{summary.queue.active}</strong><small>{summary.queue.overdue} просрочено</small></article>
            <article><span>Ждут feedback</span><strong>{summary.queue.feedback_open}</strong><small>{summary.candidates.post_stay_14d} кандидатов за 14 дней</small></article>
            <article><span>Возврат гостей</span><strong>{summary.queue.return_open}</strong><small>{summary.candidates.reactivation} доступно по фильтру</small></article>
            <article className={summary.feedback.recovery_open > 0 ? "growth-danger" : ""}><span>Recovery</span><strong>{summary.feedback.recovery_open}</strong><small>оценка 0–6 и задача в работе</small></article>
            <article><span>NPS</span><strong>{summary.feedback.nps == null ? "—" : summary.feedback.nps}</strong><small>выборка: {summary.feedback.nps_sample_size}</small></article>
            <article><span>Средняя оценка</span><strong>{summary.feedback.average_score == null ? "—" : summary.feedback.average_score.toFixed(2)}</strong><small>{summary.feedback.scored} фактических ответов</small></article>
            <article><span>Промоутеры</span><strong>{summary.feedback.promoters}</strong><small>9–10</small></article>
            <article><span>Детракторы</span><strong>{summary.feedback.detractors}</strong><small>0–6</small></article>
          </section>

          <section className="growth-segments">
            <div><span>Promoters</span><strong>{summary.feedback.promoters}</strong></div>
            <div><span>Passives</span><strong>{summary.feedback.passives}</strong></div>
            <div><span>Detractors</span><strong>{summary.feedback.detractors}</strong></div>
            <div><span>Recovery сейчас</span><strong>{activeRecovery}</strong></div>
          </section>
        </>
      )}

      <section className="growth-card">
        <div className="growth-card-head">
          <div><p className="eyebrow">РАБОЧАЯ ОЧЕРЕДЬ</p><h2>Задачи менеджера</h2></div>
          <div className="growth-filters">
            <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value)}>
              <option value="ALL">Все типы</option>
              <option value="POST_STAY_FEEDBACK">Post-stay</option>
              <option value="RETURN_GUEST">Возврат гостя</option>
              <option value="MANAGER_FOLLOWUP">Follow-up</option>
            </select>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="ACTIVE">Активные</option>
              <option value="ALL">Все статусы</option>
              <option value="OPEN">Открытые</option>
              <option value="IN_PROGRESS">В работе</option>
              <option value="DONE">Готово</option>
              <option value="CANCELLED">Отменено</option>
            </select>
          </div>
        </div>
        {loading && engagements.length === 0 ? <div className="loading">Загружаю Growth Control…</div> : engagements.length === 0 ? <div className="empty small">По выбранным фильтрам задач нет.</div> : (
          <div className="growth-table">
            {engagements.map((item) => (
              <article className={`growth-row ${item.nps_class === "DETRACTOR" ? "is-recovery" : ""}`} key={item.id}>
                <div className="growth-row-main">
                  <div className="growth-badges">
                    <span className={`growth-kind k-${item.kind}`}>{kindLabel[item.kind]}</span>
                    <span className={`growth-status s-${item.status}`}>{statusLabel[item.status]}</span>
                    {item.nps_class && <span className={`growth-nps n-${item.nps_class}`}>{npsLabel[item.nps_class]}</span>}
                  </div>
                  <strong>{item.title}</strong>
                  <span>{item.guest.name}{item.reservation ? ` · ${item.reservation.booking_number}` : ""}</span>
                  <small>{item.guest.phone || item.guest.email || "контакт не указан"} · срок {fmtDate(item.due_date)}</small>
                  {item.notes && <p>{item.notes}</p>}
                  {item.feedback_text && <blockquote>{item.feedback_text}</blockquote>}
                </div>
                <div className="growth-row-score">
                  {item.score != null ? <><strong>{item.score}/10</strong><small>NPS факт</small></> : <><strong>—</strong><small>оценки нет</small></>}
                </div>
                <div className="growth-row-actions">
                  {item.status === "OPEN" && <button className="btn sm" disabled={busyId === item.id} onClick={() => patchStatus(item, "IN_PROGRESS")}>В работу</button>}
                  {item.status === "IN_PROGRESS" && <button className="btn sm" disabled={busyId === item.id} onClick={() => patchStatus(item, "DONE")}>Готово</button>}
                  {item.kind === "POST_STAY_FEEDBACK" && item.status !== "CANCELLED" && <button className="btn sm primary" onClick={() => { setFeedbackTarget(item); setScore(item.score ?? 10); setFeedbackText(item.feedback_text || ""); }}>Записать оценку</button>}
                  {!["DONE", "CANCELLED"].includes(item.status) && <button className="btn sm" disabled={busyId === item.id} onClick={() => patchStatus(item, "CANCELLED")}>Отменить</button>}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <div className="growth-two">
        <section className="growth-card">
          <div className="growth-card-head"><div><p className="eyebrow">POST-STAY</p><h2>Кому запросить обратную связь</h2></div><span>{postStay.length}</span></div>
          <p className="growth-caption">Только завершённые CHECKED_OUT-проживания за последние 14 дней с доступным контактом и без существующего feedback engagement.</p>
          <div className="growth-candidates">
            {postStay.length === 0 ? <div className="empty small">Новых кандидатов нет.</div> : postStay.map((candidate) => (
              <article key={candidate.reservation_id}>
                <div><strong>{candidate.guest_name}</strong><span>{candidate.booking_number} · выезд {fmtDate(candidate.check_out)}</span><small>{candidate.phone || candidate.email} · {candidate.days_since_checkout} дн. после выезда</small></div>
                <button className="btn sm" disabled={busyId === candidate.reservation_id} onClick={() => createFromCandidate(candidate, "POST_STAY_FEEDBACK")}>{busyId === candidate.reservation_id ? "Создаю…" : "В очередь"}</button>
              </article>
            ))}
          </div>
        </section>

        <section className="growth-card">
          <div className="growth-card-head"><div><p className="eyebrow">RETURN GUEST</p><h2>Кого можно вернуть</h2></div><span>{reactivation.length}</span></div>
          <div className="growth-reactivation-filter"><label>Не были минимум <input type="number" min={1} max={3650} value={reactivationDays} onChange={(e) => setReactivationDays(Math.max(1, Number(e.target.value) || 30))} /> дней</label></div>
          <p className="growth-caption">Фактическая история: есть завершённое проживание, есть контакт, нет будущей активной брони и нет активной RETURN_GUEST-задачи.</p>
          <div className="growth-candidates">
            {reactivation.length === 0 ? <div className="empty small">По выбранному периоду кандидатов нет.</div> : reactivation.map((candidate) => (
              <article key={candidate.guest_id}>
                <div><strong>{candidate.guest_name}</strong><span>{candidate.completed_stays} завершённых проживаний · последнее {fmtDate(candidate.last_checkout)}</span><small>{candidate.phone || candidate.email} · {candidate.days_since_checkout} дн. · {money(candidate.completed_booked_value_kgs)}</small></div>
                <button className="btn sm" disabled={busyId === candidate.guest_id} onClick={() => createFromCandidate(candidate, "RETURN_GUEST")}>{busyId === candidate.guest_id ? "Создаю…" : "В очередь"}</button>
              </article>
            ))}
          </div>
        </section>
      </div>

      {summary && <section className="growth-truth">
        <strong>Контроль достоверности</strong>
        <p>{summary.truth.nps}</p>
        <p>{summary.truth.reactivation}</p>
        <p>{summary.truth.outbound}</p>
      </section>}

      {feedbackTarget && (
        <div className="growth-modal-backdrop" role="presentation" onMouseDown={() => setFeedbackTarget(null)}>
          <form className="growth-modal" onSubmit={submitFeedback} onMouseDown={(e) => e.stopPropagation()}>
            <div><p className="eyebrow">ФАКТИЧЕСКИЙ FEEDBACK</p><h2>{feedbackTarget.guest.name}</h2><span>{feedbackTarget.reservation?.booking_number}</span></div>
            <label><span>Оценка 0–10</span><input type="number" min={0} max={10} value={score} onChange={(e) => setScore(Number(e.target.value))} required /></label>
            <div className="growth-score-scale">
              {[0,1,2,3,4,5,6,7,8,9,10].map((value) => <button type="button" key={value} className={score === value ? "active" : ""} onClick={() => setScore(value)}>{value}</button>)}
            </div>
            <label><span>Комментарий гостя / заметка менеджера</span><textarea rows={5} value={feedbackText} onChange={(e) => setFeedbackText(e.target.value)} placeholder="Записываем только фактически полученную обратную связь." /></label>
            <p className="growth-modal-note">0–6 автоматически оставит задачу в IN_PROGRESS как recovery. 7–10 завершит feedback-задачу. Никаких сообщений гостю из этого окна не отправляется.</p>
            <div className="growth-modal-actions"><button type="button" className="btn" onClick={() => setFeedbackTarget(null)}>Отмена</button><button className="btn primary" disabled={busyId === feedbackTarget.id}>{busyId === feedbackTarget.id ? "Сохраняю…" : "Сохранить feedback"}</button></div>
          </form>
        </div>
      )}
    </main>
  );
}
