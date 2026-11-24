"""Chromium acceptance of template publishing and reuse with isolated HTTP fixtures."""
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from shutil import which

root = Path(__file__).resolve().parents[1] / 'apps/flex-console/public'
a, b, t = ['00000000-0000-4000-8000-00000000000' + x for x in ('a', 'b', 'c')]
for width, lang in [(390, 'ru'), (820, 'kg'), (1440, 'en')]:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=which('google-chrome') or which('chromium'), args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': width, 'height': 900})
        page.set_default_timeout(10000)
        errors = []
        published = []
        saves = []
        page.on('pageerror', lambda e: errors.append(str(e)))

        def route(r):
            path = urlsplit(r.request.url).path
            if not path.startswith('/api/'):
                f = root / (path.strip('/') or 'index.html')
                if f.is_file():
                    return r.fulfill(path=str(f))
                return r.fulfill(status=404)
            data = []
            if path == '/api/status':
                data = dict(configured=True, qa_catalog_admin_enabled=True)
            if path.endswith('/v1/me'):
                data = {'role': 'SUPER_ADMIN'}
            if path.endswith('/v1/hotels'):
                data = [dict(id=i, name=n, status='PENDING', currency='KGS') for i, n in [(a, 'Alpha'), (b, 'Beta')]]
            if path.endswith('/subscription'):
                data = None
            if path.endswith('/partner-earnings-summary'):
                data = {'groups': []}
            if path.endswith('/platform/catalog'):
                data = [dict(sku='QA_ADDON', name='QA', status='AVAILABLE', is_core=False, latest_price=dict(currency='KGS', monthly_price='1200.00', valid_from='2020-01-01T00:00:00Z'))]
            if path.endswith('/platform/tariff-packages') and a in r.request.url:
                data = [dict(id=t, package_kind='BUSINESS', version=1, title='Alpha private', discount_pct='20', trial_days=7, proposed_monthly_total='960', currency='KGS', state='DRAFT')]
            if path == '/api/session':
                data = {'csrf': 'fixture'}
            if path == '/api/actions/tariff-templates':
                assert r.request.post_data_json == {'package_id': t}
                published.append(dict(id=t, revision=1, package_kind='BUSINESS', skus=['QA_ADDON']))
                data = published[0]
            if path.endswith('/platform/tariff-templates'):
                data = published
            if path == '/api/actions/tariff-packages':
                saves.append(r.request.post_data_json)
                data = dict(state='DRAFT', enforcement='OFF', subscription_activated=False)
            return r.fulfill(json=data) if data is not None else r.fulfill(body='null', content_type='application/json')
        page.route('**/*', route)
        page.goto('http://flex.test/')
        page.locator('[data-hotel="' + a + '"]').first.wait_for()
        page.locator('#lang').select_option(lang)
        page.locator('[data-hotel="' + a + '"]').first.click()
        page.locator('[data-hotel-tab="subscription"]').click()
        page.locator('[data-publish-template]').click()
        page.locator('#nav [data-view="hotels"]').click()
        page.locator('[data-hotel="' + b + '"]').first.click()
        page.locator('[data-hotel-tab="subscription"]').click()
        page.locator('[data-view="subscription-draft"]').click()
        selector = page.locator('[name="source_template_id"]')
        selector.select_option(t)
        assert page.locator('[name="package_kind"]').input_value() == 'BUSINESS'
        box = page.locator('[name="skus"]')
        assert box.is_checked()
        box.uncheck()
        assert selector.input_value() == ''
        selector.select_option(t)
        page.locator('[data-package-save]').click()
        page.wait_for_function("document.getElementById('admin-action-status').textContent.length>0")
        assert len(saves) == 1 and saves[0]['hotel_id'] == b and (saves[0]['source_template_id'] == t) and (saves[0]['discount_pct'] == '0') and (saves[0]['trial_days'] == 0) and (saves[0]['skus'] == ['QA_ADDON'])
        assert not errors, errors
        print('PASS', width, lang, flush=True)
        browser.close()
