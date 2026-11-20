"""Collect normal read operations on two fixed localhost APIs. Writes are only inventoried."""
import csv,json
from datetime import date,timedelta
from pathlib import Path
import httpx

def collect():
    rows=[]
    identities={}
    for v,port in [('old',18001),('new',18002)]:
        routes=json.load(open(f'evidence/openapi-{v}.json'))['paths']
        for role in ['DINING_STAFF','RECEPTION','OWNER','MANAGER','MAID','TECHNICIAN','STORE_STAFF','CONTENT_MANAGER','BEACH_PARTNER','COOK','WAITER','AGENT','anonymous']:
            with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=10) as c:
                present=not(v=='old' and role in ['COOK','WAITER','AGENT'])
                if present and role!='anonymous':
                    r=c.post('/api/v1/auth/login',json={'username':role.lower(),'password':'Synthetic-audit-only-2026!'})
                    r.raise_for_status()
                    identities[v+'-'+role]=r.json()
                for path,ops in routes.items():
                    for method,op in ops.items():
                        status='NOT VERIFIED'
                        params={}
                        if not present:
                            status='ROLE ABSENT'
                        elif method=='get' and '{' not in path and not any(part in path for part in ['/automation/','/public/ai','/channels/','/whatsapp','/holds','/integrations/','/export','/payments/','/customer-page']):
                            required=[p['name'] for p in op.get('parameters',[]) if p.get('required')]
                            dates={'start':date.today(),'end':date.today()+timedelta(days=2),'check_in':date.today(),'check_out':date.today()+timedelta(days=2),'adults':2}
                            if set(required)<=dates.keys():
                                params={key:str(dates[key]) for key in required}
                                status=c.get(path,params=params).status_code
                        rows.append([v,role,method,path,status])
    with open('evidence/rights.csv','w') as f:
        out=csv.writer(f);out.writerow(['version','role','method','path','http_or_coverage']);out.writerows(rows)
    Path('evidence/identities.json').write_text(json.dumps(identities,indent=2))
if __name__=='__main__':
    collect()
