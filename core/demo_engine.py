"""Offline DEMO engine – rule-based, NOT AI.

Used only when the user explicitly switches on Demo mode (e.g. no API key during a
presentation). It uses keyword matching, regular expressions and fixed templates.
Every result is labelled source="demo" and shown with a "Demo mode – not AI" banner.
It is never used as a silent fallback when the API fails.
"""
from __future__ import annotations

import re

from .legal_sources import laws_for_area, resources_for_area

DEMO_MODEL = "offline-demo-engine (rule-based, not AI)"

_KEYWORDS = {
    "tenancy": ["deposit", "landlord", "tenant", "rent", "vacat", "lease", "flat", "kiraya",
                "makan malik", "मकान", "किराय", "जमा"],
    "employment": ["salary", "employer", "wages", "hr ", "company", "unpaid", "job",
                   "tankhwah", "वेतन", "तनख्वाह", "नौकरी"],
    "consumer": ["refund", "defective", "product", "order", "seller", "delivery", "online",
                 "amazon", "flipkart", "warranty", "रिफंड", "सामान"],
    "cyber": ["otp", "fraud", "hacked", "scam", "upi fraud"],
}

_TYPE_LABEL = {
    "tenancy": "Security deposit not refunded",
    "employment": "Unpaid salary",
    "consumer": "Defective product – refund not given",
    "cyber": "Possible online fraud",
    "general": "General legal query",
}


def _result(task, data, warnings=None):
    from .legal_ai import TaskResult  # local import avoids a cycle
    return TaskResult(task=task, data=data, source="demo", model=DEMO_MODEL,
                      raw_outputs=[], citation_warnings=warnings or [])


