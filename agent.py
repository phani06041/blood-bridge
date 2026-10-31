"""
Blood Bridge 🩸 — turns an urgent blood request into a live, verified hunt, inside ASI:One.

  Requester: "Need 2 units O- at Manipal Hospital Old Airport Road, urgent, contact Ravi 98xxxxxx10"
    1. Understand  : ASI-1 extracts blood group, units, hospital, urgency, contact
    2. Verify      : checks the hospital exists, contact is present, and flags scam patterns
                     (requests for money / UPI / "processing fee")
    3. Blood banks : nearest blood banks with phone numbers (TomTom places) + live stock link (e-RaktKosh)
    4. Donors      : opt-in donors who are compatible, nearby and eligible (90+ days since last donation)
                     get an alert card in ASI:One: "I can donate" / "Not now"
    5. Rally       : one clean WhatsApp message with a request code, instead of endless "URGENT!!" forwards
    6. Track       : confirmations arrive live; the requester closes the request and donors are told
                     it's no longer needed, so forwards stop.

  Donor: "Register me as a donor" -> form card (blood group, area, last donation, phone, consent)

Hosted on Agentverse. Secrets: TOMTOM_API_KEY (places + blood banks; optional — falls back to a
built-in area list). ASI1_API_KEY / ASI1_BASE_URL are provided by Agentverse. ASI-1 is the only LLM.
Blood-group compatibility shown is for red cells / whole blood; the hospital always cross-matches.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import random
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from uuid import uuid4

import requests

try:
    from uagents import Agent, Context, Protocol
    from uagents_core.contrib.protocols.chat import (
        ChatAcknowledgement,
        ChatMessage,
        EndSessionContent,
        MetadataContent,
        StartSessionContent,
        TextContent,
        chat_protocol_spec,
    )
    HAVE_UAGENTS = True
except ImportError:  # unit tests import the logic without uAgents
    HAVE_UAGENTS = False

IST = timezone(timedelta(hours=5, minutes=30))
BLR_LAT, BLR_LON = 12.9716, 77.5946
HTTP_TIMEOUT = 8
DONOR_RADIUS_KM = 15
MIN_DAYS_BETWEEN_DONATIONS = 90
MAX_ALERTS_PER_REQUEST = 15
ERAKTKOSH_URL = "https://eraktkosh.mohfw.gov.in/BLDAHIMS/bloodbank/stockAvailability.cnt"

GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
# Red-cell / whole-blood compatibility: recipient -> donor groups that can give to them.
COMPATIBLE_DONORS = {
    "O-": ["O-"],
    "O+": ["O+", "O-"],
    "A-": ["A-", "O-"],
    "A+": ["A+", "A-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": GROUPS,
}

AREAS = {  # fallback geocoding (approximate area centres)
    "koramangala": (12.9352, 77.6245), "indiranagar": (12.9784, 77.6408), "hsr": (12.9116, 77.6474),
    "btm": (12.9166, 77.6101), "jayanagar": (12.9250, 77.5938), "jp nagar": (12.9063, 77.5857),
    "whitefield": (12.9698, 77.7500), "marathahalli": (12.9569, 77.7011), "bellandur": (12.9260, 77.6762),
    "electronic city": (12.8452, 77.6602), "hebbal": (13.0358, 77.5970), "yelahanka": (13.1007, 77.5963),
    "malleshwaram": (13.0035, 77.5710), "rajajinagar": (12.9910, 77.5525), "banashankari": (12.9255, 77.5468),
    "mg road": (12.9756, 77.6066), "majestic": (12.9767, 77.5713), "domlur": (12.9610, 77.6387),
    "old airport road": (12.9592, 77.6489), "sarjapur": (12.9107, 77.6866), "yeshwanthpur": (13.0280, 77.5409),
    "kr puram": (13.0076, 77.6955), "silk board": (12.9177, 77.6233), "vijayanagar": (12.9719, 77.5300),
}

SCAM_PATTERNS = [
    (r"\b(upi|gpay|google pay|phonepe|paytm|bank account|ifsc)\b", "asks for a payment / UPI transfer"),
    (r"\b(processing|registration|booking|advance)\s+(fee|charge|amount)\b", "mentions a 'fee' to get blood"),
    (r"\b(send|transfer|pay)\b.{0,20}\b(rs\.?|₹|inr|rupees|money)\b", "asks you to send money"),
    (r"\b(otp|pin|password)\b", "asks for an OTP / PIN"),
]

# ----------------------------------------------------------------------------- pure logic


def now_ist() -> datetime:
    return datetime.now(IST)


def haversine_km(a_lat, a_lon, b_lat, b_lon) -> float:
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def normalize_group(text: str | None) -> str | None:
    if not text:
        return None
    t = str(text).upper().replace(" ", "").replace("VE", "")
    t = t.replace("POSITIVE", "+").replace("POS", "+").replace("NEGATIVE", "-").replace("NEG", "-")
    t = t.replace("–", "-").replace("—", "-")
    m = re.search(r"(AB|A|B|O|0)([+-])", t)
    if not m:
        return None
    g = ("O" if m.group(1) == "0" else m.group(1)) + m.group(2)
    return g if g in GROUPS else None


def find_group_in_text(text: str) -> str | None:
    m = re.search(r"\b(AB|A|B|O)\s*(\+|-|\s?pos(?:itive)?|\s?neg(?:ative)?|\s?\+?ve|\s?-ve)", text, re.I)
    return normalize_group(m.group(0)) if m else None


def parse_date(text: str | None):
    if not text:
        return None
    t = str(text).strip().lower()
    if t in ("never", "no", "none", "never donated", "first time", "-"):
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y", "%b %Y", "%B %Y", "%m/%Y"):
        try:
            return datetime.strptime(str(text).strip(), fmt).date()
        except ValueError:
            continue
    m = re.search(r"(\d+)\s*(day|week|month|year)s?\s*ago", t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days = {"day": 1, "week": 7, "month": 30, "year": 365}[unit] * n
        return (now_ist() - timedelta(days=days)).date()
    return None


def is_eligible(donor: dict, today) -> bool:
    last = donor.get("last_donated")
    if not last:
        return True
    try:
        d = datetime.fromisoformat(last).date()
    except ValueError:
        return True
    return (today - d).days >= MIN_DAYS_BETWEEN_DONATIONS


def match_donors(request: dict, donors: dict, today, allow_self: bool = False) -> list[dict]:
    """Compatible, nearby, eligible, available donors — nearest first."""
    allowed = COMPATIBLE_DONORS.get(request["group"], [])
    out = []
    for d in donors.values():
        if not d.get("available", True) or d["group"] not in allowed:
            continue
        if not allow_self and d.get("sender") == request.get("requester"):
            continue
        if not is_eligible(d, today):
            continue
        dist = haversine_km(request["lat"], request["lon"], d["lat"], d["lon"])
        if dist <= DONOR_RADIUS_KM:
            out.append({**d, "distance_km": round(dist, 1), "exact_match": d["group"] == request["group"]})
    out.sort(key=lambda x: (not x["exact_match"], x["distance_km"]))
    return out[:MAX_ALERTS_PER_REQUEST]


def verify_request(req: dict, hospital_found: bool) -> tuple[str, list[str]]:
    """Returns (level, notes). level: 'ok' | 'check' | 'suspicious'."""
    notes, level = [], "ok"
    text = " ".join(str(v) for v in req.values() if v)
    for pattern, why in SCAM_PATTERNS:
        if re.search(pattern, text, re.I):
            notes.append(f"⚠️ {why}: real blood requests never need money from donors")
            level = "suspicious"
    if not hospital_found:
        notes.append("Hospital not found on the map; double-check the name")
        level = "check" if level == "ok" else level
    if not req.get("contact"):
        notes.append("No attendant contact given; donors need someone to call")
        level = "check" if level == "ok" else level
    units = req.get("units") or 1
    if units > 6:
        notes.append(f"{units} units is unusually high; confirm with the hospital")
        level = "check" if level == "ok" else level
    if level == "ok":
        notes.append("Hospital found, contact present, no scam patterns")
    return level, notes


def new_code(existing) -> str:
    while True:
        code = f"BB-{random.randint(1000, 9999)}"
        if code not in existing:
            return code


def rally_text(req: dict, handle: str) -> str:
    return (f"🩸 URGENT: {req['units']} unit(s) of {req['group']} blood needed at {req['hospital']}"
            f" ({req.get('urgency') or 'urgent'}). Contact: {req.get('contact') or 'see Blood Bridge'}.\n"
            f"Can you donate? Ask {handle} on ASI:One: \"I can donate {req['code']}\" — it shows live "
            f"if this is still needed.\nRequest {req['code']} · verified by Blood Bridge")


def whatsapp_link(text: str) -> str:
    return "https://wa.me/?text=" + quote(text)


def send_email_alert(donor: dict, req: dict, handle: str) -> bool:
    """Optional donor email alert via Brevo (free tier). Needs secrets BREVO_API_KEY + SENDER_EMAIL."""
    key, sender = os.environ.get("BREVO_API_KEY"), os.environ.get("SENDER_EMAIL")
    if not (key and sender and donor.get("email")):
        return False
    body = (f"Hi {donor['name']},\n\nSomeone ~{donor.get('distance_km', '?')} km from you needs {req['group']} blood "
            f"({req['units']} unit(s)) at {req['hospital']}, needed {req.get('urgency') or 'urgently'}.\n\n"
            f"If you can donate, open ASI:One (asi1.ai), message {handle} and say: \"I can donate {req['code']}\". "
            f"You'll get the hospital and contact details there.\n\nThank you,\nBlood Bridge")
    try:
        r = requests.post("https://api.brevo.com/v3/smtp/email", timeout=HTTP_TIMEOUT,
                          headers={"api-key": key, "Content-Type": "application/json"},
                          json={"sender": {"name": "Blood Bridge", "email": sender}, "to": [{"email": donor["email"]}],
                                "subject": f"🩸 {req['group']} blood needed near you ({req['code']})", "textContent": body})
        return r.status_code < 300
    except Exception:
        return False


def open_requests_for(donor: dict, requests_db: dict, today) -> list[dict]:
    """Open requests this donor can help with (compatible, within radius, eligible)."""
    if not is_eligible(donor, today):
        return []
    out = []
    for req in requests_db.values():
        if req.get("status") != "open" or req.get("lat") is None:
            continue
        if donor["group"] not in COMPATIBLE_DONORS.get(req["group"], []) or donor["id"] in req.get("confirmed", []):
            continue
        dist = haversine_km(req["lat"], req["lon"], donor["lat"], donor["lon"])
        if dist <= DONOR_RADIUS_KM:
            out.append({**req, "distance_km": round(dist, 1)})
    out.sort(key=lambda r: r["distance_km"])
    return out[:5]


def mask_phone(p: str | None) -> str:
    digits = re.sub(r"\D", "", p or "")
    return (digits[:2] + "•" * max(0, len(digits) - 4) + digits[-2:]) if len(digits) >= 6 else (p or "")


# ----------------------------------------------------------------------------- live data


class Geo:
    """Place text -> {'label','lat','lon'} via TomTom; falls back to known Bengaluru areas."""

    def __init__(self, key: str | None):
        self.key = key

    def find_hospital(self, text: str | None):
        """Hospital search: TomTom hospital category, rejecting dental/diagnostic/pharmacy look-alikes."""
        if not text:
            return None
        if self.key:
            typed = text.lower()
            try:
                r = requests.get(
                    f"https://api.tomtom.com/search/2/poiSearch/{quote(text)}.json",
                    params={"key": self.key, "countrySet": "IN", "lat": BLR_LAT, "lon": BLR_LON, "radius": 50000,
                            "limit": 10, "categorySet": "7321", "typeahead": "false"},
                    timeout=HTTP_TIMEOUT,
                )
                r.raise_for_status()
                words = {w for w in re.findall(r"[a-z]{3,}", typed)} - {"road", "bengaluru", "bangalore", "hospital", "hospitals", "layout"}
                best, best_score = None, -1
                for res in r.json().get("results") or []:
                    name = res.get("poi", {}).get("name", "")
                    low = (name + " " + res.get("address", {}).get("freeformAddress", "")).lower()
                    if re.search(r"dental|diagnostic|pharmacy|scan|lab\b|eye|skin|vet", name.lower()) and not re.search(r"dental|eye|skin", typed):
                        continue
                    score = sum(w in low for w in words) + (1 if "hospital" in name.lower() else 0)
                    if score > best_score:
                        pos = res["position"]
                        best, best_score = {"label": name, "lat": pos["lat"], "lon": pos["lon"], "source": "tomtom",
                                            "phone": res.get("poi", {}).get("phone")}, score
                if best and best_score >= max(1, len(words) // 2):
                    return best
            except Exception:
                pass
        return self.find(text)

    def find(self, text: str | None, poi_first: bool = True):
        if not text:
            return None
        if self.key:
            for endpoint in (("poiSearch", "search") if poi_first else ("search",)):
                try:
                    r = requests.get(
                        f"https://api.tomtom.com/search/2/{endpoint}/{quote(text)}.json",
                        params={"key": self.key, "countrySet": "IN", "lat": BLR_LAT, "lon": BLR_LON,
                                "radius": 50000, "limit": 3, "typeahead": "false"},
                        timeout=HTTP_TIMEOUT,
                    )
                    r.raise_for_status()
                    words = {w for w in re.findall(r"[a-z]{3,}", text.lower())} - {"road", "bengaluru", "bangalore", "hospital"}
                    for res in r.json().get("results") or []:
                        pos = res["position"]
                        if haversine_km(BLR_LAT, BLR_LON, pos["lat"], pos["lon"]) > 60:
                            continue
                        name = res.get("poi", {}).get("name") or res.get("address", {}).get("freeformAddress") or text
                        hay = re.sub(r"[^a-z ]", "", (name + " " + res.get("address", {}).get("freeformAddress", "")).lower())
                        if words and sum(w in hay or w in hay.replace(" ", "") for w in words) < max(1, (len(words) + 1) // 2):
                            continue
                        return {"label": name, "lat": pos["lat"], "lon": pos["lon"], "source": "tomtom",
                                "phone": res.get("poi", {}).get("phone")}
                except Exception:
                    pass
        t = re.sub(r"[^a-z ]", " ", text.lower())
        for area, (lat, lon) in AREAS.items():
            if area in t or area.replace(" ", "") in t.replace(" ", ""):
                return {"label": text.strip(), "lat": lat, "lon": lon, "source": "area"}
        return None

    def blood_banks(self, lat, lon, limit: int = 4) -> list[dict]:
        if not self.key:
            return []
        try:
            r = requests.get(
                f"https://api.tomtom.com/search/2/search/{quote('blood bank')}.json",
                params={"key": self.key, "countrySet": "IN", "lat": lat, "lon": lon, "radius": 15000,
                        "limit": 10, "typeahead": "false"},
                timeout=HTTP_TIMEOUT,
            )
            r.raise_for_status()
            banks = []
            for res in r.json().get("results") or []:
                poi = res.get("poi", {})
                name = poi.get("name", "")
                cats = " ".join(poi.get("categories", []) + [c.get("names", [{}])[0].get("name", "") for c in poi.get("classifications", [])])
                if "blood" not in (name + " " + cats).lower():
                    continue
                pos = res["position"]
                banks.append({"name": name, "phone": poi.get("phone"), "address": res.get("address", {}).get("freeformAddress", ""),
                              "km": round(haversine_km(lat, lon, pos["lat"], pos["lon"]), 1)})
            banks.sort(key=lambda b: b["km"])
            return banks[:limit]
        except Exception:
            return []


# ----------------------------------------------------------------------------- ASI-1 (only LLM)


def asi1_client():
    try:
        from openai import OpenAI
        return OpenAI(base_url=os.environ.get("ASI1_BASE_URL", "https://api.asi1.ai/v1"),
                      api_key=os.environ["ASI1_API_KEY"])
    except Exception:
        return None


INTENT_PROMPT = (
    "You route messages for Blood Bridge, a blood-donation coordinator in Bengaluru. Reply with ONLY JSON: "
    '{"intent": one of ["request","register","donate","decline","status","close","delete","nearby","help"], '
    '"group": blood group like "O-" or null, "units": integer or null, "hospital": string or null, '
    '"urgency": "today"|"within hours"|"tomorrow"|null, "contact": name and/or phone string or null, '
    '"code": request code like "BB-1234" or null, "area": donor area/pincode or null, '
    '"last_donated": date text or null, "name": donor name or null, "phone": phone or null}. '
    '"request" = someone needs blood; "register" = wants to become a donor; "donate" = offers to donate for a code; '
    '"decline" = cannot donate; "status" = asks about a request; "close" = request fulfilled/cancel; '
    '"delete" = remove my donor profile; "nearby" = a donor asks which requests near them need help.'
)


def understand(text: str) -> dict:
    client = asi1_client()
    if client:
        try:
            r = client.chat.completions.create(
                model="asi1", temperature=0, max_tokens=250,
                messages=[{"role": "system", "content": INTENT_PROMPT}, {"role": "user", "content": text}],
            )
            m = re.search(r"\{.*\}", r.choices[0].message.content or "", re.S)
            if m:
                data = json.loads(m.group(0))
                data["group"] = normalize_group(data.get("group")) or find_group_in_text(text)
                return data
        except Exception:
            pass
    return rule_understand(text)


def rule_understand(text: str) -> dict:
    t = text.lower()
    code = re.search(r"\bBB-\d{4}\b", text, re.I)
    code = code.group(0).upper() if code else None
    out = {"intent": "help", "group": find_group_in_text(text), "units": None, "hospital": None,
           "urgency": None, "contact": None, "code": code, "area": None, "last_donated": None,
           "name": None, "phone": None}
    if re.search(r"\b(delete|remove)\b.*\b(profile|me|donor)\b", t):
        out["intent"] = "delete"
    elif code and re.search(r"\b(can donate|i can|i'll donate|yes|available)\b", t):
        out["intent"] = "donate"
    elif code and re.search(r"\b(can't|cannot|not now|no)\b", t):
        out["intent"] = "decline"
    elif code and re.search(r"\b(close|closed|fulfilled|got it|arranged|done|cancel)\b", t):
        out["intent"] = "close"
    elif code:
        out["intent"] = "status"
    elif re.search(r"\b(near me|nearby|any requests|who needs)\b", t):
        out["intent"] = "nearby"
    elif re.search(r"\b(register|sign me up|become a donor|i want to donate|add me)\b", t):
        out["intent"] = "register"
    elif re.search(r"\b(need|needed|require|urgent|blood for)\b", t) and out["group"]:
        out["intent"] = "request"
    u = re.search(r"(\d+)\s*(unit|bottle|pint)s?", t)
    out["units"] = int(u.group(1)) if u else None
    h = re.search(r"\b(?:at|in)\s+([A-Z][\w .&'-]*?(?:hospital|clinic|medical|centre|center|institute|health)[\w .'-]*)", text, re.I)
    out["hospital"] = re.split(r"\b(?:call|contact|attendant|today|urgent|tomorrow|asap)\b", h.group(1), flags=re.I)[0].strip(" ,.-") if h else None
    p = re.search(r"\+?\d[\d\s-]{6,14}\d", text)
    if p:
        out["phone"] = p.group(0).strip()
    c = re.search(r"\b(?:contact|call|attendant)\b[:\s-]*([A-Za-z][A-Za-z .]{0,30}?)?[\s,:-]*(\+?\d[\d\s-]{6,14}\d)?\s*(?:$|[,.;])", text, re.I)
    if c and (c.group(1) or c.group(2)):
        out["contact"] = " ".join(x.strip() for x in (c.group(1), c.group(2)) if x and x.strip())
    elif p:
        out["contact"] = p.group(0).strip()
    return out


# ----------------------------------------------------------------------------- cards

GROUP_OPTIONS = [{"value": g, "label": g} for g in GROUPS]

DONOR_FORM = {
    "title": "Become a Blood Bridge donor 🩸",
    "fields": [
        {"name": "name", "kind": "text", "label": "Your first name", "required": True},
        {"name": "group", "kind": "select", "label": "Blood group", "required": True, "options": GROUP_OPTIONS},
        {"name": "area", "kind": "text", "label": "Area or pincode in Bengaluru", "required": True, "placeholder": "e.g. HSR Layout or 560102"},
        {"name": "last_donated", "kind": "text", "label": "Last donated (e.g. 2026-06-15, '4 months ago' or 'never')", "required": False},
        {"name": "phone", "kind": "text", "label": "Phone (shared only when you accept a request)", "required": True},
        {"name": "email", "kind": "email", "label": "Email for urgent alerts (optional)", "required": False},
        {"name": "consent", "kind": "checkbox", "label": "I'm 18–65, at least 45 kg, and agree to be alerted for nearby requests", "required": True},
    ],
    "submit_cta": {"label": "Register me", "selection": {"action": "register"}},
}

REQUEST_FORM = {
    "title": "Request blood 🩸",
    "fields": [
        {"name": "group", "kind": "select", "label": "Patient's blood group", "required": True, "options": GROUP_OPTIONS},
        {"name": "units", "kind": "number", "label": "Units needed", "required": True},
        {"name": "hospital", "kind": "text", "label": "Hospital name and area", "required": True, "placeholder": "e.g. Manipal Hospital, Old Airport Road"},
        {"name": "urgency", "kind": "select", "label": "Needed", "required": True,
         "options": [{"value": "within hours", "label": "Within hours"}, {"value": "today", "label": "Today"},
                     {"value": "tomorrow", "label": "Tomorrow"}]},
        {"name": "contact", "kind": "text", "label": "Attendant name + phone", "required": True},
    ],
    "submit_cta": {"label": "Review request", "selection": {"action": "review_request"}},
}


def welcome_card():
    def item(i, title, sub, action):
        return {"id": i, "title": title, "subtitle": sub, "primary_cta": {"label": "Start", "selection": {"action": action}}}
    return {"title": "Blood Bridge", "subtitle": "Urgent blood, found faster",
            "items": [item("req", "🩸 I need blood", "Verify, find blood banks, alert donors", "start_request"),
                      item("don", "🙋 Become a donor", "Get alerts for nearby requests", "start_register"),
                      item("near", "🔔 Requests near me", "Open requests you can help with", "nearby"),
                      item("mine", "📋 My requests", "Live status of your requests", "my_requests")]}


def review_card(req, level, notes):
    badge = {"ok": "✅ Looks genuine", "check": "🟡 Needs a quick check", "suspicious": "🚩 Possible scam"}[level]
    rows = [{"label": "Blood group", "value": req["group"]}, {"label": "Units", "value": str(req["units"])},
            {"label": "Hospital", "value": req["hospital"]}, {"label": "Needed", "value": req.get("urgency") or "urgent"},
            {"label": "Contact", "value": req.get("contact") or "—"}, {"label": "Verification", "value": badge}]
    rows += [{"label": "•", "value": n} for n in notes]
    return {"title": "Check before we alert donors", "summary_rows": rows,
            "approve_cta": {"label": "Alert donors now", "selection": {"action": "confirm_request"}, "primary": True},
            "reject_cta": {"label": "Edit", "selection": {"action": "start_request"}}}


def donor_alert_card(req, donor):
    return {"title": f"🩸 {req['group']} needed near you", "summary_rows": [
        {"label": "Hospital", "value": req["hospital"]},
        {"label": "Distance", "value": f"~{donor['distance_km']} km from {donor['area']}"},
        {"label": "Units", "value": str(req["units"])},
        {"label": "Needed", "value": req.get("urgency") or "urgent"},
        {"label": "Request", "value": req["code"]}],
        "ctas": [{"label": "I can donate", "selection": {"action": "donate", "code": req["code"]}, "primary": True},
                 {"label": "Not now", "selection": {"action": "decline", "code": req["code"]}}]}


def status_card(req, donors):
    rows = [{"label": "Status", "value": "🟢 Open" if req["status"] == "open" else "✅ Closed"},
            {"label": "Need", "value": f"{req['units']} × {req['group']} at {req['hospital']}"},
            {"label": "Donors alerted", "value": str(len(req.get("notified", [])))},
            {"label": "Confirmed", "value": f"{len(req.get('confirmed', []))} of {req['units']}"}]
    for did in req.get("confirmed", []):
        d = donors.get(did)
        if d:
            rows.append({"label": f"✅ {d['name']} ({d['group']})", "value": d.get("phone", "")})
    ctas = [{"label": "Refresh", "selection": {"action": "status", "code": req["code"]}}]
    if req["status"] == "open":
        ctas.insert(0, {"label": "Mark fulfilled", "selection": {"action": "close", "code": req["code"]}, "primary": True})
    return {"title": f"Request {req['code']}", "summary_rows": rows, "ctas": ctas}


# ----------------------------------------------------------------------------- card answers


def _json_objects(text: str):
    for m in re.finditer(r"\{[^{}]*\}", text or ""):
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                yield obj
        except Exception:
            continue


def read_selection(text: str, metas: list[dict]) -> dict:
    """Card answers arrive as MetadataContent 'selection', JSON in text, or planner prose."""
    sel: dict = {}
    for meta in metas:
        raw = meta.get("selection")
        if raw:
            try:
                v = json.loads(raw)
                if isinstance(v, dict):
                    sel.update(v)
            except Exception:
                pass
    for obj in _json_objects(text):
        sel.update(obj)
    for k in ("action", "code", "group", "units", "hospital", "urgency", "contact", "name", "area", "last_donated", "phone"):
        if k not in sel:
            m = re.search(rf"\b{k}\b[\"']?\s*[:=]\s*[\"']?([^,;\"'\n}}]+)", text or "", re.I)
            if m and m.group(1).strip():
                sel[k] = m.group(1).strip()
    return sel


# ----------------------------------------------------------------------------- agent

if HAVE_UAGENTS:
    agent = Agent()
    chat = Protocol(spec=chat_protocol_spec)
    HANDLE = os.environ.get("AGENT_HANDLE", "@blood-bridge")

    def card_block(kind: str, payload: dict):
        return MetadataContent(metadata={
            "card_protocol_version": "1", "requires_card_interaction": "true", "card_kind": kind,
            "card_payload": json.dumps(payload, ensure_ascii=False), "card_id": str(uuid4())})

    def msg(*blocks):
        content = [TextContent(type="text", text=b) if isinstance(b, str) else b for b in blocks]
        return ChatMessage(timestamp=datetime.utcnow(), msg_id=uuid4(), content=content)

    def load(ctx, key, default):
        v = ctx.storage.get(key)
        return v if v is not None else default

    async def handle_request_review(ctx, sender, req):
        geo = Geo(os.environ.get("TOMTOM_API_KEY"))
        place = await asyncio.to_thread(geo.find_hospital, req["hospital"])
        req["lat"], req["lon"] = (place["lat"], place["lon"]) if place else (None, None)
        level, notes = verify_request(req, bool(place))
        if not place:
            await ctx.send(sender, msg(f"I couldn't find **{req['hospital']}** on the map. Please add the area "
                                       "(e.g. 'Manipal Hospital, Old Airport Road').", card_block("form", REQUEST_FORM)))
            return
        req["hospital_label"] = place["label"]
        ctx.storage.set(f"draft:{sender}", {**req, "level": level, "notes": notes})
        await ctx.send(sender, msg("🔍 I checked the request before alerting anyone:", card_block("review", review_card(req, level, notes))))

    async def confirm_request(ctx, sender):
        draft = ctx.storage.get(f"draft:{sender}")
        if not draft:
            await ctx.send(sender, msg("Let's start the request:", card_block("form", REQUEST_FORM)))
            return
        if draft["level"] == "suspicious":
            await ctx.send(sender, msg("🚩 This request looks like a known scam pattern (money/UPI). I won't alert donors. "
                                       "If it's genuine, remove any payment details and try again."))
            return
        requests_db = load(ctx, "requests", {})
        donors = load(ctx, "donors", {})
        code = new_code(requests_db)
        req = {**{k: draft[k] for k in ("group", "units", "hospital", "urgency", "contact", "lat", "lon")},
               "hospital": draft.get("hospital_label") or draft["hospital"], "code": code, "requester": sender,
               "status": "open", "created": now_ist().isoformat(), "notified": [], "confirmed": [], "declined": []}
        geo = Geo(os.environ.get("TOMTOM_API_KEY"))
        banks = await asyncio.to_thread(geo.blood_banks, req["lat"], req["lon"])
        matches = match_donors(req, donors, now_ist().date(), allow_self=os.environ.get("DEMO_ALLOW_SELF") == "1")
        emailed = 0
        for d in matches:
            req["notified"].append(d["id"])
            if d.get("email") and await asyncio.to_thread(send_email_alert, d, req, HANDLE):
                emailed += 1
        requests_db[code] = req
        ctx.storage.set("requests", requests_db)
        mine = load(ctx, f"mine:{sender}", [])
        ctx.storage.set(f"mine:{sender}", mine + [code])
        ctx.storage.set(f"draft:{sender}", None)

        lines = [f"✅ **Request {code} is live.** Here's what I did:"]
        exact = sum(1 for d in matches if d["exact_match"])
        lines.append(f"🙋 **Donors**: **{len(matches)}** registered compatible donor(s) within {DONOR_RADIUS_KM} km "
                     f"({exact} exact {req['group']} match) will see this request the moment they open Blood Bridge"
                     + (f"; **{emailed}** emailed now" if emailed else "") if matches else
                     "🙋 **Donors**: no registered donors match nearby yet — the rally message below reaches people who aren't registered.")
        if banks:
            lines.append("🏥 **Nearest blood banks** (call to confirm stock):")
            lines += [f"- {b['name']} — {b['km']} km" + (f" · 📞 {b['phone']}" if b.get("phone") else "") for b in banks]
        lines.append(f"📊 **Live stock** by blood bank: [e-RaktKosh]({ERAKTKOSH_URL})")
        lines.append(f"📣 **Rally**: [share one clean request on WhatsApp]({whatsapp_link(rally_text(req, HANDLE))}) — "
                     f"people can reply to {HANDLE} with \"I can donate {code}\".")
        lines.append("I'll update you here as donors confirm.")
        await ctx.send(sender, msg("\n\n".join(lines).replace(":**\n\n- ", ":**\n- ").replace("\n\n- ", "\n- "),
                                   card_block("detail", status_card(req, donors))))

    async def donor_response(ctx, sender, code, accept: bool):
        requests_db = load(ctx, "requests", {})
        donors = load(ctx, "donors", {})
        req = requests_db.get((code or "").upper())
        if not req:
            await ctx.send(sender, msg(f"I can't find request {code}. Check the code (like BB-1234)."))
            return
        if req["status"] != "open":
            await ctx.send(sender, msg(f"🙏 Thank you! Request {req['code']} is already fulfilled — no need to go."))
            return
        donor = donors.get(sender)
        if not accept:
            req["declined"].append(sender)
            requests_db[req["code"]] = req
            ctx.storage.set("requests", requests_db)
            await ctx.send(sender, msg("No problem — thanks for replying. 💛"))
            return
        if not donor:
            await ctx.send(sender, msg("Thank you! 🙏 Quick details so the family can reach you:", card_block("form", {
                **DONOR_FORM, "title": f"Donating for {req['code']}",
                "submit_cta": {"label": "Confirm I can donate", "selection": {"action": "register", "code": req["code"]}}})))
            return
        if sender not in req["confirmed"]:
            req["confirmed"].append(sender)
        requests_db[req["code"]] = req
        ctx.storage.set("requests", requests_db)
        await ctx.send(sender, msg(f"💛 Thank you, {donor['name']}! Please go to **{req['hospital']}** and call "
                                   f"**{req.get('contact') or 'the attendant'}** on the way. Carry an ID; eat something light first."))
        # The requester sees the confirmation (name, group, phone) on their status card's Refresh.

    async def register_donor(ctx, sender, data, code=None):
        geo = Geo(os.environ.get("TOMTOM_API_KEY"))
        group = normalize_group(data.get("group"))
        place = await asyncio.to_thread(geo.find, data.get("area"), False)
        missing = [n for n, ok in (("blood group", group), ("area", place), ("phone", data.get("phone")), ("name", data.get("name"))) if not ok]
        if missing:
            await ctx.send(sender, msg(f"Almost there — I still need: {', '.join(missing)}.", card_block("form", DONOR_FORM)))
            return
        last = parse_date(data.get("last_donated"))
        donors = load(ctx, "donors", {})
        donors[sender] = {"id": sender, "sender": sender, "name": str(data["name"]).strip()[:30], "group": group,
                          "area": str(data["area"]).strip()[:40], "lat": place["lat"], "lon": place["lon"],
                          "last_donated": last.isoformat() if last else None, "phone": str(data["phone"]).strip()[:20],
                          "email": (str(data.get("email")).strip()[:80] if data.get("email") and "@" in str(data.get("email")) else None),
                          "available": True, "registered": now_ist().isoformat()}
        ctx.storage.set("donors", donors)
        eligible = is_eligible(donors[sender], now_ist().date())
        note = "" if eligible else f" You can donate again after {MIN_DAYS_BETWEEN_DONATIONS} days from your last donation; I'll only alert you after that."
        await ctx.send(sender, msg(f"🎉 You're registered, {donors[sender]['name']} ({group}, {donors[sender]['area']}). "
                                   f"I'll alert you only for compatible requests within {DONOR_RADIUS_KM} km.{note}\n"
                                   f"Your number stays hidden until you tap **I can donate**. Say \"delete my donor profile\" anytime."))
        if code:
            await donor_response(ctx, sender, code, True)

    async def show_nearby(ctx, sender, explicit=False):
        donors = load(ctx, "donors", {})
        me = donors.get(sender)
        if not me:
            if explicit:
                await ctx.send(sender, msg("Register as a donor first, then I'll show requests you can help with:",
                                           card_block("form", DONOR_FORM)))
            return False
        found = open_requests_for(me, load(ctx, "requests", {}), now_ist().date())
        if not found:
            if explicit:
                await ctx.send(sender, msg(f"No open requests near {me['area']} right now, {me['name']}. Thank you for being ready 💛"))
            return False
        for req in found[:3]:
            await ctx.send(sender, msg(f"🩸 Someone ~{req['distance_km']} km from you needs {req['group']} blood:",
                                       card_block("detail", donor_alert_card(req, {**me, "distance_km": req["distance_km"]}))))
        return True

    @chat.on_message(ChatMessage)
    async def on_chat(ctx: Context, sender: str, m: ChatMessage):
        await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.utcnow(), acknowledged_msg_id=m.msg_id))
        text = re.sub(r"@[\w-]+", "", m.text()).strip()
        metas = [c.metadata for c in m.content if isinstance(c, MetadataContent)]
        ctx.logger.info(f"IN from={sender[:16]} text={text[:300]!r} metadata={json.dumps(metas)[:300]}")
        try:
            sel = read_selection(text, metas)
            action = sel.get("action")
            if not action and (not text or re.fullmatch(r"(hi|hello|hey|hii+)[!. ]*", text.lower())):
                if await show_nearby(ctx, sender):
                    return
                await ctx.send(sender, msg("Hi! I'm **Blood Bridge** 🩸 — I turn an urgent blood request into a verified, "
                                           "live hunt across blood banks and nearby donors.", card_block("carousel", welcome_card())))
                return
            if not action:
                u = await asyncio.to_thread(understand, text)
                action = {"request": "review_request", "register": "register", "donate": "donate", "decline": "decline",
                          "status": "status", "close": "close", "delete": "delete", "nearby": "nearby"}.get(u.get("intent"), "help")
                sel = {**{k: v for k, v in u.items() if v}, **sel}
            if action == "start_request":
                await ctx.send(sender, msg("Tell me what's needed:", card_block("form", REQUEST_FORM)))
            elif action == "start_register":
                await ctx.send(sender, msg("Thank you for stepping up 💛", card_block("form", DONOR_FORM)))
            elif action == "review_request":
                if not (sel.get("contact") or sel.get("phone")):
                    sel["contact"] = rule_understand(text).get("contact")
                req = {"group": normalize_group(sel.get("group")), "units": int(re.sub(r"\D", "", str(sel.get("units") or "1")) or 1),
                       "hospital": sel.get("hospital"), "urgency": sel.get("urgency"), "contact": sel.get("contact") or sel.get("phone"),
                       "raw": text[:600]}  # the scam check reads the original words too
                if not req["group"] or not req["hospital"]:
                    await ctx.send(sender, msg("I need at least the blood group and hospital:", card_block("form", REQUEST_FORM)))
                else:
                    await handle_request_review(ctx, sender, req)
            elif action == "confirm_request":
                await confirm_request(ctx, sender)
            elif action == "register":
                await register_donor(ctx, sender, sel, sel.get("code"))
            elif action in ("donate", "decline"):
                await donor_response(ctx, sender, sel.get("code"), action == "donate")
            elif action in ("status", "close", "my_requests"):
                requests_db, donors = load(ctx, "requests", {}), load(ctx, "donors", {})
                codes = [sel["code"].upper()] if sel.get("code") else load(ctx, f"mine:{sender}", [])[-3:]
                if not codes:
                    await ctx.send(sender, msg("You have no requests yet.", card_block("carousel", welcome_card())))
                for code in codes:
                    req = requests_db.get(code)
                    if not req:
                        continue
                    if action == "close" and req["requester"] == sender and req["status"] == "open":
                        req["status"] = "closed"
                        requests_db[code] = req
                        ctx.storage.set("requests", requests_db)
                        await ctx.send(sender, msg(f"✅ Closed {code}. It disappears from every donor's list right away, and anyone "
                                                   f"who replies to the WhatsApp message is told it's no longer needed. "
                                                   "Wishing the patient a quick recovery 💛"))
                    else:
                        await ctx.send(sender, msg(f"Live status of {code}:", card_block("detail", status_card(req, donors))))
            elif action == "nearby":
                await show_nearby(ctx, sender, explicit=True)
            elif action == "delete":
                donors = load(ctx, "donors", {})
                if donors.pop(sender, None):
                    ctx.storage.set("donors", donors)
                    await ctx.send(sender, msg("Done — your donor profile and phone number are deleted."))
                else:
                    await ctx.send(sender, msg("You don't have a donor profile with me."))
            else:
                await ctx.send(sender, msg("I'm **Blood Bridge** 🩸. Need blood, or want to be a donor?",
                                           card_block("carousel", welcome_card())))
        except Exception as e:
            ctx.logger.exception("handler failed")
            await ctx.send(sender, msg(f"Sorry, something went wrong ({type(e).__name__}). Please try again — "
                                       f"for emergencies also call the hospital blood bank directly."))

    @chat.on_message(ChatAcknowledgement)
    async def on_ack(ctx: Context, sender: str, a: ChatAcknowledgement):
        pass

    agent.include(chat, publish_manifest=True)

    if __name__ == "__main__":
        agent.run()
