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


def enroll(browser, email=None, password=None):
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

    password = password or os.environ["QA_PASSWORD"]
    post("sign-in/email", {"email": email or os.environ["QA_EMAIL"], "password": password})
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
        with page.expect_response(ORIGIN + "/api/identity/two-factor/verify-totp") as verified:
            challenge.locator('button[type="submit"]').click()
        # Successful login immediately navigates away. Check the cookie and server-side
        # role in the new document instead of reading the discarded response body.
        assert verified.value.status == 200, ("login challenge", verified.value.status)
        assert any(c["name"] == "flex_session" for c in context.cookies()), "Missing platform session cookie"
        for path in ["/api/data/v1/me", "/api/data/v1/hotels"]:
            status = page.request.get(ORIGIN + path, ignore_https_errors=True)
            assert status.status == 200, (path, status.status, status.text()[:200])
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
        open_card(page, HOTEL_A)
        form=page.locator("#hotel-commercial-offer")
        expect(form).to_be_visible()
        form.locator('[name="package_kind"]').select_option("BASE")
        form.locator('[name="term_months"]').select_option("12")
        form.locator('[name="launch_offer"]').check()
        form.locator('[name="include_implementation"]').check()
        with page.expect_response(ORIGIN+"/api/actions/tariff-packages") as submitted:
            form.locator('button[type="submit"]').click()
        response=submitted.value
        assert response.status==201, ("launch offer",response.status,response.text()[:250])
        launch=response.json()
        from decimal import Decimal
        assert Decimal(str(launch["subscription_term_total"]))==Decimal("36000")
        assert Decimal(str(launch["implementation_total"]))==Decimal("25000")
        assert launch["launch_offer_slot"]==1
        assert launch["launch_offer_reserved"] and not launch["payments_enabled"] and not launch["subscription_activated"]
        # Navigation waits for the saved card to finish rendering.
        expect(page.locator("#hotel-commercial-offer")).to_be_visible()
        stats=page.request.get(ORIGIN+"/api/data/v1/platform/launch-offer",ignore_https_errors=True)
        assert stats.status==200, ("launch stats",stats.status)
        data=stats.json()
        assert (data["capacity"],data["reserved"],data["available"])==(50,1,49)
        assert data["reservations"][0]["offer_id"]==launch["id"]
        page.locator('#nav [data-view="catalog"]').click()
        panel=page.locator("section.panel").filter(has=page.get_by_role("heading",name="Launch offer",exact=True))
        expect(panel).to_contain_text("1 / 50")
        expect(panel).to_contain_text("49")
        expect(panel.locator("tr").filter(has_text="BASE")).to_contain_text("36,000 KGS")
        expect(panel.locator("tr").filter(has_text="BASE")).to_contain_text("25,000 KGS")
        query="""SELECT json_build_object('slot',r.slot,'hotel',r.hotel_id,'offer',r.offer_id,
            'total',p.subscription_term_total,'implementation',p.implementation_total,
            'payments',(SELECT count(*) FROM flex_private.flex_confirmed_payments))
            FROM flex_private.flex_launch_offer_reservations r
            JOIN flex_private.flex_tariff_package_versions p ON p.id=r.offer_id"""
        saved=json.loads(subprocess.check_output(["psql","-XAt","-v","ON_ERROR_STOP=1","-c",query],text=True))
        assert saved=={"slot":1,"hotel":HOTEL_A,"offer":launch["id"],"total":36000,"implementation":25000,"payments":0},saved
        print("PASS browser launch offer BASE 36000 + setup 25000, capacity 1/50, independent PostgreSQL match")
        page.locator('#nav [data-view="hotels"]').click()
        page.locator(f'[data-hotel="{HOTEL_A}"]').click()
        page.locator('[data-hotel-tab="overview"]').click()
        profile=page.locator("#customer-profile-form")
        expect(profile).to_be_visible()
        profile.locator('[name="contact_name"]').fill("Synthetic hotel contact")
        profile.locator('[name="contact_email"]').fill("contact@example.test")
        profile.locator('[name="contact_phone"]').fill("+996000000000")
        profile.locator('[name="responsible_name"]').fill("Synthetic manager")
        with page.expect_response(ORIGIN+"/api/actions/customer-profile") as submitted:
            profile.locator('button[type="submit"]').click()
        assert submitted.value.status==201, ("profile",submitted.value.status,submitted.value.text()[:250])
        expect(profile.locator('[name="expected_version"]')).to_have_value("1")
        profile.locator('[name="contact_name"]').fill("Updated synthetic contact")
        with page.expect_response(ORIGIN+"/api/actions/customer-profile") as submitted:
            profile.locator('button[type="submit"]').click()
        assert submitted.value.status==201
        expect(profile.locator('[name="expected_version"]')).to_have_value("2")
        page.locator('[data-hotel-tab="history"]').click()
        expect(page.get_by_role("heading",name="Contact history",exact=True)).to_be_visible()
        expect(page.get_by_text("Updated synthetic contact",exact=True)).to_be_visible()
        expect(page.get_by_text("Synthetic hotel contact",exact=True)).to_be_visible()
        agreement=page.locator("#agreement-draft-form")
        agreement.locator('[name="offer_id"]').select_option(launch["id"])
        with page.expect_response(ORIGIN+"/api/actions/agreement-drafts") as submitted:
            agreement.locator('button[type="submit"]').click()
        response=submitted.value
        assert response.status==201, ("agreement",response.status,response.text()[:250])
        contract=response.json()
        assert contract["state"]=="DRAFT" and contract["source_offer_id"]==launch["id"]
        preview=page.locator(".invoice-preview-form")
        with page.expect_response(ORIGIN+"/api/actions/invoice-previews") as submitted:
            preview.locator('button[type="submit"]').click()
        response=submitted.value
        assert response.status==201, ("preview",response.status,response.text()[:250])
        doc=response.json()
        assert doc["status"]=="NON_ISSUABLE" and Decimal(str(doc["amount_before_unresolved_taxes"]))==Decimal("61000")
        expect(page.locator("tr").filter(has_text="NON_ISSUABLE")).to_contain_text("61,000 KGS")
        query="""SELECT json_build_object('profiles',(SELECT count(*) FROM flex_private.flex_hotel_profile_versions),
          'agreement',a.id,'source',a.source_offer_id,'state',a.state,'preview',p.id,
          'amount',p.amount_before_unresolved_taxes,'payments',(SELECT count(*) FROM flex_private.flex_confirmed_payments))
          FROM flex_private.flex_commercial_agreement_versions a JOIN flex_private.flex_non_issuable_invoice_previews p ON p.agreement_version_id=a.id"""
        saved=json.loads(subprocess.check_output(["psql","-XAt","-v","ON_ERROR_STOP=1","-c",query],text=True))
        assert saved=={"profiles":2,"agreement":contract["id"],"source":launch["id"],"state":"DRAFT","preview":doc["id"],"amount":61000,"payments":0},saved
        print("PASS browser customer profile revisions, unsigned agreement and non-issuable 61000 KGS preview match PostgreSQL")
        page.locator('[data-hotel-tab="finance"]').click()
        panel=page.locator("section.panel").filter(has=page.get_by_role("heading",name="Financial reconciliation",exact=True))
        expect(panel).to_be_visible()
        expect(panel).to_contain_text("Outstanding")
        expect(panel).to_contain_text("Unapplied credit")
        stats=page.request.get(ORIGIN+"/api/data/v1/platform/financial-reconciliation?hotel_id="+HOTEL_A,ignore_https_errors=True)
        assert stats.status==200, ("financial reconciliation",stats.status,stats.text()[:250])
        data=stats.json()
        assert data["invoice_count"]==0 and data["reconciled"]
        assert all(Decimal(v)==0 for v in data["totals"].values())
        assert not data["payments_enabled"] and not data["payouts_enabled"]
        expect(panel).not_to_contain_text("61,000 KGS")
        print("PASS browser financial reconciliation excludes non-issuable 61000 KGS preview")
        page.locator('[data-hotel-tab="history"]').click()
        form=page.locator(".agreement-approval-form")
        expect(form).to_be_visible()
        form.locator('[name="acknowledged"]').check()
        with page.expect_response(ORIGIN+"/api/actions/agreement-internal-approvals") as submitted:
            form.locator('button[type="submit"]').click()
        response=submitted.value
        assert response.status==201, ("internal approval",response.status,response.text()[:250])
        approval=response.json()
        assert approval["terms_digest"]==contract["terms_digest"]
        assert approval["agreement_id"]==contract["id"] and approval["state"]=="INTERNALLY_APPROVED"
        assert not approval["client_signed"] and not approval["subscription_activated"]
        expect(page.get_by_text("Internally approved",exact=False)).to_be_visible()
        page.locator('[data-hotel-tab="subscription"]').click()
        panel=page.locator("section.panel").filter(has=page.get_by_role("heading",name="Subscription plan",exact=True))
        expect(panel).to_be_visible()
        expect(panel).to_contain_text("36,000 KGS")
        expect(panel).to_contain_text("25,000 KGS")
        expect(panel).to_contain_text("PLAN_ONLY")
        query="""SELECT json_build_object('approvals',count(*),'signed',(SELECT count(*) FROM flex_private.flex_commercial_agreement_versions WHERE state='SIGNED'),
            'payments',(SELECT count(*) FROM flex_private.flex_confirmed_payments),'subscriptions',(SELECT count(*) FROM flex_private.flex_subscriptions))
            FROM flex_private.flex_agreement_internal_approvals"""
        evidence=json.loads(subprocess.check_output(["psql","-XAt","-v","ON_ERROR_STOP=1","-c",query],text=True))
        assert evidence=={"approvals":1,"signed":0,"payments":0,"subscriptions":2},evidence
        print("PASS browser internal agreement approval and subscription plan; client signature, payment and activation remain disabled")
        # Real invitation-backed owner session; no forged identity or admin impersonation.
        owner_email=os.environ["QA_OWNER_EMAIL"]
        owner_password=os.environ["QA_OWNER_PASSWORD"]
        owner_secret=enroll(browser,owner_email,owner_password)
        # Better Auth shares a database-backed 60-second rate window on the
        # local runner IP. Enrollment and the second fresh login must not
        # consume each other's allowance. Keep the production limiter intact.
        time.sleep(65)
        owner_context=browser.new_context()
        owner=owner_context.new_page()
        owner.goto(ORIGIN)
        signin=owner.locator("#flex-identity-signin")
        signin.locator('[name="email"]').fill(owner_email)
        signin.locator('[name="password"]').fill(owner_password)
        with owner.expect_response(ORIGIN+"/api/identity/sign-in/email") as signed_in:
            signin.locator('button[type="submit"]').click()
        reply=signed_in.value
        assert reply.status==200,("owner sign-in HTTP",reply.status)
        assert reply.json().get("twoFactorRedirect") is True, "Owner fresh password login did not request TOTP"
        challenge=owner.locator("#flex-identity-totp")
        expect(challenge).to_be_visible(timeout=15000)
        challenge.locator('[name="code"]').fill(totp(owner_secret))
        with owner.expect_response(ORIGIN+"/api/identity/two-factor/verify-totp") as verified:
            challenge.locator('button[type="submit"]').click()
        assert verified.value.status==200
        me=owner.request.get(ORIGIN+"/api/data/v1/me",ignore_https_errors=True)
        assert me.status==200 and me.json()["role"]=="HOTEL_OWNER"
        assert me.json()["hotels"]==[HOTEL_A]
        owner.locator("#lang").select_option("en")
        owner.locator('[data-hotel-tab="subscription"]').click()
        panel=owner.locator("section.panel").filter(has=owner.get_by_role("heading",name="Confirm commercial terms",exact=True))
        expect(panel).to_be_visible()
        expect(panel).to_contain_text("36,000 KGS")
        expect(panel).to_contain_text("25,000 KGS")
        form=panel.locator(".customer-acceptance-form")
        form.locator('[name="acknowledged"]').check()
        with owner.expect_response(ORIGIN+"/api/actions/customer-agreement-acceptances") as submitted:
            form.locator('button[type="submit"]').click()
        response=submitted.value
        assert response.status==201,("owner acceptance",response.status,response.text()[:250])
        accepted=response.json()
        assert accepted["agreement_id"]==contract["id"] and accepted["terms_digest"]==contract["terms_digest"]
        assert not accepted["client_signed"] and not accepted["subscription_activated"] and not accepted["payments_enabled"]
        expect(panel.get_by_text("Customer accepted terms",exact=False)).to_be_visible()
        denied=owner.request.get(ORIGIN+"/api/data/v1/platform/customer-agreement-acceptances?hotel_id="+HOTEL_B,ignore_https_errors=True)
        assert denied.status==404
        page.locator('[data-hotel-tab="history"]').click()
        expect(page.get_by_text("Customer accepted terms",exact=True)).to_be_visible()
        query="""SELECT json_build_object('acceptances',count(*),'signed',(SELECT count(*) FROM flex_private.flex_commercial_agreement_versions WHERE state='SIGNED'),
            'payments',(SELECT count(*) FROM flex_private.flex_confirmed_payments),'subscriptions',(SELECT count(*) FROM flex_private.flex_subscriptions))
            FROM flex_private.flex_customer_agreement_acceptances"""
        evidence=json.loads(subprocess.check_output(["psql","-XAt","-v","ON_ERROR_STOP=1","-c",query],text=True))
        assert evidence=={"acceptances":1,"signed":0,"payments":0,"subscriptions":2},evidence
        owner_context.close()
        print("PASS browser real hotel owner accepted exact terms; other hotel denied; administrator sees evidence; PostgreSQL matches")
        browser.close()


if __name__ == "__main__":
    run()
