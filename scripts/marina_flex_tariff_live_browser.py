"""One browser login -> two hotel offers -> independent read of the same QA DB."""
import base64
import hashlib
import hmac
import json
import os
import subprocess
import time
from shutil import which
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import expect, sync_playwright

ORIGIN = "https://127.0.0.1:3443"
HOTEL_A = "00000000-0000-0000-0000-00000000000a"
HOTEL_B = "00000000-0000-0000-0000-00000000000b"


def totp(secret):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    counter = int(time.time() // 30).to_bytes(8, "big")
    digest = hmac.new(key, counter, hashlib.sha1).digest()
    offset = digest[-1] & 15
    value = int.from_bytes(digest[offset:offset + 4], "big") & 0x7fffffff
    return f"{value % 1000000:06d}"


def enroll(browser):
    context = browser.new_context()
    page = context.new_page()
    page.goto(ORIGIN)
    expect(page.locator("#flex-identity-signin")).to_be_visible()

    def post(path, body):
        reply = page.evaluate("""async ([path, body]) => {
          const response = await fetch('/api/identity/' + path, {
            method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
          });
          return {status:response.status, data:await response.json()};
        }""", [path, body])
        assert reply["status"] == 200, (path, reply["status"], reply["data"].get("code"))
        return reply["data"]

    password = os.environ["QA_PASSWORD"]
    post("sign-in/email", {"email": os.environ["QA_EMAIL"], "password": password})
    setup = post("two-factor/enable", {"password": password})
    secret = parse_qs(urlsplit(setup["totpURI"]).query)["secret"][0]
    post("two-factor/verify-totp", {"code": totp(secret), "trustDevice": False})
    assert not any(c["name"] == "flex_session" for c in context.cookies())
    post("sign-out", {})
    context.close()
    return secret


def open_card(page, hotel):
    page.locator('#nav [data-view="hotels"]').click()
    page.locator(f'[data-hotel="{hotel}"]').click()
    page.locator('[data-hotel-tab="subscription"]').click()
    expect(page.locator('[data-view="subscription-draft"]')).to_be_visible()


def save_offer(page, hotel, discount, title, template=None):
    open_card(page, hotel)
    page.locator('[data-view="subscription-draft"]').click()
    form = page.locator("#subscription-draft-form")
    if template:
        form.locator('[name="source_template_id"]').select_option(template)
        expect(form.locator('[name="package_kind"]')).to_have_value("BUSINESS")
        expect(form.locator('[value="TARIFF_E2E"]')).to_be_checked()
        expect(form.locator('[name="discount_pct"]')).to_have_value("0")
    else:
        form.locator('[name="package_kind"]').select_option("BUSINESS")
        form.locator('[value="TARIFF_E2E"]').check()
    form.locator('[name="title"]').fill(title)
    form.locator('[name="discount_pct"]').fill(str(discount))
    with page.expect_response(ORIGIN + "/api/actions/tariff-packages") as submitted:
        form.locator('[data-package-save]').click()
    response = submitted.value
    assert response.status == 201, ("save", response.status, response.text()[:250])
    offer = response.json()
    assert offer["hotel_id"] == hotel and offer["source_template_id"] == template
    assert offer["state"] == "DRAFT" and offer["enforcement"] == "OFF"
    return offer["id"]


def pg_rows():
    query = """
      SELECT json_agg(row_to_json(offers) ORDER BY hotel_id) FROM (
        SELECT p.id,p.hotel_id,p.version,p.discount_pct::text,p.proposed_monthly_total::text AS total,
               p.state,p.enforcement,p.source_template_id,t.revision AS template_revision,
               p.sku_snapshot->0->>'sku' AS sku
        FROM flex_private.flex_tariff_package_versions p
        LEFT JOIN flex_private.flex_tariff_templates t ON t.id=p.source_template_id
      ) offers
    """
    return json.loads(subprocess.check_output(["psql","-XAt","-v","ON_ERROR_STOP=1","-c",query],text=True))


def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=which("google-chrome") or which("chromium"),
            args=["--ignore-certificate-errors-spki-list=" + os.environ["QA_TLS_PIN"]])
        secret = enroll(browser)
        context = browser.new_context()
        page = context.new_page()
        page.goto(ORIGIN)
        signin = page.locator("#flex-identity-signin")
        signin.locator('[name="email"]').fill(os.environ["QA_EMAIL"])
        signin.locator('[name="password"]').fill(os.environ["QA_PASSWORD"])
        signin.locator('button[type="submit"]').click()
        challenge = page.locator("#flex-identity-totp")
        challenge.locator('[name="code"]').fill(totp(secret))
        challenge.locator('button[type="submit"]').click()
        expect(page.locator(f'[data-hotel="{HOTEL_A}"]')).to_be_visible(timeout=15000)
        me = page.evaluate("async () => (await fetch('/api/data/v1/me')).json()")
        assert me["role"] == "SUPER_ADMIN"
        page.locator("#lang").select_option("en")
        first = save_offer(page, HOTEL_A, 10, "QA Alpha")
        open_card(page, HOTEL_A)
        with page.expect_response(ORIGIN + "/api/actions/tariff-templates") as published:
            page.locator(f'[data-publish-template="{first}"]').click()
        assert published.value.status == 201
        template = published.value.json()
        assert template["id"] == first and template["revision"] == 1
        second = save_offer(page, HOTEL_B, 25, "QA Beta", template["id"])
        page.reload()
        for hotel, title, discount, total in [
            (HOTEL_A,"QA Alpha","10.00%","3,600 KGS"), (HOTEL_B,"QA Beta","25.00%","3,000 KGS")
        ]:
            open_card(page, hotel)
            row = page.locator("tr").filter(has_text=title)
            for value in ["BUSINESS", "v1", discount, total, "DRAFT"]:
                expect(row).to_contain_text(value)
            expect(page.locator("tr").filter(has_text="QA Beta" if hotel == HOTEL_A else "QA Alpha")).to_have_count(0)
        rows = pg_rows()
        assert len(rows) == 2
        for row, ident, hotel, pct, total, source in [
            (rows[0], first, HOTEL_A, "10.00", "3600.00", None),
            (rows[1], second, HOTEL_B, "25.00", "3000.00", first)
        ]:
            assert (row["id"],row["hotel_id"],row["version"],row["discount_pct"],row["total"],
                    row["source_template_id"],row["template_revision"],row["sku"],row["state"],row["enforcement"]) == (
                    ident,hotel,1,pct,total,source,1 if source else None,"TARIFF_E2E","DRAFT","OFF")
        print("PASS real SUPER_ADMIN password/TOTP login, catalog and shared template revision 1")
        print("PASS reopened hotel A v1 10% = 3600.00 KGS; hotel B v1 25% = 3000.00 KGS; both match PostgreSQL")
        browser.close()


if __name__ == "__main__":
    run()
