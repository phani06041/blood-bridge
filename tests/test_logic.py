"""Offline tests for Blood Bridge's logic (no network, no uAgents).  Run: python -m unittest discover -s tests -v"""
import os
import sys
import unittest
from datetime import date, timedelta
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import agent as bb  # noqa: E402

TODAY = date(2026, 10, 31)
MANIPAL = {"lat": 12.9592, "lon": 77.6489}


def donor(sender, group, lat, lon, last=None, available=True):
    return {"id": sender, "sender": sender, "name": sender, "group": group, "area": "x", "lat": lat, "lon": lon,
            "last_donated": last, "phone": "9876543210", "available": available}


class GroupTests(unittest.TestCase):
    def test_normalize(self):
        for raw, want in [("O-", "O-"), ("o neg", "O-"), ("O -ve", "O-"), ("AB positive", "AB+"), ("b+ve", "B+"),
                          ("0+", "O+"), ("A Negative", "A-"), ("xyz", None)]:
            self.assertEqual(bb.normalize_group(raw), want, raw)

    def test_find_in_sentence(self):
        self.assertEqual(bb.find_group_in_text("Need 2 units O negative at Manipal"), "O-")
        self.assertEqual(bb.find_group_in_text("urgent AB+ve blood"), "AB+")

    def test_compatibility(self):
        self.assertEqual(bb.COMPATIBLE_DONORS["O-"], ["O-"])
        self.assertIn("O-", bb.COMPATIBLE_DONORS["AB+"])
        self.assertNotIn("A+", bb.COMPATIBLE_DONORS["B+"])


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.req = {"group": "A+", "requester": "req", **MANIPAL}
        self.donors = {
            "near_exact": donor("near_exact", "A+", 12.96, 77.65),
            "near_o": donor("near_o", "O-", 12.97, 77.64),
            "wrong_group": donor("wrong_group", "B+", 12.96, 77.65),
            "too_far": donor("too_far", "A+", 13.20, 77.70),
            "recent": donor("recent", "A+", 12.96, 77.65, last=(TODAY - timedelta(days=30)).isoformat()),
            "paused": donor("paused", "A+", 12.96, 77.65, available=False),
            "req": donor("req", "A+", 12.96, 77.65),
        }

    def test_match_filters_and_orders(self):
        got = [d["id"] for d in bb.match_donors(self.req, self.donors, TODAY)]
        self.assertEqual(got, ["near_exact", "near_o"])

    def test_self_match_only_in_demo(self):
        got = [d["id"] for d in bb.match_donors(self.req, self.donors, TODAY, allow_self=True)]
        self.assertIn("req", got)

    def test_eligibility_window(self):
        self.assertTrue(bb.is_eligible({"last_donated": (TODAY - timedelta(days=91)).isoformat()}, TODAY))
        self.assertFalse(bb.is_eligible({"last_donated": (TODAY - timedelta(days=10)).isoformat()}, TODAY))
        self.assertTrue(bb.is_eligible({"last_donated": None}, TODAY))


class VerifyTests(unittest.TestCase):
    def test_genuine(self):
        level, notes = bb.verify_request({"group": "O-", "units": 2, "hospital": "Manipal", "contact": "Ravi 9876543210"}, True)
        self.assertEqual(level, "ok")

    def test_scam_upi(self):
        level, notes = bb.verify_request({"group": "O-", "units": 2, "hospital": "X", "contact": "send ₹2000 processing fee to UPI abc@ybl"}, True)
        self.assertEqual(level, "suspicious")
        self.assertTrue(any("money" in n or "payment" in n for n in notes))

    def test_missing_contact_and_hospital(self):
        level, _ = bb.verify_request({"group": "O-", "units": 9, "hospital": "Nowhere", "contact": None}, False)
        self.assertEqual(level, "check")


