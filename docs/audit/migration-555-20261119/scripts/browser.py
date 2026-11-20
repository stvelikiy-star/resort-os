from pathlib import Path
from urllib.parse import urlsplit
import json
from playwright.sync_api import sync_playwright
from httpx import Client
tests=[('old',18102,'dining_staff','/'),('new',18105,'dining_staff','/'),('old',18103,'reception','/'),('new',18106,'reception','/'),('old',18101,None,'/'),('new',18104,None,'/'),('new',18104,None,'/guest')]
out=[]
with sync_playwright() as pw:
    for v,p,role,path in tests:
        browser=pw.chromium.launch(executable_path=str(Path('runtime/headless/usr/lib/chromium/chromium-headless-shell').resolve()),args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--no-zygote','--single-process'])
        label=f'{v}-{p}-{role or "public"}-{path.strip("/") or "root"}'
        ctx=browser.new_context(viewport={'width':1440,'height':900})
        ctx.route('**/*',lambda route: route.continue_() if urlsplit(route.request.url).hostname in ['127.0.0.1','localhost'] else route.abort())
        try:
            if role:
                with Client(trust_env=False) as c:
                    auth=c.post(f'http://127.0.0.1:{18001 if v=="old" else 18002}/api/v1/auth/login',json={'username':role,'password':'Synthetic-audit-only-2026!'})
                    auth.raise_for_status()
                    ctx.add_cookies([{'name':'resort_session','value':c.cookies['resort_session'],'url':f'http://127.0.0.1:{p}'}])
            page=ctx.new_page()
            response=page.goto(f'http://127.0.0.1:{p}'+path,wait_until='domcontentloaded',timeout=120000)
            if role:
                try: page.get_by_text('Выйти',exact=True).first.wait_for(timeout=18000)
                except Exception: pass
            page.wait_for_timeout(1400)
            body=page.locator('body').inner_text()
            Path('evidence/'+label+'.txt').write_text(body)
            page.screenshot(path='evidence/'+label+'.png')
            out.append([label,response.status,page.title(),len(body),page.locator('a[href="/kitchen"]').count()])
        except Exception as ex: out.append([label,'NOT VERIFIED',str(ex)[:350]])
        ctx.close()
        Path('evidence/browser.json').write_text(json.dumps(out,ensure_ascii=False,indent=1))
        browser.close()
