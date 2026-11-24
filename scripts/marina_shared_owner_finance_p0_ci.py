# Synthetic two-hotel finances only. Never run against customer/QA/Production DB.
import os
from urllib.parse import urlsplit
dsn = urlsplit(os.environ.get("DATABASE_URL", "").split("?", 1)[0])
if not (
    os.environ.get("MARINA_SHARED_FINANCE_P0_CI_CONFIRM") == "ISOLATED_OWNER_FINANCE_CI_ONLY"
    and os.environ.get("MARINA_SHARED_BROWSER_CI_CONFIRM") == "DISPOSABLE_TWO_HOTEL_BROWSER_CI"
    and os.environ.get("APP_ENV") == "staging"
    and os.environ.get("MARINA_SHARED_AUTH_PREVIEW_ENABLED") == "true"
    and os.environ.get("PROPERTY_CODE") == "MARINA_BROWSER_CI"
    and os.environ.get("MARINA_TENANT_CONTEXT_ENABLED") == "true"
    and os.environ.get("MARINA_SHARED_BROWSER_CI_PASSWORD", "").startswith("synthetic-ci-only-")
    and dsn.hostname in ("127.0.0.1", "localhost")
    and dsn.path == "/marina_shared_browser_ci"
):
    raise SystemExit("Refusing non-disposable finance fixture database")

from fastapi.testclient import TestClient
from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD
from datetime import date
from uuid import uuid4
n=0
def check(result,want,label):
 global n
 assert result==want,(label,result,want)
 n+=1
day=date.today().isoformat()
url="/api/v1/admin/finance/owner/expenses"
expense_ids={}
with TestClient(app,base_url="https://isolated-staging.local") as c:
 def login(code,role):
  r=c.post("/api/v1/auth/login",json={"username":role.lower(),"password":PASSWORD,"tenant_code":"tenant_"+code.lower(),"property_code":"HOTEL_"+code})
  check(r.status_code,200,"login "+code+role)
  return r.json()
 for code in ("A","B"):
  other="B" if code=="A" else "A"
  login(code,"OWNER")
  initial=c.get(url,params={"from_date":day,"to_date":day})
  check(initial.status_code,200,"initial expenses")
  assert initial.json()["totals"]["posted_expenses_kgs"]==0
  exp_id=str(uuid4());expense_ids[code]=exp_id
  expense={"id":exp_id,"expense_date":day,"category":"SUPPLIES","title":"QA synthetic hotel "+code,"amount_kgs":1200 if code=="A" else 2300}
  posted=c.post(url,json=expense)
  check(posted.status_code,201,"post expense "+posted.text[:160])
  check(posted.json()["payment_created"],False,"no automatic payment")
  replay=c.post(url,json=expense)
  check(replay.status_code,201,"expense replay")
  check(replay.json()["already_processed"],True,"expense idempotency")
  listed=c.get(url,params={"from_date":day,"to_date":day})
  check(listed.status_code,200,"expense listing")
  total=expense["amount_kgs"]
  check(listed.json()["totals"]["posted_expenses_kgs"],total,"own expense total")
  assert len(listed.json()["items"])==1
  settlement={"id":str(uuid4()),"amount_kgs":400,"paid_on":day,"method":"CASH"}
  paid=c.post(url+"/"+exp_id+"/settlements",json=settlement)
  check(paid.status_code,201,"manual expense settlement "+paid.text[:170])
  check(paid.json()["payment_created"],False,"manual expense not income payment")
  duplicate=c.post(url+"/"+exp_id+"/settlements",json=settlement)
  check(duplicate.status_code,201,"settlement replay")
  check(duplicate.json()["already_processed"],True,"settlement idempotency")
  over=c.post(url+"/"+exp_id+"/settlements",json={**settlement,"id":str(uuid4()),"amount_kgs":total})
  check(over.status_code,409,"block over settlement")
  after=c.get(url,params={"from_date":day,"to_date":day}).json()
  check(after["totals"]["settled_against_period_expenses_kgs"],400,"settlement total")
  check(after["totals"]["outstanding_kgs"],total-400,"outstanding expense")
  audit=c.get("/api/v1/admin/finance/owner/accrual-readiness",params={"from_date":day,"to_date":day})
  check(audit.status_code,200,"accrual readiness")
  assert audit.json()["recognition"]["recognized_profit_kgs"] is None
  n+=1
  cash=c.get("/api/v1/admin/finance/owner/recorded-cash-movements",params={"from_date":day,"to_date":day})
  check(cash.status_code,200,"cash reconciliation read")
  check(c.post(url+"/"+exp_id+"/void",json={"reason":"Cannot void settled expense"}).status_code,409,"settled expense cannot void")
  c.post("/api/v1/auth/logout")
 for code in ("A","B"):
  other="B" if code=="A" else "A"
  login(code,"OWNER")
  foreign=c.post(url+"/"+expense_ids[other]+"/settlements",json={"id":str(uuid4()),"amount_kgs":1,"paid_on":day,"method":"CASH"})
  check(foreign.status_code,404,"foreign expense settlement blocked")
  own=c.get(url,params={"from_date":day,"to_date":day})
  check(own.status_code,200,"own expense read")
  assert len(own.json()["items"])==1 and own.json()["items"][0]["id"]==expense_ids[code]
  n+=1
  c.post("/api/v1/auth/logout")
 for role in ("RECEPTION","COOK","STORE_STAFF"):
  login("A",role)
  check(c.get(url,params={"from_date":day,"to_date":day}).status_code,403,role+" owner read denied")
  check(c.post(url,json={"id":str(uuid4()),"expense_date":day,"category":"OTHER","title":"Forbidden","amount_kgs":1}).status_code,403,role+" owner write denied")
  c.post("/api/v1/auth/logout")
print("REAL_TWO_HOTEL_OWNER_EXPENSES_PASS",n)