class TextTests(unittest.TestCase):
    def test_rule_request(self):
        u = bb.rule_understand("Need 2 units O negative at Manipal Hospital Old Airport Road, contact Ravi 9876543210")
        self.assertEqual(u["intent"], "request")
        self.assertEqual((u["group"], u["units"]), ("O-", 2))
        self.assertIn("Manipal Hospital", u["hospital"])
        self.assertIn("9876543210", u["contact"])

    def test_rule_donate_and_close(self):
        self.assertEqual(bb.rule_understand("I can donate BB-1234")["intent"], "donate")
        self.assertEqual(bb.rule_understand("BB-1234 is fulfilled, close it")["intent"], "close")
        self.assertEqual(bb.rule_understand("register me as a donor")["intent"], "register")

    def test_understand_falls_back_without_asi1(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(bb.understand("I can donate BB-4321")["code"], "BB-4321")

    def test_dates(self):
        self.assertIsNone(bb.parse_date("never"))
        self.assertEqual(bb.parse_date("2026-06-15"), date(2026, 6, 15))
        self.assertIsNotNone(bb.parse_date("4 months ago"))

    def test_card_answers(self):
        sel = bb.read_selection('{"action": "donate", "code": "BB-1111"}', [])
        self.assertEqual(sel["code"], "BB-1111")
        sel = bb.read_selection("", [{"selection": '{"action": "confirm_request"}'}])
        self.assertEqual(sel["action"], "confirm_request")

    def test_rally_and_mask(self):
        req = {"units": 2, "group": "O-", "hospital": "Manipal", "urgency": "today", "contact": "Ravi", "code": "BB-1234"}
        self.assertIn("BB-1234", bb.rally_text(req, "@blood-bridge"))
        self.assertTrue(bb.whatsapp_link("hi there").startswith("https://wa.me/?text=hi%20there"))
        self.assertEqual(bb.mask_phone("9876543210"), "98••••••10")


class GeoTests(unittest.TestCase):
    def test_area_fallback(self):
        g = bb.Geo(None).find("HSR Layout sector 2")
        self.assertAlmostEqual(g["lat"], 12.9116, places=3)

    @mock.patch("requests.get")
    def test_blood_banks_filter(self, get):
        get.return_value.raise_for_status = lambda: None
        get.return_value.json = lambda: {"results": [
            {"poi": {"name": "Rotary Blood Bank", "phone": "+91 80 1234 5678", "categories": ["blood bank"]},
             "position": {"lat": 12.96, "lon": 77.65}, "address": {"freeformAddress": "Old Airport Rd"}},
            {"poi": {"name": "Pizza Place", "categories": ["restaurant"]}, "position": {"lat": 12.96, "lon": 77.65},
             "address": {}}]}
        banks = bb.Geo("k").blood_banks(**MANIPAL)
        self.assertEqual([b["name"] for b in banks], ["Rotary Blood Bank"])


if __name__ == "__main__":
    unittest.main()


class FeedbackChanges(unittest.TestCase):
    """Nov 2026 feedback: a safe sandbox, clearer context, and checked donor details."""

    def test_indian_mobile(self):
        self.assertEqual(bb.valid_indian_mobile("98765 43210"), "+91 98765 43210")
        self.assertEqual(bb.valid_indian_mobile("+91-9876543210"), "+91 98765 43210")
        self.assertEqual(bb.valid_indian_mobile("09876543210"), "+91 98765 43210")
        for bad in ("23456789187", "12345", "5876543210", "9999999999", None, ""):
            self.assertIsNone(bb.valid_indian_mobile(bad), bad)

    def test_demo_donors_are_compatible_samples(self):
        req = {"group": "A-", "code": "DEMO-1234"}
        ds = bb.demo_donors(req)
        self.assertEqual(len(ds), 3)
        for d in ds:
            self.assertIn(d["group"], bb.COMPATIBLE_DONORS["A-"])
            self.assertIn("(sample)", d["name"])
        self.assertEqual(ds[0]["group"], "A-")

    def test_demo_and_why_intents(self):
        self.assertEqual(bb.rule_understand("can I try a demo?")["intent"], "demo")
        self.assertEqual(bb.rule_understand("exit demo")["intent"], "exit_demo")
        self.assertEqual(bb.rule_understand("why does this matter?")["intent"], "why")
        self.assertEqual(bb.rule_understand("status DEMO-1234")["code"], "DEMO-1234")
        self.assertEqual(bb.rule_understand("Need 1 unit O+ at Manipal Hospital")["intent"], "request")


class Coverage(unittest.TestCase):
    def test_other_city(self):
        self.assertEqual(bb.other_city("Kokilaben Hospital, Andheri West, Mumbai"), "Mumbai")
        self.assertIsNone(bb.other_city("Manipal Hospital Old Airport Road"))
        self.assertEqual(bb.other_city("AIIMS New Delhi"), "Delhi")
