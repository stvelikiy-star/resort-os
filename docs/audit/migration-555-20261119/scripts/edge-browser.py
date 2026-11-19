import json
from pathlib import Path
from playwright.sync_api import sync_playwright
out=[]
with sync_playwright() as pw:
    for label,base,path in [('old-rooms',18101,'/rooms'),('customer-ru',18200,'/'),('customer-en',18200,'/?locale=en'),('customer-rooms',18200,'/rooms'),('customer-unpublished',18200,'/?locale=kg')]:
        b=pw.chromium.launch(executable_path=str(Path('runtime/headless/usr/lib/chromium/chromium-headless-shell').resolve()),args=['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process'])
        page=b.new_page()
        page.route('**/*',lambda r:r.continue_() if r.request.url.startswith('http://127.0.0.1:') else r.abort())
        resp=page.goto(f'http://127.0.0.1:{base}'+path,wait_until='domcontentloaded',timeout=90000)
        body=page.locator('body').inner_text()
        out.append([label,resp.status,page.title(),body[:240]])
        page.screenshot(path=f'evidence/edge-{label}.png')
        Path('evidence/edge.json').write_text(json.dumps(out,ensure_ascii=False,indent=1))
        b.close()
