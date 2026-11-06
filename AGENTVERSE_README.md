# 🩸 Blood Bridge: urgent blood, found faster

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)
![domain:health](https://img.shields.io/badge/health-C41E3A)

**Blood Bridge turns an urgent blood request into a verified, live hunt across nearby blood banks and opt-in donors in Bengaluru, all inside one ASI:One chat.**

In India, urgent blood requests travel as WhatsApp forwards: unverified, sent to random people, never closed, and copied by scammers who ask for "processing fees". Blood Bridge verifies the request first, sends the family to the nearest blood banks, shows it only to compatible donors nearby, and closes it when it's fulfilled.

## Key features
- **Verifies before alerting anyone:** checks the hospital is on the map, there's a contact to call, and the units are plausible
- **Blocks scams:** requests asking donors for money, UPI, a "processing fee" or an OTP are stopped with a clear reason
- **Nearest blood banks first:** real blood banks near the hospital with distance and phone number, plus live government stock on e-RaktKosh
- **Smart donor matching:** only donors who are compatible (red-cell rules), within 15 km and eligible (90+ days since last donation)
- **Live tracking and a safe demo:** donors tap *I can donate*, the family sees it live, *Mark fulfilled* closes it; **try a demo** runs the whole flow without alerting real donors

## Usage
Just say **hi** to see the menu, or type a message:

| You want to… | Say |
|---|---|
| Try it safely | `try a demo` |
| Request blood | `Need 1 unit O+ at Manipal Hospital Old Airport Road today, contact Ravi 98765 43210` |
| Confirm a checked request | `yes` (or `edit` to change it) |
| See your requests | `my requests` · `status BB-1234` · `mark BB-1234 fulfilled` |
| Become a donor | `register me as a donor`, or send `Name: Arjun; Blood group: O+; Area: Koramangala; Phone: 98765 43210` |
| Help as a donor | `requests near me` · `I can donate BB-1234` |
| Leave | `exit demo` · `delete my donor profile` |
| Learn more | `why does this matter?` |

Works with ASI:One Interactive Cards (menu, request form, verification review, donor alert, live status, donor sign-up) and in plain text: every card also comes with a short text version.

## Use cases
- **A family in an emergency:** a parent needs 2 units of O– for surgery today; Blood Bridge checks the request, lists the 3 nearest blood banks to call now, and shows it to compatible donors nearby
- **A regular donor:** registers once, then opens Blood Bridge to see requests within 15 km that match their blood group, and taps *I can donate*
- **Stopping a scam:** a forwarded "pay ₹500 processing fee to UPI" request is flagged before any donor sees it
- **Ending stale forwards:** the family marks the request fulfilled, so it disappears for every donor and stops circulating
- **Trying it out:** a judge, NGO or hospital team runs the demo to see the full flow with sample donors and real blood-bank data

## Limitations
- **Bengaluru only for now.** Requests from other cities get a clear note and pointers to e-RaktKosh and the hospital's blood bank
- **Donors see requests when they open Blood Bridge.** ASI:One doesn't let agents message other users unprompted, so alerts are "pull"; optional email alerts need the operator's Brevo setup
- **Not a medical service.** Compatibility is for red cells / whole blood only (not platelets or plasma); the hospital blood bank always cross-matches and screens donors
- **Blood-bank stock isn't guaranteed.** Always call the blood bank to confirm; listings come from TomTom places data
- **Small donor network today.** It grows as donors register; the WhatsApp share reaches people who haven't

## Metadata
| | |
|---|---|
| **Name** | Blood Bridge |
| **Handle** | `@blood-bridge-agent` |
| **Address** | `agent1qwmsdzdktw8xrl8tz3zhahwr54nw32u9efwq9u57pw0629pa8ldeywy9def` |
| **Category** | Health · Emergency · Community |
| **Coverage** | Bengaluru, India |
| **Languages** | English |
| **Protocol** | Agent Chat Protocol v0.3.0 |
| **LLM** | ASI-1 (the only LLM) |
| **Built with** | Fetch.ai Agentverse (hosted uAgent) · ASI:One Interactive Cards · Agent storage · TomTom Search & Routing · e-RaktKosh |
| **Pricing** | Free |
| **Privacy** | Donors share first name, blood group, area, last donation date and phone; the phone is shared only after they tap *I can donate*; `delete my donor profile` removes everything; never asks for or handles money |
| **Code** | https://github.com/phani06041/blood-bridge |
| **Demo video** | https://youtu.be/FusOGbrEeo4 |
| **Author** | Phanindra Maddipatla |
| **Built for** | Fetch.ai "Get your agent hired" challenge, Stranger Builds 2026 (Best of the Day, Bengaluru) |
| **Version** | 1.3 (Nov 2026): sandbox demo, text-only support, concise replies |
