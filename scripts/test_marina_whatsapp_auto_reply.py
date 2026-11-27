import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services"/"api"))
from app.whatsapp_auto_reply import activation_time, build_quote_reply

ENV = {"ENABLE_GREEN_API_AI_AUTO_SEND":"true","GREEN_API_AI_AUTO_SEND_CONFIRM":"OWNER_APPROVED_SINGLE_HOTEL_QUOTES","ENABLE_GREEN_API_SINGLE_OUTBOUND":"true","GREEN_API_AI_AUTO_SEND_FROM":"2026-11-27T12:00:00+06:00"}
SEARCH = {"check_in":"2026-12-05","check_out":"2026-12-07","adults":2,"children":0}
INTENT = {"intent":"availability","search":SEARCH}
AVAIL = {**SEARCH,"nights":2,"options":[{"room_type_name":"Standard","total_kgs":12000,"available_count":2}]}

def reply(text="2 взрослых, без детей",intent=INTENT,availability=AVAIL,currency="KGS"):
    return build_quote_reply(intent,availability,currency,[{"direction":"INBOUND","text":text}])

class AutoQuoteTests(unittest.TestCase):
    def test_explicit_activation_only(self):
        self.assertIsNone(activation_time({}))
        self.assertEqual(activation_time(ENV),datetime(2026,11,27,6,tzinfo=timezone.utc))
        for key in ENV:
            self.assertIsNone(activation_time({k:v for k,v in ENV.items() if k!=key}))
        self.assertIsNone(activation_time({**ENV,"GREEN_API_AI_AUTO_SEND_FROM":"2026-11-27T12:00:00"}))
    def test_ru(self):
        text=reply()
        self.assertIn("12 000 сом",text)
        self.assertIn("Это не бронь",text)
    def test_en(self):
        self.assertIn("not a reservation",reply("2 adults, no children"))
    def test_kg(self):
        self.assertIn("Бул брондоо эмес",reply("2 чоң киши, баласыз"))
    def test_nonquote(self):
        for intent in ("consultation","clarify","staff_review"):
            self.assertIsNone(reply(intent={"intent":intent,"search":None}))
    def test_no_inventory(self):
        self.assertIsNone(reply(availability={**AVAIL,"options":[]}))
    def test_mismatch(self):
        for field,value in (("check_in","2026-12-06"),("adults",3),("nights",3)):
            self.assertIsNone(reply(availability={**AVAIL,field:value}))
    def test_invalid_facts(self):
        for option in ({"room_type_name":"Standard","total_kgs":False,"available_count":2},{"room_type_name":"Standard","total_kgs":12000,"available_count":0},{"room_type_name":"Standard\nSECRET","total_kgs":12000,"available_count":2}):
            self.assertIsNone(reply(availability={**AVAIL,"options":[option]}))
        self.assertIsNone(reply(currency="USD"))
    def test_no_language_marker(self):
        self.assertIsNone(reply("hello"))

if __name__=="__main__":
    unittest.main()
