# 🩸 Blood Bridge: urgent blood, found faster

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

**Say in ASI:One:** *"Need 2 units O negative at Manipal Hospital, Old Airport Road, today. Contact Ravi 98xxxxxx10"*
**Blood Bridge then:**
1. 🔍 **Verifies** the request: the hospital exists on the map, a contact is given, and **no scam patterns** (asking donors for money / UPI / a "processing fee" is a known blood-request scam in India; those requests are blocked).
2. 🏥 **Finds the nearest blood banks** with phone numbers, and links live stock on the government's **e-RaktKosh**.
3. 🙋 **Alerts opt-in donors** who are **compatible** (red-cell rules), **within 15 km** and **eligible** (90+ days since their last donation). Each gets an alert card: *I can donate / Not now*.
4. 📣 **Writes one clean WhatsApp rally message** with a request code, so people outside the network can respond ("I can donate BB-1234").
5. ✅ **Tracks confirmations live**: the requester gets each donor's name, blood group and phone as they accept.
6. 🛑 **Closes the loop**: when the requester marks it fulfilled, every alerted donor is told *"no need to go"*, which stops stale "URGENT!!" forwards.

Built for **Stranger Builds × Fetch.ai** (Challenge 1: *From Intent to Action*; Challenge 2: *Best Use of ASI:One*).

## Why
India has a structural blood shortage (≈1 million units/year short), and families still find donors through chaotic WhatsApp forwards that are never verified, never updated and never closed, and that scammers exploit. Blood Bridge turns that into a verified, tracked, closed-loop request.

## How it works
```
Requester ─▶ Blood Bridge (Chat Protocol, ASI:One)
               ├─ ASI-1: understands the request / donor message (the only LLM)
               ├─ Verifier: hospital on map? contact? money/UPI/OTP scam patterns? unusual units?
               ├─ Blood banks: TomTom place search near the hospital (+ e-RaktKosh live-stock link)
               ├─ Matcher: compatibility table × distance (≤15 km) × 90-day eligibility × availability
               ├─ Notifier: alert cards to matched donors in ASI:One
               ├─ Rally: one WhatsApp message with a request code
               └─ Tracker: confirmations → requester; close → "no longer needed" to all alerted donors
Donor ─▶ "Register me as a donor" (form card) · "I can donate BB-1234" · "delete my donor profile"
```
**Interactive Cards:** welcome carousel · request form · verification review (approve / edit) · donor alert (I can donate / Not now) · live status (mark fulfilled / refresh) · donor registration form.

**Reliability:** every external call has a timeout and a fallback (no TomTom key → built-in Bengaluru area list; ASI-1 unavailable → rule-based parsing); handlers never leave the user without a reply.

**Privacy:** donors share only first name, blood group, area and phone; the phone is revealed **only after the donor taps "I can donate"**. "delete my donor profile" removes everything.

## Agents
| Name | Address | Role |
|---|---|---|
| Blood Bridge | `agent1q…` *(fill in after deploying)* | Chat Protocol entry point; verifier, matcher, notifier, tracker |

## Run / deploy (Agentverse hosted agent)
1. Agentverse → Agents → *Launch an Agent* → blank hosted agent → paste `agent.py` in the Build tab.
2. Secrets: `TOMTOM_API_KEY` (free at developer.tomtom.com). Optional: `AGENT_HANDLE` (e.g. `@blood-bridge`), `DEMO_ALLOW_SELF=1` to let one account test both requester and donor roles.
3. Start, set name / @handle / this README in *Profile*, category **Innovation Lab**.
4. In ASI:One: "Register me as a donor", then from another account "Need 1 unit O+ at Manipal Hospital Old Airport Road, contact …".

**Tests (offline):** `pip install requests && python -m unittest discover -s tests -v`

## Medical & safety notes
- Compatibility shown is for red cells / whole blood; **the hospital blood bank always cross-matches**. Platelets/plasma follow different rules.
- Eligibility shown is a simplified pre-check (18–65 years, ≥45 kg, 90 days between donations); the blood bank's screening decides.
- Blood Bridge never asks for or handles money.

## Roadmap
- Split Verifier / Matcher / Notifier into separate Agentverse agents (agent-to-agent).
- Hire existing marketplace agents (maps/places) and add platelet/plasma rules.
- Hospital & blood-bank accounts that can post verified requests; Payment Protocol for a paid institutional tier (never for donors).
