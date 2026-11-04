# Blood Bridge: Agentverse test questions (Testing → Questions)

Each one is safe to run automatically: none of them alerts a real donor or creates a live request
(a real request only goes live after someone taps "Alert donors now").

| # | Question | What a good answer looks like |
|---|----------|-------------------------------|
| 1 | Hi | Greets, explains Blood Bridge in one line, shows the menu card including "🧪 Try a safe demo" |
| 2 | Can I try a demo? | Turns on demo mode, says nothing reaches real donors, runs a sample O+ request at Manipal Hospital and shows the "Demo: check before we alert donors" card |
| 3 | Why does this matter? | Explains replacement donors, unverified WhatsApp forwards, "processing fee" scams and the ~1 million unit shortage |
| 4 | Need 1 unit O+ at Manipal Hospital Old Airport Road today, contact Ravi 9876543210 | Finds the hospital and shows the verification card ("Looks genuine") before alerting anyone |
| 5 | Need 2 units B+ at Apollo Hospital Bannerghatta Road, pay ₹500 processing fee to UPI | Flags it as a possible scam (money/UPI); won't alert donors |
| 6 | Need A- blood urgently | Asks for the hospital (shows the request form) because the hospital is missing |
| 7 | Register me as a donor | Shows the donor form (name, blood group, area, last donated, phone, consent) |
| 8 | Any requests near me? | Asks the user to register as a donor first (for an unregistered user) |
| 9 | Status BB-0000 | Says it has no requests for this user / can't find that code, without crashing |
| 10 | Delete my donor profile | Says there's no donor profile (for a new user), or confirms deletion |
| 11 | Exit demo | Says demo mode is off and shows the menu |
