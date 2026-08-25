"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Totals = {
  transaction_count: number;
  completed_count: number;
  reversed_count: number;
  gross_kgs: number;
  hotel_commission_kgs: number;
  partner_net_kgs: number;
};

type PartnerSummary = {
  partner_id: string;
  partner_name: string;
  username: string;
  completed_count: number;
  gross_kgs: number;
  hotel_commission_kgs: number;
  partner_net_kgs: number;
  last_transaction_at?: string | null;
};

type Transaction = {
  id: string;
  partner_id: string;
  partner_name: string;
  amount_kgs: number;
  hotel_commission_kgs: number;
  partner_net_kgs: number;
  commission_bps: number;
  status: string;
  description?: string | null;
  booking_number: string;
  guest_name?: string | null;
  created_at: string;
};

const fmt = (value: number) => new Intl.NumberFormat("ru-RU").format(value || 0) + " сом";
const todayIso = () => new Date().toISOString().slice(0, 10);
const monthStartIso = () => {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1, 12).toISOString().slice(0, 10);
};

export default function NfcFinanceBoard() {
  const [start, setStart] = useState(monthStartIso());
  const [end, setEnd] = useState(todayIso());
  const [partnerId, setPartnerId] = useState("");
  const [totals, setTotals] = useState<Totals>({ transaction_count: 0, completed_count: 0, reversed_count: 0, gross_kgs: 0, hotel_commission_kgs: 0, partner_net_kgs: 0 });
  const [partners, setPartners] = useState<PartnerSummary[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    if (partnerId) params.set("partner_id", partnerId);
    params.set("limit", "500");
    return params.toString();
  }, [start, end, partnerId]);

  const periodQuery = useMemo(() => {
    const params = new URLSearchParams();
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    return params.toString();
  }, [start, end]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [txResponse, partnerResponse] = await Promise.all([
        fetch(`/core/api/v1/admin/nfc/transactions?${query}`, { cache: "no-store" }),
        fetch(`/core/api/v1/admin/nfc/partners/summary?${periodQuery}`, { cache: "no-store" }),
      ]);
      const txBody = await txResponse.json().catch(() => ({}));
      const partnerBody = await partnerResponse.json().catch(() => ({}));
      if (!txResponse.ok) throw new Error(txBody.detail || "Не удалось загрузить NFC-транзакции");
      if (!partnerResponse.ok) throw new Error(partnerBody.detail || "Не удалось загрузить отчёт по партнёрам");
      setTotals(txBody.totals || {});
      setTransactions(txBody.items || []);
      setPartners(partnerBody.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки NFC-финансов");
    } finally {
      setLoading(false);
    }
  }, [query, periodQuery]);

  useEffect(() => { load(); }, [load]);

  return (
    <main className="work-shell nfc-finance-shell">
      <div className="work-head">
        <div><p className="eyebrow">NFC · контроль денег</p><h1>Финансы NFC</h1><p className="subtitle">Оборот пляжных партнёров, комиссия отеля и журнал всех списаний.</p></div>
        <div className="work-actions finance-filters">
          <label><span>С</span><input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
          <label><span>По</span><input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
          <label><span>Партнёр</span><select value={partnerId} onChange={(e) => setPartnerId(e.target.value)}><option value="">Все</option>{partners.map((partner) => <option key={partner.partner_id} value={partner.partner_id}>{partner.partner_name}</option>)}</select></label>
          <button className="btn" onClick={load}>Обновить</button>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      <section className="finance-kpis">
        <article><span>Оборот</span><strong>{fmt(totals.gross_kgs)}</strong><small>{totals.completed_count || 0} успешных операций</small></article>
        <article><span>Комиссия отеля</span><strong>{fmt(totals.hotel_commission_kgs)}</strong><small>Фактически записано в транзакциях</small></article>
        <article><span>Партнёрам</span><strong>{fmt(totals.partner_net_kgs)}</strong><small>После комиссии отеля</small></article>
        <article><span>Reversed</span><strong>{totals.reversed_count || 0}</strong><small>Отдельно от completed-оборота</small></article>
      </section>

      <section className="finance-section">
        <div className="section-head"><div><p className="eyebrow">Сверка</p><h2>Пляжные партнёры</h2></div></div>
        {loading ? <div className="loading">Считаю оборот…</div> : <div className="partner-finance-grid">
          {partners.length === 0 && <div className="empty">Операций за выбранный период нет.</div>}
          {partners.map((partner) => <article key={partner.partner_id} className={`partner-finance-card ${partnerId === partner.partner_id ? "selected" : ""}`} onClick={() => setPartnerId(partnerId === partner.partner_id ? "" : partner.partner_id)}>
            <div><strong>{partner.partner_name}</strong><span>@{partner.username}</span></div>
            <dl><div><dt>Оборот</dt><dd>{fmt(partner.gross_kgs)}</dd></div><div><dt>Отелю</dt><dd>{fmt(partner.hotel_commission_kgs)}</dd></div><div><dt>Партнёру</dt><dd>{fmt(partner.partner_net_kgs)}</dd></div><div><dt>Операций</dt><dd>{partner.completed_count}</dd></div></dl>
          </article>)}
        </div>}
      </section>

      <section className="finance-section">
        <div className="section-head"><div><p className="eyebrow">Ledger view</p><h2>Последние списания</h2></div><span>{transactions.length} записей</span></div>
        {loading ? <div className="loading">Загружаю транзакции…</div> : <div className="transaction-table-wrap"><table className="transaction-table"><thead><tr><th>Время</th><th>Партнёр</th><th>Бронь</th><th>Услуга</th><th>Сумма</th><th>Отелю</th><th>Партнёру</th><th>Статус</th></tr></thead><tbody>
          {transactions.map((tx) => <tr key={tx.id}><td>{new Date(tx.created_at).toLocaleString("ru-RU")}</td><td>{tx.partner_name}</td><td>{tx.booking_number}{tx.guest_name ? <small>{tx.guest_name}</small> : null}</td><td>{tx.description || "—"}</td><td><b>{fmt(tx.amount_kgs)}</b></td><td>{fmt(tx.hotel_commission_kgs)}</td><td>{fmt(tx.partner_net_kgs)}</td><td><span className={`tx-status ${tx.status}`}>{tx.status}</span></td></tr>)}
          {transactions.length === 0 && <tr><td colSpan={8} className="empty">Транзакций нет.</td></tr>}
        </tbody></table></div>}
      </section>
    </main>
  );
}
