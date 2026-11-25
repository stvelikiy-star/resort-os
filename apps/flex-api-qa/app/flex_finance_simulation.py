"""Pure, explicitly synthetic FLEX cash exercise. No DB or provider writes."""
from decimal import Decimal
from .flex_foundation import InvoiceBalance, allocate_confirmed_payment, money

ZERO=Decimal("0.00")


def simulate_cash(subscription, implementation, events):
    """Replay ordered synthetic receipts/refunds against a non-fiscal quote.

    Each refund references its original simulated receipt. Consume its credit
    first, then reverse its own allocations in reverse order. No implicit
    redistribution of other receipts. CREDIT_APPLY explicitly reallocates existing
    receipt credit, without changing simulated cash. This is not a real settlement writer.
    """
    charges={"subscription":money(subscription),"implementation":money(implementation)}
    if any(v<ZERO for v in charges.values()) or sum(charges.values())<=ZERO:
        raise ValueError("Invalid synthetic charges")
    if len(events)>100:
        raise ValueError("Too many synthetic events")
    due=charges.copy()
    receipts={}
    seen=set()
    history=[]
    for event in events:
        kind=event["kind"]
        key=event["event_id"]
        raw=Decimal(event["amount"])
        amount=money(raw)
        if not key or key in seen or amount<=ZERO or raw!=amount:
            raise ValueError("Duplicate event or invalid minor units")
        seen.add(key)
        if kind=="PAYMENT":
            if event.get("payment_id") is not None:
                raise ValueError("Payment must not reference another receipt")
            plan=allocate_confirmed_payment(amount,tuple(InvoiceBalance(k,v) for k,v in due.items()))
            allocations={k:ZERO for k in charges}
            for a in plan.allocations:
                due[a.line_id]-=a.amount
                allocations[a.line_id]=a.amount
            receipts[key]={"remaining":amount,"credit":plan.unallocated_credit,"allocations":allocations}
        elif kind=="CREDIT_APPLY":
            receipt=receipts.get(event.get("payment_id"))
            if receipt is None or amount>receipt["credit"] or amount>sum(due.values(),ZERO):
                raise ValueError("Credit application exceeds available receipt credit or outstanding balance")
            plan=allocate_confirmed_payment(amount,tuple(InvoiceBalance(k,v) for k,v in due.items()))
            if plan.unallocated_credit!=ZERO:
                raise ValueError("Credit application conservation failure")
            receipt["credit"]-=amount
            for a in plan.allocations:
                due[a.line_id]-=a.amount
                receipt["allocations"][a.line_id]+=a.amount
        elif kind=="REFUND":
            receipt=receipts.get(event.get("payment_id"))
            if receipt is None or amount>receipt["remaining"]:
                raise ValueError("Refund exceeds original synthetic receipt")
            receipt["remaining"]-=amount
            credit=min(amount,receipt["credit"])
            receipt["credit"]-=credit
            left=amount-credit
            for k in reversed(tuple(charges)):
                value=min(left,receipt["allocations"][k])
                receipt["allocations"][k]-=value
                due[k]+=value
                left-=value
            if left!=ZERO:
                raise ValueError("Synthetic refund conservation failure")
        else:
            raise ValueError("Unknown synthetic event")
        cash=sum((r["remaining"] for r in receipts.values()),ZERO)
        credit=sum((r["credit"] for r in receipts.values()),ZERO)
        total=sum(charges.values(),ZERO)
        outstanding=sum(due.values(),ZERO)
        applied=total-outstanding
        if cash!=applied+credit or any(due[k]<ZERO or due[k]>charges[k] for k in due):
            raise ValueError("Synthetic reconciliation failed")
        history.append({"event_id":key,"kind":kind,"amount":str(amount),
            "cash":str(cash),"applied":str(applied),"outstanding":str(outstanding),"credit":str(credit)})
    return {"mode":"SYNTHETIC_ONLY","currency":"KGS","amount_before_unresolved_taxes":str(sum(charges.values(),ZERO)),
        "net_simulated_cash":str(sum((r["remaining"] for r in receipts.values()),ZERO)),
        "outstanding":str(sum(due.values(),ZERO)),
        "credit":str(sum((r["credit"] for r in receipts.values()),ZERO)),
        "subscription_outstanding":str(due["subscription"]),
        "history":history,"discrepancy":"0.00","payments_enabled":False,
        "subscription_activated":False,"launch_offer_finalized":False}
