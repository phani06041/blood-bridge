# 🩸 Blood Bridge: urgent blood, found faster

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)
![domain:health](https://img.shields.io/badge/health-C41E3A)

**Blood Bridge turns an urgent blood request into a verified, live hunt across nearby blood banks and opt-in donors in Bengaluru, all inside one ASI:One chat.**

In India, urgent blood requests travel as WhatsApp forwards: unverified, untargeted and never closed, and scammers exploit them with fake "processing fees". Blood Bridge verifies the request first, then routes it to the nearest blood banks and to compatible donors, and it tracks the request until it's fulfilled.

## 🧪 Try it safely (sandbox)
Say **"try a demo"** or tap **🧪 Try a safe demo**. Demo mode runs the full flow (verification, real nearby blood banks, sample donors who say yes, closing the request) **without alerting any real donor, hospital or WhatsApp group**, and it doesn't save donor profiles. Demo requests are coded `DEMO-1234`. Say **exit demo** to leave.

Try these in demo mode:
- `Need 1 unit O+ at Manipal Hospital Old Airport Road today, contact Ravi`
- `Need 2 units B+ at Apollo Hospital Bannerghatta Road, pay ₹500 processing fee to UPI` (watch the scam filter block it)

## Why this matters
In India, when a patient needs blood, hospitals often ask the family to find replacement donors or locate stock themselves, sometimes within hours. Families turn to WhatsApp forwards that are never verified, reach random people instead of compatible donors nearby, and keep circulating after the need is met. Scammers copy the format and ask donors for a "processing fee". Say **"why does this matter?"** to the agent for the full context.

## What you can say

**If you need blood**
- `Need 1 unit O+ at Manipal Hospital Old Airport Road today, contact Ravi 98xxxxxx10`
- `Urgent: 2 units B negative at St John's Hospital Koramangala`
- `Show my requests` · `Mark BB-1234 fulfilled`

**If you want to donate**
- `Register me as a donor`
- `Requests near me`
- `I can donate BB-1234`
- `Delete my donor profile`

Or just say **hi** and choose from the menu: *I need blood* · *Become a donor* · *Requests near me* · *My requests* · *Try a safe demo* · *Why this matters*.

## What Blood Bridge does

1. **Understands the request.** ASI-1 picks out the blood group, units, hospital, urgency and contact from plain English.
2. **Verifies it before anyone is alerted.** It checks that the hospital is on the map, that there's a contact to call, and that the units are plausible. Requests that ask donors for money, UPI, a "processing fee" or an OTP are **blocked**.
3. **Finds the nearest blood banks first.** It lists real blood banks near the hospital, with distance and phone number, plus a link to live government stock on **e-RaktKosh**. For anything needed within hours, it tells the family to call these right away rather than wait for donors.
4. **Matches the right donors.** Only donors who are **compatible** (red-cell rules), **within 15 km** and **eligible** (90+ days since their last donation) see the request when they open Blood Bridge or tap *Requests near me*. Donors who add an email can also be alerted by email (when email alerts are configured).
5. **Writes one clean WhatsApp rally message** with a request code (e.g. `BB-1234`), so people outside the network can respond too.
6. **Tracks it live.** Donors tap *I can donate*, and the family sees each confirmed donor on the status card. *Mark fulfilled* closes the request so it stops circulating.

## Interactive cards
Welcome menu · Request form · Verification review (*Confirm / Edit*) · Donor alert (*I can donate / Not now*) · Live status (*Mark fulfilled / Refresh*) · Donor registration form · Donor profile summary

Every card also comes with a short plain-text version, so Blood Bridge works in text-only chats too: reply **yes** to confirm, **edit** to change, or type the details in one message (e.g. `Name: Arjun; Blood group: O+; Area: Koramangala; Phone: 98765 43210`). It remembers what it just asked for, so missing details can come in the next message.

## Checked details
Donor sign-ups are checked before they're saved: a valid 10-digit Indian mobile number, an area found on the map, a real first name, the eligibility tick, and a last-donation date that isn't in the future. The donor then sees a profile summary (phone masked) to confirm their details.

## Coverage
Bengaluru for now. If a request is for another city (Mumbai, Delhi, Chennai…), Blood Bridge says so clearly and points the family to e-RaktKosh live stock, the hospital's own blood bank and local helplines, instead of pretending to match donors.

## Privacy
- Donors share only their first name, blood group, area, last donation date and phone number.
- A donor's phone number is shared with the family **only after the donor taps "I can donate"**.
- `Delete my donor profile` removes everything.
- Blood Bridge never asks for or handles money.

## Medical note
Compatibility is for red cells / whole blood, and the hospital blood bank always cross-matches. Eligibility is a simple pre-check (18–65 years, at least 45 kg, 90 days between donations); the blood bank's screening decides. Always call the blood bank to confirm stock.

## Built with
Fetch.ai Agentverse (hosted uAgent) · Agent Chat Protocol · **ASI-1 as the only LLM** · ASI:One Interactive Cards · Agent storage · TomTom Search & Routing · e-RaktKosh

**Try it live:** https://asi1.ai/ai/agent1qwmsdzdktw8xrl8tz3zhahwr54nw32u9efwq9u57pw0629pa8ldeywy9def (or search `@blood-bridge-agent` on ASI:One)
**Code:** https://github.com/phani06041/blood-bridge
**Demo:** https://youtu.be/FusOGbrEeo4

*Built for the Fetch.ai "Get your agent hired" challenge at Stranger Builds 2026.*
