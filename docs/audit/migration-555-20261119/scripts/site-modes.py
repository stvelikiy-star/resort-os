"""Exercise old publication format, unpublished locale and explicit customer publication."""
import json,sys
from pathlib import Path
import httpx
mode=sys.argv[1]
port=18001 if mode=='old' else 18002
with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as c:
    out=[]
    def fetch(method,path,**kw):
        r=c.request(method,path,**kw)
        out.append({'method':method,'path':path,'status':r.status_code,'body':r.text[:24000]})
        return r
    for lang in ('ru','en'):
        fetch('GET','/api/v1/site/content?locale='+lang)
        if mode=='customer':
            fetch('GET','/api/v1/site/customer-page?locale='+lang)
    if mode=='customer':
        c.post('/api/v1/auth/login',json={'username':'owner','password':'Synthetic-audit-only-2026!'}).raise_for_status()
        content={'hero':{'title':'Synthetic ALPHA','subtitle':'Synthetic hotel'},'contacts':{'phone':'+12025550100','whatsapp':'+12025550100','email':'alpha@example.invalid','address':'Synthetic ALPHA address'},'seo':{'title':'Synthetic ALPHA','description':'Synthetic hotel'}}
        fetch('PUT','/api/v1/admin/site/content/en/draft',json={'content':content})
        fetch('POST','/api/v1/admin/site/content/en/publish')
        fetch('GET','/api/v1/site/content?locale=en')
        fetch('GET','/api/v1/site/customer-page?locale=en')
    Path('evidence/site-'+mode+'.json').write_text(json.dumps(out,ensure_ascii=False,indent=1))