def _area(text: str) -> str:
    low = text.lower()
    scores = {a: sum(low.count(k) for k in kws) for a, kws in _KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def _amount(text: str):
    m = re.search(r"(?:₹|rs\.?|inr|rupees)\s*([\d,]+(?:\.\d+)?)", text, flags=re.I) or \
        re.search(r"([\d,]{3,}(?:\.\d+)?)\s*(?:rupees|rs\b|/-|₹)", text, flags=re.I)
    if not m:
        return None
    try:
        return int(float(m.group(1).replace(",", "")))
    except ValueError:
        return None


_DATE_RE = (r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|"
            r"Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s*\d{0,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|"
            r"Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}?,?\s*\d{4})")


def chat_reply(history, language):
    user_text = " ".join(m["content"] for m in history if m["role"] == "user")
    area = _area(user_text)
    missing = []
    if _amount(user_text) is None:
        missing.append("What is the exact amount involved (in ₹)?")
    if not re.search(_DATE_RE, user_text, flags=re.I):
        missing.append("When did the key events happen (approximate dates)?")
    if not re.search(r"\b(in|at|from)\s+[A-Z][a-z]+", user_text):
        missing.append("Which city and state are you in? Rules can differ by state.")
    if not re.search(r"agreement|receipt|email|whatsapp|message|invoice|bill|slip|statement",
                     user_text, flags=re.I):
        missing.append("What written proof do you have (agreement, receipts, messages, emails)?")
    missing = missing[:3]
    if missing:
        reply = ("[Demo mode – rule-based reply, not AI] Thank you for explaining. To build your "
                 "case summary I need a few more details:\n" +
                 "\n".join(f"• {q}" for q in missing))
    else:
        reply = ("[Demo mode – rule-based reply, not AI] Thank you – I have the key details. "
                 "Open the Case Builder to generate your structured case summary.")
    return _result("chat", {"reply": reply, "language": "English",
                            "follow_up_questions": missing,
                            "ready_for_case_summary": not missing or area != "general"})


def classify(narrative):
    area = _area(narrative)
    return _result("classify", {
        "issue_area": area, "issue_type": _TYPE_LABEL.get(area, _TYPE_LABEL["general"]),
        "language": "English", "summary": narrative[:160].strip(),
        "urgency": "medium", "confidence": "low", "needs_lawyer_urgently": False})


def extract_facts(narrative):
    area = _area(narrative)
    amt = _amount(narrative)
    dates = [d.strip() for d in re.findall(_DATE_RE, narrative, flags=re.I)]
    roles = {"tenancy": [("Not stated", "Tenant (user)"), ("Not stated", "Landlord")],
             "employment": [("Not stated", "Employee (user)"), ("Not stated", "Employer")],
             "consumer": [("Not stated", "Customer (user)"), ("Not stated", "Seller / platform")]}
    evidence = [w for w in ["agreement", "receipt", "email", "whatsapp", "messages", "invoice",
                            "bank statement", "salary slip", "photos", "order"]
                if w in narrative.lower()]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", narrative) if s.strip()]
    return _result("extract_facts", {
        "case_title": f"{_TYPE_LABEL.get(area, 'Legal matter')} (demo extraction)",
        "issue_type": _TYPE_LABEL.get(area, _TYPE_LABEL["general"]),
        "location": "",
        "people_involved": [{"name": n, "role": r} for n, r in roles.get(area, [])],
        "timeline": [{"date": "Not stated", "event": s} for s in sentences[:6]],
        "important_dates": [{"date": d, "description": "Date mentioned by user"} for d in dates],
        "amount_involved": {"value": amt, "currency": "INR",
                            "description": "Amount mentioned by user" if amt else ""},
        "evidence_available": [e.title() for e in evidence],
        "missing_information": ["Names of the parties", "Exact dates", "City / state",
                                "Copies of written communication"],
    })


_GUIDE = {
    "tenancy": {
        "overview": "This appears to be a dispute over the refund of a rental security deposit "
                    "after vacating. Whether deductions are allowed usually depends on the rental "
                    "agreement and the condition of the property.",
        "options": [("Written demand letter", "Send a dated letter/email asking for the refund "
                     "within a fixed time.", "Low cost; creates a written record."),
                    ("Mediation / Lok Adalat", "Seek a settlement through mediation or a Lok "
                     "Adalat via the District Legal Services Authority.", "Free or low cost; "
                     "needs both sides to cooperate."),
                    ("Civil remedy through a lawyer", "A lawyer can advise on a legal notice or "
                     "civil claim under the law applicable in your state.", "Costs time and "
                     "money; consider for larger amounts.")],
    },
    "employment": {
        "overview": "This appears to be a claim for unpaid salary. Employers generally must pay "
                    "earned wages on time; the exact process depends on your employment terms "
                    "and your state's labour authorities.",
        "options": [("Written salary request", "Email HR/management with the months and amount "
                     "due and request payment by a date.", "Creates a record; low cost."),
                    ("Complaint to the Labour Department", "Approach your state Labour "
                     "Department / Labour Commissioner office.", "Process and timelines vary by "
                     "state."),
                    ("Legal notice through a lawyer", "A lawyer can send a formal notice and "
                     "advise on further remedies.", "Advisable if the amount is large or you "
                     "were terminated.")],
    },
    "consumer": {
        "overview": "This appears to be a consumer complaint about a defective product bought "
                    "online and a refund that has not been given.",
        "options": [("Complain to seller/platform", "Use the platform's grievance officer / "
                     "customer support in writing.", "Fastest; keep ticket numbers."),
                    ("National Consumer Helpline", "Register a grievance by calling 1915 or "
                     "online at consumerhelpline.gov.in.", "Free; aims at pre-litigation "
                     "resolution."),
                    ("Consumer Commission via e-Daakhil", "File a complaint online with the "
                     "District Consumer Commission.", "Formal process; may take months.")],
    },
}


def guidance(facts, area):
    g = _GUIDE.get(area, {"overview": "The issue could not be classified by the demo engine.",
                          "options": []})
    amt = (facts.get("amount_involved") or {}).get("value")
    confirmed = [f"Issue type: {facts.get('issue_type', '')}"]
    if amt:
        confirmed.append(f"Amount involved: ₹{amt:,}")
    confirmed += [f"Evidence mentioned: {e}" for e in facts.get("evidence_available", [])]
    data = {
        "issue_overview": "[Demo mode – template guidance, not AI] " + g["overview"],
        "confirmed_facts": confirmed,
        "assumptions": ["The demo engine uses templates and cannot assess the specific facts."],
        "legal_options": [{"option": o, "description": d, "considerations": c}
                          for o, d, c in g["options"]],
        "next_steps": [{"step": "Collect documents", "details": "Gather all proofs listed in the "
                        "Evidence Checklist."},
                       {"step": "Send a written request", "details": "Use the Document "
                        "Generator to prepare a draft and send it by email and/or registered "
                        "post."},
                       {"step": "Use official channels", "details": "; ".join(
                           f"{r['name']} – {r['url']}" for r in resources_for_area(area))}],
        "documents_to_collect": facts.get("evidence_available", []) or ["Agreement", "Receipts"],
        "when_to_consult_lawyer": ["If the other side sends a legal notice or threatens action",
                                   "If the amount is large or deadlines are involved",
                                   "Before filing any court case"],
        "laws_referenced": [{"name": l["name"], "relevance": l["note"]}
                            for l in laws_for_area(area) if area in l["areas"]][:2],
        "uncertainty_notes": ["Demo mode does not analyse your facts. Use AI mode or consult a "
                              "lawyer / free legal aid for case-specific information."],
    }
    return _result("guidance", data)


_DOC = {
    "deposit_refund": ("Request for Refund of Security Deposit", "[Landlord's name]",
                       "Request for refund of security deposit of ₹{amt}",
                       "I was a tenant at [property address] from [start date] to [date of "
                       "vacating]. At the start of the tenancy I paid a security deposit of "
                       "₹{amt}. I vacated the property on [date] and handed over the keys. "
                       "Despite my requests, the deposit has not been refunded.\n\nI request you "
                       "to refund ₹{amt} (less any deduction you can justify in writing with "
                       "supporting bills) within 15 days of this letter, to [bank details / UPI "
                       "ID].",
                       ["Rental agreement", "Deposit payment receipt / bank statement",
                        "Proof of vacating (handover message, photos)", "Earlier messages"]),
    "salary_request": ("Request for Payment of Pending Salary", "[HR Manager / Employer name]",
                       "Request for payment of pending salary – ₹{amt}",
                       "I have been working as [designation] since [joining date]. My salary "
                       "for [month 1] and [month 2] has not been paid, amounting to ₹{amt}. I "
                       "have raised this on [dates] but have not received payment.\n\nI request "
                       "you to pay the pending amount within 15 days of this letter and to "
                       "confirm the payment date in writing.",
                       ["Appointment / offer letter", "Salary slips", "Bank statements showing "
                        "non-payment", "Attendance records", "Emails to HR"]),
    "consumer_refund": ("Complaint and Request for Refund", "[Seller / Grievance Officer]",
                        "Complaint regarding defective product – Order [order number] – "
                        "refund of ₹{amt}",
                        "On [order date] I purchased [product name] for ₹{amt} (Order "
                        "[number]). The product delivered on [delivery date] was defective: "
                        "[describe defect]. I reported this on [date] but have not received a "
                        "refund.\n\nI request a full refund of ₹{amt} within 15 days. If not "
                        "resolved, I may approach the National Consumer Helpline or the "
                        "Consumer Commission.",
                        ["Order confirmation / invoice", "Payment proof", "Photos/video of "
                         "defect", "Complaint ticket numbers and emails"]),
}


def document(facts, doc_key, sender_details=""):
    title, recipient, subject, body, attach = _DOC[doc_key]
    amt = (facts.get("amount_involved") or {}).get("value")
    amt_s = f"{amt:,}" if amt else "[amount]"
    full = (f"Dear {recipient},\n\n" + body.format(amt=amt_s) +
            "\n\nI have attached copies of the supporting documents.\n\nYours sincerely,\n"
            f"{sender_details or '[Your name]'}\n[Phone] | [Email]")
    return _result(f"document:{doc_key}", {
        "title": title + " (demo template)", "recipient_name": recipient,
        "recipient_address": "[Recipient address]", "sender_name": sender_details or "[Your name]",
        "sender_address": "[Your address]", "date": "[Date]",
        "subject": subject.format(amt=amt_s), "body": full, "supporting_documents": attach,
        "placeholders_to_fill": sorted(set(re.findall(r"\[[^\]]+\]", full)))})


def checklist(facts):
    base = [("Agreements", "Written agreement / contract / offer letter", "Proves the terms",
             "high"),
            ("Receipts", "Payment receipts or invoices", "Proves the amount paid", "high"),
            ("Bank statements", "Bank / UPI statements showing the transaction", "Independent "
             "proof of payment", "high"),
            ("Messages", "WhatsApp/SMS messages with the other party", "Shows your requests and "
             "their replies", "medium"),
            ("Emails", "Emails sent and received", "Dated written record", "medium"),
            ("Notices", "Any notice or letter sent or received", "Shows formal demand", "medium"),
            ("Identity/Address proof", "Your ID and address proof", "Needed for complaints",
             "low")]
    return _result("checklist", {"items": [
        {"category": c, "item": i, "why_needed": w, "priority": p} for c, i, w, p in base]})
