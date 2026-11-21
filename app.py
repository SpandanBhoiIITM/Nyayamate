"""NyayaMate AI – Indian everyday legal information assistant (Streamlit prototype).

Run:  streamlit run app.py
"""
from __future__ import annotations

import html
import re

import pandas as pd
import streamlit as st

from core import legal_ai, storage
from core.ai_client import AIServiceError, OpenRouterClient
from core.config import DEFAULT_MODEL, LANGUAGES, SUGGESTED_MODELS, get_env_api_key
from core.legal_sources import ISSUE_AREAS, VERIFIED_LAWS, resources_for_area
from core.prompts import DOCUMENT_TYPES
from core.ui_styles import CSS

st.set_page_config(page_title="NyayaMate AI – Legal Assistant", page_icon="⚖️",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)

PAGES = ["🏠  Home", "💬  Legal Chat", "🗂️  Case Builder", "🧭  Legal Guidance",
         "📝  Document Generator", "✅  Evidence Checklist", "📚  Case History", "⚙️  Settings"]

DISCLAIMER = ("<b>Important:</b> NyayaMate AI provides general legal <i>information</i>, not "
              "legal advice. It is not a law firm, does not represent you, and can make "
              "mistakes. Verify laws on <a href='https://www.indiacode.nic.in' target='_blank'>"
              "India Code</a> and consult a qualified lawyer – or free legal aid via NALSA "
              "(helpline 15100) – for urgent, complex or high-value matters.")

DOC_LABELS = {"deposit_refund": "🏠 Rental security deposit refund request",
              "salary_request": "💼 Salary payment request",
              "consumer_refund": "🛒 Consumer refund complaint"}

CATEGORIES = [
    ("🏠", "Rent & Tenancy", "Security deposits, eviction notices, rent disputes.",
     "My landlord is not returning my security deposit."),
    ("💼", "Salary & Employment", "Unpaid salary, final settlement, wrongful deductions.",
     "My employer has not paid my salary."),
    ("🛒", "Consumer & Online Shopping", "Defective products, refunds, service failures.",
     "I received a defective product and have not got a refund."),
    ("🔐", "Cyber & UPI Fraud", "Online scams, unauthorised transactions.",
     "Money was taken from my account through an online scam."),
]

# ------------------------------------------------------------------ session state
ss = st.session_state
ss.setdefault("nav", PAGES[0])
ss.setdefault("model", DEFAULT_MODEL)
ss.setdefault("language_pref", "Auto-detect")
ss.setdefault("demo_mode", False)
ss.setdefault("session_api_key", "")
ss.setdefault("case", None)
ss.setdefault("last_error", None)

if "_goto" in ss:            # programmatic navigation (must happen before the radio renders)
    ss.nav = ss.pop("_goto")


def goto(page_prefix: str):
    ss["_goto"] = next(p for p in PAGES if page_prefix in p)
    st.rerun()


def api_key() -> str | None:
    return ss.session_api_key.strip() or get_env_api_key()


def client() -> OpenRouterClient | None:
    if ss.demo_mode:
        return None
    return OpenRouterClient(api_key(), ss.model)   # raises AIServiceError(missing_key)


def current_case() -> dict:
    if ss.case is None:
        ss.case = storage.new_case()
    return ss.case


def save():
    if ss.case is not None:
        storage.save_case(ss.case)


def narrative(case: dict) -> str:
    return "\n".join(m["content"] for m in case["messages"] if m["role"] == "user").strip()


def facts_of(case: dict) -> dict | None:
    if case.get("facts_edited"):
        return case["facts_edited"]
    return (case.get("facts") or {}).get("data")


def issue_area(case: dict) -> str:
    return ((case.get("classification") or {}).get("data") or {}).get("issue_area", "general")


def output_language(case: dict) -> str:
    if ss.language_pref != "Auto-detect":
        return ss.language_pref
    lang = ((case.get("classification") or {}).get("data") or {}).get("language", "")
    return lang if lang and "unknown" not in lang.lower() else "English"


def log_result(case: dict, result: legal_ai.TaskResult):
    case["ai_log"].append({"task": result.task, "source": result.source, "model": result.model,
                           "created_at": result.created_at, "raw_outputs": result.raw_outputs})


def run_task(label: str, fn, *args, **kwargs):
    """Run an AI task with a spinner and user-friendly error display. Never fakes output."""
    ss.last_error = None
    try:
        kwargs.setdefault("demo", ss.demo_mode)
        cl = client()
        with st.spinner(f"{label}…" + (" (demo engine)" if ss.demo_mode else f" ({ss.model})")):
            result = fn(cl, *args, **kwargs)
        log_result(current_case(), result)
        return result
    except AIServiceError as e:
        ss.last_error = {"kind": e.kind, "message": e.message, "detail": e.detail,
                         "raw": getattr(e, "raw_outputs", [])}
        if getattr(e, "raw_outputs", None):
            current_case()["ai_log"].append({"task": label, "source": "ai", "model": ss.model,
                                             "error": e.kind, "raw_outputs": e.raw_outputs})
            save()
        return None


def show_error():
    err = ss.get("last_error")
    if not err:
        return
    st.error(f"**AI request failed – {err['kind'].replace('_', ' ')}.** {err['message']}",
             icon="⚠️")
    if err.get("detail") or err.get("raw"):
        with st.expander("Technical details"):
            if err.get("detail"):
                st.code(err["detail"][:1500])
            for r in err.get("raw", []):
                st.text_area("Raw model output (unedited)", r, height=150, disabled=True)
    c1, c2 = st.columns([1, 3])
    if c1.button("Open Settings", key=f"err_settings_{err['kind']}"):
        goto("Settings")
    c2.caption("No AI output was generated, so nothing is shown. You can retry, change the "
               "model, or switch on clearly-labelled Demo mode in Settings.")


def source_badge(result: dict | None) -> str:
    if not result:
        return ""
    if result.get("source") == "demo":
        return "<span class='nm-badge demo'>DEMO ENGINE · not AI</span>"
    return (f"<span class='nm-badge ai'>AI · {html.escape(result.get('model', ''))}</span>"
            f"<span class='nm-badge grey'>{html.escape(result.get('created_at', ''))}</span>")


def demo_banner():
    if ss.demo_mode:
        st.markdown("<div class='nm-demo-banner'>🧪 Demo mode is ON – results come from a "
                    "rule-based template engine, <u>not</u> from AI. Turn it off in Settings "
                    "to use OpenRouter.</div>", unsafe_allow_html=True)


def citation_warnings(warnings: list[dict]):
    if not warnings:
        st.markdown("<span class='nm-badge ok'>✓ Citation check: no section numbers, case law "
                    "or unlisted laws detected</span>", unsafe_allow_html=True)
        return
    with st.expander(f"⚠️ Citation check: {len(warnings)} item(s) need verification",
                     expanded=True):
        for w in warnings:
            st.markdown(f"- **{html.escape(w['text'])}** ({w['type']}) – {w['message']}")


def disclaimer():
    st.markdown(f"<div class='nm-disclaimer'>⚖️ {DISCLAIMER}</div>", unsafe_allow_html=True)


def header(title: str, subtitle: str):
    st.markdown(f"## {title}")
    st.caption(subtitle)
    demo_banner()


def need_facts(case: dict) -> bool:
    if facts_of(case):
        return False
    st.info("No case summary yet. Describe your problem in **Legal Chat**, then build the "
            "summary in **Case Builder**.", icon="🗂️")
    c1, c2 = st.columns(2)
    if c1.button("Go to Legal Chat", key="nf_chat"):
        goto("Legal Chat")
    if c2.button("Go to Case Builder", key="nf_cb"):
        goto("Case Builder")
    return True


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("<div class='nm-brand'>Nyaya<span>Mate</span> AI</div>"
                "<div class='nm-tag'>Everyday legal help for India</div>",
                unsafe_allow_html=True)
    st.markdown("---")
    st.radio("Navigation", PAGES, key="nav", label_visibility="collapsed")
    st.markdown("---")
    case_sb = ss.case
    if case_sb:
        st.markdown(f"**Current case**  \n{html.escape(case_sb['title'])}  \n"
                    f"<small>Status: {case_sb['status']}</small>", unsafe_allow_html=True)
    else:
        st.markdown("<small>No case open</small>", unsafe_allow_html=True)
    if ss.demo_mode:
        mode = "🧪 Demo mode (not AI)"
    elif api_key():
        mode = "🟢 AI connected (key set)"
    else:
        mode = "🔴 No API key"
    st.markdown(f"<small>{mode}<br>Model: {html.escape(ss.model)}</small>",
                unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<small>Information only – not legal advice. Not a law firm.</small>",
                unsafe_allow_html=True)

page = ss.nav

# ================================================================== HOME
if "Home" in page:
    st.markdown(
        "<div class='nm-hero'><div class='nm-kicker'>Legal information · India</div>"
        "<h1>Namaste. Let's make sense of your legal problem.</h1>"
        "<p>Explain what happened in your own words – English, Hindi or another Indian "
        "language. NyayaMate organises your story into a case summary, explains possible "
        "options in plain language, drafts letters and builds your evidence checklist.</p>"
        "</div>", unsafe_allow_html=True)
    st.write("")
    c1, c2, c3 = st.columns([1.2, 1.2, 3])
    if c1.button("➕ Start New Case", type="primary", use_container_width=True):
        ss.case = storage.new_case()
        goto("Legal Chat")
    if ss.case and c2.button("↪ Continue current case", use_container_width=True):
        goto("Legal Chat")
    disclaimer()

    cases = storage.list_cases()
    s1, s2, s3, s4 = st.columns(4)
    with_facts = sum(1 for c in cases if c["status"] != "Gathering facts")
    for col, num, label in [(s1, len(cases), "Saved cases"),
                            (s2, with_facts, "Cases analysed"),
                            (s3, len(DOC_LABELS), "Letter templates"),
                            (s4, len(VERIFIED_LAWS), "Verified law references")]:
        col.markdown(f"<div class='nm-card'><div class='nm-stat'>{num}</div>"
                     f"<div class='nm-stat-label'>{label}</div></div>", unsafe_allow_html=True)

    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("### Legal assistance categories")
        g = st.columns(2)
        for i, (icon, name, desc, starter) in enumerate(CATEGORIES):
            with g[i % 2]:
                st.markdown(f"<div class='nm-card'><div class='nm-icon'>{icon}</div>"
                            f"<h4>{name}</h4><p>{desc}</p></div>", unsafe_allow_html=True)
                if st.button(f"Start a {name} case", key=f"cat_{i}", use_container_width=True):
                    ss.case = storage.new_case()
                    ss["chat_prefill"] = starter
                    goto("Legal Chat")
    with right:
        st.markdown("### Recent cases")
        if not cases:
            st.markdown("<div class='nm-card'><p>No saved cases yet. Start a new case to "
                        "begin.</p></div>", unsafe_allow_html=True)
        for c in cases[:5]:
            area = ISSUE_AREAS.get(c["issue_area"], "Unclassified")
            st.markdown(f"<div class='nm-card'><h4>{html.escape(c['title'])}</h4>"
                        f"<p><span class='nm-badge gold'>{area}</span>"
                        f"<span class='nm-badge grey'>{c['status']}</span><br>"
                        f"<small>Updated {c['updated_at'].replace('T', ' ')}</small></p></div>",
                        unsafe_allow_html=True)
            if st.button("Open", key=f"open_{c['id']}"):
                ss.case = storage.load_case(c["id"])
                goto("Case Builder")
        st.markdown("### How it works")
        for n, (t, d) in enumerate([("Explain", "Describe your problem in Legal Chat."),
                                    ("Organise", "Review the AI-built case summary."),
                                    ("Understand", "Read options and next steps."),
                                    ("Act", "Draft a letter and collect evidence.")], 1):
            st.markdown(f"<div class='nm-step'><div class='nm-step-num'>{n}</div>"
                        f"<div class='nm-step-body'><b>{t}</b><div>{d}</div></div></div>",
                        unsafe_allow_html=True)

# ================================================================== CHAT
elif "Legal Chat" in page:
    case = current_case()
    header("💬 Legal Chat", "Describe your problem naturally. NyayaMate will ask only the "
                           "questions that matter. Hindi and other Indian languages are welcome.")
    disclaimer()
    if not case["messages"]:
        st.markdown("<div class='nm-card'><h4>Tips for a good description</h4><p>Include: what "
                    "happened, when, how much money is involved, who the other party is, your "
                    "city/state, and what proof you have (agreement, receipts, messages).<br>"
                    "<i>उदाहरण: मैंने मार्च 2024 में ₹25,000 सिक्योरिटी डिपॉज़िट दिया था…</i>"
                    "</p></div>", unsafe_allow_html=True)
    for m in case["messages"]:
        with st.chat_message(m["role"], avatar="🧑" if m["role"] == "user" else "⚖️"):
            st.markdown(m["content"])
            if m["role"] == "assistant" and m.get("source") == "demo":
                st.markdown(source_badge({"source": "demo"}), unsafe_allow_html=True)
            if m.get("warnings"):
                citation_warnings(m["warnings"])
    show_error()

    prefill = ss.pop("chat_prefill", None)
    if prefill:
        st.info(f"Suggested start: “{prefill}” – type your own details below.", icon="💡")
    prompt = st.chat_input("Describe your legal problem…")
    if prompt:
        case["messages"].append({"role": "user", "content": prompt})
        if case["title"] == "Untitled case":
            case["title"] = (prompt[:60] + "…") if len(prompt) > 60 else prompt
        save()
        result = run_task("Thinking", legal_ai.chat_reply, case["messages"], ss.language_pref)
        if result:
            case["messages"].append({"role": "assistant", "content": result.data["reply"],
                                     "source": result.source,
                                     "warnings": result.citation_warnings})
            if result.data.get("ready_for_case_summary"):
                case["ready"] = True
            save()
        st.rerun()

    if case["messages"]:
        st.write("")
        c1, c2, c3 = st.columns([1.4, 1, 2.6])
        if c1.button("🗂️ Build case summary", type="primary"):
            goto("Case Builder")
        if c2.button("🧹 Clear chat"):
            case["messages"] = []
            save()
            st.rerun()
        if case.get("ready"):
            c3.success("Key facts collected – ready for the Case Builder.", icon="✅")

# ================================================================== CASE BUILDER
elif "Case Builder" in page:
    case = current_case()
    header("🗂️ Case Builder", "Turns your explanation into a structured case summary. Review "
                             "and correct everything – you know your case best.")
    text = narrative(case)
    with st.expander("Your description (from chat)" if text else
                     "No chat yet – type or paste your description here", expanded=not text):
        manual = st.text_area("Description", value=text, height=160,
                              help="Edits here are added to the case as a new message.",
                              key=f"desc_{case['id']}")
        if manual.strip() and manual.strip() != text:
            if st.button("Use this description"):
                case["messages"].append({"role": "user", "content": manual.strip()})
                if case["title"] == "Untitled case":
                    case["title"] = manual.strip()[:60]
                save()
                st.rerun()

    b1, b2 = st.columns([1.3, 3])
    analyse = b1.button("✨ Analyse & build summary" if not case.get("facts") else
                        "🔄 Re-run analysis", type="primary", disabled=not text)
    if case.get("facts_edited"):
        b2.caption("Re-running replaces your edited summary with a fresh AI version.")
    if analyse:
        cls = run_task("Classifying the issue", legal_ai.classify_legal_issue, text)
        if cls:
            case["classification"] = cls.to_dict()
            fx = run_task("Extracting case facts", legal_ai.extract_case_facts, text)
            if fx:
                case["facts"] = fx.to_dict()
                case["facts_edited"] = None
                case["title"] = fx.data["case_title"] or case["title"]
                case["status"] = "Summary ready"
                case["guidance"], case["checklist"] = None, None
        save()
        st.rerun()
    show_error()

    if case.get("classification") and case.get("facts"):
        cls = case["classification"]["data"]
        f = facts_of(case)
        st.markdown(source_badge(case["facts"]) +
                    (" <span class='nm-badge ok'>✎ Reviewed by user</span>"
                     if case.get("facts_edited") else
                     " <span class='nm-badge warn'>Not yet reviewed</span>"),
                    unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        amt = (f.get("amount_involved") or {}).get("value")
        for col, lbl, val in [(k1, "Issue area", ISSUE_AREAS.get(cls["issue_area"], "Other")),
                              (k2, "Urgency", cls["urgency"].title()),
                              (k3, "Amount", f"₹{amt:,.0f}" if isinstance(amt, (int, float))
                               else "Not stated"),
                              (k4, "Missing facts", str(len(f.get("missing_information", []))))]:
            col.markdown(f"<div class='nm-card'><div class='nm-stat-label'>{lbl}</div>"
                         f"<div class='nm-stat' style='font-size:1.25rem'>{html.escape(val)}"
                         f"</div></div>", unsafe_allow_html=True)
        if cls.get("needs_lawyer_urgently"):
            st.warning("This looks urgent or high-risk. Please contact a lawyer or your District "
                       "Legal Services Authority (NALSA helpline 15100) as soon as possible.",
                       icon="🚨")

        st.markdown("### Review and edit the case summary")
        ver = f"{case['id']}_{case['facts']['created_at']}"   # resets editors after re-analysis
        with st.form(f"facts_form_{ver}"):
            c1, c2 = st.columns(2)
            title = c1.text_input("Case title", f.get("case_title", ""))
            itype = c2.text_input("Type of legal issue", f.get("issue_type", ""))
            c3, c4, c5 = st.columns([1, 1, 2])
            location = c3.text_input("Location (city/state)", f.get("location", ""))
            amt_val = c4.number_input("Amount involved (₹)", min_value=0.0, step=500.0,
                                      value=float(amt) if isinstance(amt, (int, float)) else 0.0)
            amt_desc = c5.text_input("What the amount is for",
                                     (f.get("amount_involved") or {}).get("description", ""))
            st.markdown("**People involved**")
            people = st.data_editor(pd.DataFrame(f.get("people_involved") or [],
                                                 columns=["name", "role"]),
                                    num_rows="dynamic", use_container_width=True,
                                    key=f"pe_{ver}")
            st.markdown("**Timeline of events**")
            timeline = st.data_editor(pd.DataFrame(f.get("timeline") or [],
                                                   columns=["date", "event"]),
                                      num_rows="dynamic", use_container_width=True,
                                      key=f"tl_{ver}")
            st.markdown("**Important dates**")
            dates = st.data_editor(pd.DataFrame(f.get("important_dates") or [],
                                                columns=["date", "description"]),
                                   num_rows="dynamic", use_container_width=True,
                                   key=f"dt_{ver}")
            c6, c7 = st.columns(2)
            evidence = c6.text_area("Available evidence (one per line)",
                                    "\n".join(f.get("evidence_available", [])), height=130)
            missing = c7.text_area("Missing information (one per line)",
                                   "\n".join(f.get("missing_information", [])), height=130)
            if st.form_submit_button("💾 Save reviewed summary", type="primary"):
                def rows(df):
                    return [{k: ("" if pd.isna(v) else str(v)) for k, v in r.items()}
                            for r in df.to_dict("records") if any(not pd.isna(v) and str(v).strip()
                                                                   for v in r.values())]
                case["facts_edited"] = {
                    "case_title": title, "issue_type": itype, "location": location,
                    "people_involved": rows(people), "timeline": rows(timeline),
                    "important_dates": rows(dates),
                    "amount_involved": {"value": amt_val or None, "currency": "INR",
                                        "description": amt_desc},
                    "evidence_available": [x.strip() for x in evidence.splitlines() if x.strip()],
                    "missing_information": [x.strip() for x in missing.splitlines() if x.strip()],
                }
                case["title"] = title or case["title"]
                case["status"] = "Summary reviewed"
                save()
                st.success("Summary saved.")
                st.rerun()
        if f.get("missing_information"):
            st.info("**Still missing:** " + "; ".join(f["missing_information"]) +
                    "  \nAdd these in Legal Chat for better guidance.", icon="❓")
        n1, n2, n3 = st.columns(3)
        if n1.button("🧭 Get legal guidance", type="primary"):
            goto("Legal Guidance")
        if n2.button("📝 Draft a document"):
            goto("Document Generator")
        if n3.button("✅ Evidence checklist"):
            goto("Evidence Checklist")
        with st.expander("Raw AI output (unedited)"):
            for r in (case["classification"].get("raw_outputs") or []) + \
                     (case["facts"].get("raw_outputs") or []):
                st.code(r, language="json")
            if case["facts"].get("source") == "demo":
                st.caption("Demo engine – no AI output.")

# ================================================================== GUIDANCE
elif "Legal Guidance" in page:
    case = current_case()
    header("🧭 Legal Guidance", "Plain-language information about your options. Confirmed "
                               "facts and assumptions are shown separately.")
    disclaimer()
    if not need_facts(case):
        area = issue_area(case)
        lang = output_language(case)
        c1, c2 = st.columns([1.3, 3])
        if c1.button("✨ Generate guidance" if not case.get("guidance") else "🔄 Regenerate",
                     type="primary"):
            r = run_task("Preparing guidance", legal_ai.generate_legal_guidance,
                         facts_of(case), area, lang)
            if r:
                case["guidance"] = r.to_dict()
                case["status"] = "Guidance ready"
                save()
            st.rerun()
        c2.caption(f"Based on: {'your reviewed summary' if case.get('facts_edited') else 'the AI summary (not yet reviewed)'}"
                   f" · Language: {lang}")
        show_error()
        gres = case.get("guidance")
        if gres:
            g = gres["data"]
            st.markdown(source_badge(gres), unsafe_allow_html=True)
            citation_warnings(gres.get("citation_warnings", []))
            st.markdown("### What the issue appears to be")
            st.markdown(f"<div class='nm-card'><p style='font-size:1rem'>"
                        f"{html.escape(g['issue_overview'])}</p></div>", unsafe_allow_html=True)
            a, b = st.columns(2)
            with a:
                st.markdown("#### ✅ Confirmed facts (from your summary)")
                for x in g["confirmed_facts"] or ["—"]:
                    st.markdown(f"- {x}")
            with b:
                st.markdown("#### ❔ Assumptions (please verify)")
                for x in g["assumptions"] or ["None stated"]:
                    st.markdown(f"- {x}")
            st.markdown("### Possible options")
            cols = st.columns(max(1, min(3, len(g["legal_options"]))))
            for i, o in enumerate(g["legal_options"]):
                with cols[i % len(cols)]:
                    st.markdown(f"<div class='nm-card'><h4>{html.escape(o['option'])}</h4>"
                                f"<p>{html.escape(o['description'])}</p><p style='margin-top:"
                                f".5rem'><small><b>Consider:</b> {html.escape(o['considerations'])}"
                                f"</small></p></div>", unsafe_allow_html=True)
            st.markdown("### Practical next steps")
            st.markdown("".join(
                f"<div class='nm-step'><div class='nm-step-num'>{n}</div><div class='nm-step-body'>"
                f"<b>{html.escape(s['step'])}</b><div>{html.escape(s['details'])}</div></div></div>"
                for n, s in enumerate(g["next_steps"], 1)), unsafe_allow_html=True)
            a, b = st.columns(2)
            with a:
                st.markdown("### 📎 Documents / evidence to collect")
                for x in g["documents_to_collect"]:
                    st.markdown(f"- {x}")
            with b:
                st.markdown("### 👩‍⚖️ When to get a lawyer")
                for x in g["when_to_consult_lawyer"]:
                    st.markdown(f"- {x}")
            st.markdown("### Laws mentioned")
            verified = {l["name"].lower() for l in VERIFIED_LAWS}
            if not g["laws_referenced"]:
                st.caption("No specific law named – NyayaMate prefers no citation over an "
                           "unverified one.")
            for l in g["laws_referenced"]:
                ok = l["name"].strip().lower() in verified
                badge = ("<span class='nm-badge ok'>On verified list</span>" if ok else
                         "<span class='nm-badge warn'>Not verified – check India Code</span>")
                st.markdown(f"- **{html.escape(l['name'])}** {badge} – "
                            f"{html.escape(l['relevance'])}", unsafe_allow_html=True)
            st.markdown("### Official resources (curated, not AI-generated)")
            for r in resources_for_area(area):
                st.markdown(f"- [{r['name']}]({r['url']})")
            if g["uncertainty_notes"]:
                st.warning("**Uncertain or state-specific:**\n\n" +
                           "\n".join(f"- {x}" for x in g["uncertainty_notes"]), icon="🔎")
            with st.expander("Raw AI output (unedited)"):
                for r in gres.get("raw_outputs") or ["Demo engine – no AI output."]:
                    st.code(r, language="json")

# ================================================================== DOCUMENTS
elif "Document Generator" in page:
    case = current_case()
    header("📝 Document Generator", "Creates an editable DRAFT letter from your case summary. "
                                   "Always review and fill in the placeholders before sending.")
    disclaimer()
    if not need_facts(case):
        f = facts_of(case)
        keys = list(DOC_LABELS)
        default = legal_ai.suggest_document_type(issue_area(case), f)
        c1, c2, c3 = st.columns([2, 1.2, 2])
        doc_key = c1.selectbox("Document type", keys, index=keys.index(default),
                               format_func=lambda k: DOC_LABELS[k])
        lang_opts = ["English", output_language(case)] if output_language(case) != "English" \
            else ["English", "Hindi"]
        lang = c2.selectbox("Language", lang_opts)
        sender = c3.text_input("Your name & contact (optional)",
                               help="Used as the sender. Leave blank to get a placeholder.")
        if st.button("✨ Generate draft" if doc_key not in case["documents"] else "🔄 Regenerate",
                     type="primary"):
            r = run_task("Drafting document", legal_ai.generate_legal_document, f, doc_key,
                         issue_area(case), lang, sender)
            if r:
                case["documents"][doc_key] = r.to_dict()
                case["documents_edited"].pop(doc_key, None)
                case["status"] = "Document drafted"
                save()
            st.rerun()
        show_error()
        dres = case["documents"].get(doc_key)
        if dres:
            d = dres["data"]
            st.markdown(source_badge(dres), unsafe_allow_html=True)
            citation_warnings(dres.get("citation_warnings", []))
            composed = (f"{d['sender_name']}\n{d['sender_address']}\n\n{d['date']}\n\nTo,\n"
                        f"{d['recipient_name']}\n{d['recipient_address']}\n\n"
                        f"Subject: {d['subject']}\n\n{d['body']}")
            left, right = st.columns([1.5, 1])
            with left:
                st.markdown("<span class='nm-draft-stamp'>DRAFT – REVIEW BEFORE SENDING</span>",
                            unsafe_allow_html=True)
                edited = st.text_area("Edit your letter", case["documents_edited"].get(
                    doc_key, composed), height=520, key=f"doc_{case['id']}_{doc_key}_{dres['created_at']}")
                s1, s2, s3 = st.columns(3)
                if s1.button("💾 Save edits"):
                    case["documents_edited"][doc_key] = edited
                    save()
                    st.success("Saved.")
                header_txt = ("DRAFT – generated by NyayaMate AI. Not legal advice. Review all "
                              "facts and fill placeholders before sending.\n" + "=" * 60 + "\n\n")
                s2.download_button("⬇ Download .txt", header_txt + edited,
                                   file_name=f"{doc_key}_draft.txt")
                s3.download_button("⬇ Download .md", f"> **DRAFT – review before sending.**\n\n"
                                   + edited.replace("\n", "  \n"),
                                   file_name=f"{doc_key}_draft.md")
            with right:
                st.markdown("<div class='nm-card'><h4>📎 Attach these</h4>" +
                            "".join(f"<p>• {html.escape(x)}</p>"
                                    for x in d["supporting_documents"]) + "</div>",
                            unsafe_allow_html=True)
                remaining = [p for p in d["placeholders_to_fill"] if p in edited] or \
                    sorted({p for p in re.findall(r"\[[^\]]+\]", edited)})
                st.markdown("<div class='nm-card'><h4>✏️ Fill in before sending</h4>" +
                            ("".join(f"<p>• {html.escape(x)}</p>" for x in remaining)
                             if remaining else "<p>No placeholders left.</p>") + "</div>",
                            unsafe_allow_html=True)
                st.markdown("<div class='nm-card'><h4>How to send</h4><p>Send by email and by "
                            "registered post / speed post with acknowledgement, and keep "
                            "copies and receipts.</p></div>", unsafe_allow_html=True)
            with st.expander("Raw AI output (unedited)"):
                for r in dres.get("raw_outputs") or ["Demo engine – no AI output."]:
                    st.code(r, language="json")

# ================================================================== CHECKLIST
elif "Evidence Checklist" in page:
    case = current_case()
    header("✅ Evidence Checklist", "What to collect for your case. Tick items as you gather "
                                   "them – progress is saved.")
    if not need_facts(case):
        if st.button("✨ Generate checklist" if not case.get("checklist") else "🔄 Regenerate",
                     type="primary"):
            r = run_task("Building checklist", legal_ai.generate_evidence_checklist,
                         facts_of(case))
            if r:
                case["checklist"] = r.to_dict()
                case["checklist_state"] = {}
                save()
            st.rerun()
        show_error()
        cres = case.get("checklist")
        if cres:
            items = cres["data"]["items"] + case.get("custom_items", [])
            state = case["checklist_state"]
            done = sum(1 for i in range(len(items)) if state.get(str(i)))
            st.markdown(source_badge(cres), unsafe_allow_html=True)
            st.progress(done / len(items) if items else 0.0,
                        text=f"{done} of {len(items)} collected")
            cats: dict[str, list[int]] = {}
            for i, it in enumerate(items):
                cats.setdefault(it["category"] or "Other", []).append(i)
            pri = {"high": "🔴 High", "medium": "🟠 Medium", "low": "⚪ Low"}
            changed = False
            for cat, idxs in cats.items():
                st.markdown(f"#### {cat}")
                for i in idxs:
                    it = items[i]
                    c1, c2 = st.columns([4, 1])
                    val = c1.checkbox(f"**{it['item']}** — {it['why_needed']}",
                                      value=bool(state.get(str(i))),
                                      key=f"chk_{case['id']}_{cres['created_at']}_{i}")
                    c2.markdown(f"<small>{pri.get(it['priority'], it['priority'])}</small>",
                                unsafe_allow_html=True)
                    if val != bool(state.get(str(i))):
                        state[str(i)] = val
                        changed = True
            if changed:
                save()
                st.rerun()
            with st.form("add_item", clear_on_submit=True):
                a1, a2 = st.columns([1, 3])
                cat = a1.selectbox("Category", ["Agreements", "Receipts", "Emails", "Messages",
                                                "Bank statements", "Notices", "Other"])
                new = a2.text_input("Add your own item")
                if st.form_submit_button("➕ Add item") and new.strip():
                    case.setdefault("custom_items", []).append(
                        {"category": cat, "item": new.strip(), "why_needed": "Added by you",
                         "priority": "medium"})
                    save()
                    st.rerun()
            with st.expander("Raw AI output (unedited)"):
                for r in cres.get("raw_outputs") or ["Demo engine – no AI output."]:
                    st.code(r, language="json")

# ================================================================== HISTORY
elif "Case History" in page:
    header("📚 Case History", "Cases are saved locally on this computer as JSON files in "
                             "data/cases/.")
    cases = storage.list_cases()
    if not cases:
        st.info("No saved cases yet.")
    q = st.text_input("Search cases", placeholder="e.g. deposit") if cases else ""
    for c in cases:
        if q and q.lower() not in c["title"].lower():
            continue
        area = ISSUE_AREAS.get(c["issue_area"], "Unclassified")
        with st.container(border=True):
            a, b, cc, d = st.columns([4, 1, 1, 1])
            a.markdown(f"**{html.escape(c['title'])}**  \n<span class='nm-badge gold'>{area}</span>"
                       f"<span class='nm-badge grey'>{c['status']}</span> "
                       f"<small>{c['updated_at'].replace('T', ' ')}</small>",
                       unsafe_allow_html=True)
            if b.button("Open", key=f"h_open_{c['id']}"):
                ss.case = storage.load_case(c["id"])
                goto("Case Builder")
            full = storage.load_case(c["id"])
            cc.download_button("Export", storage.export_case(full) if full else "{}",
                               file_name=f"case_{c['id']}.json", key=f"h_exp_{c['id']}")
            if d.button("Delete", key=f"h_del_{c['id']}"):
                storage.delete_case(c["id"])
                if ss.case and ss.case["id"] == c["id"]:
                    ss.case = None
                st.rerun()

# ================================================================== SETTINGS
elif "Settings" in page:
    header("⚙️ Settings", "API configuration, model, language and data.")
    st.markdown("### OpenRouter API")
    env_key = get_env_api_key()
    if env_key:
        st.success("An API key was found in the environment (.env / Streamlit secrets). It is "
                   "kept on the server and never displayed.", icon="🔐")
    else:
        st.warning("No OPENROUTER_API_KEY in .env or Streamlit secrets.", icon="🔑")
    new_key = st.text_input("Override key for this session only (not saved to disk)",
                            type="password", placeholder="sk-or-…")
    k1, k2, k3 = st.columns(3)
    if k1.button("Use this key") and new_key.strip():
        ss.session_api_key = new_key.strip()
        st.success("Key set for this browser session.")
    if k2.button("Forget session key"):
        ss.session_api_key = ""
        st.rerun()
    if k3.button("🔌 Test connection"):
        try:
            with st.spinner("Contacting OpenRouter…"):
                resp = OpenRouterClient(api_key(), ss.model).complete(
                    "Reply with the single word OK.", [{"role": "user", "content": "ping"}],
                    max_tokens=10)
            st.success(f"Connected. Model answered via **{resp.model}**.")
        except AIServiceError as e:
            st.error(f"{e.kind.replace('_', ' ').title()}: {e.message}")
            if e.detail:
                st.caption(e.detail[:400])

    st.markdown("### Model")
    choice = st.selectbox("Suggested models", SUGGESTED_MODELS + ["Custom…"],
                          index=SUGGESTED_MODELS.index(ss.model)
                          if ss.model in SUGGESTED_MODELS else len(SUGGESTED_MODELS))
    if choice == "Custom…":
        custom = st.text_input("OpenRouter model id", ss.model if ss.model not in
                               SUGGESTED_MODELS else "", placeholder="provider/model-name")
        if custom.strip() and custom.strip() != ss.model:
            ss.model = custom.strip()
            st.rerun()
    elif choice != ss.model:
        ss.model = choice
        st.rerun()
    st.caption("Free models on OpenRouter change often. If one fails, the app also tries "
               "backup free models automatically. The model that answered is recorded with every output.")

    st.markdown("### Language")
    ss.language_pref = st.selectbox("Response language", LANGUAGES,
                                    index=LANGUAGES.index(ss.language_pref))
    st.caption("Auto-detect replies in the language you write in. Quality for languages other "
               "than English and Hindi depends on the selected model.")

    st.markdown("### Demo mode")
    ss.demo_mode = st.toggle("Use offline demo engine (rule-based, NOT AI)", value=ss.demo_mode)
    st.caption("For presentations without an API key. All demo output is labelled. Demo mode "
               "is never switched on automatically when the API fails.")

    st.markdown("### Data")
    d1, d2, d3 = st.columns(3)
    if d1.button("Clear current chat") and ss.case:
        ss.case["messages"] = []
        save()
        st.success("Chat cleared.")
    if d2.button("Close current case"):
        ss.case = None
        st.success("Case closed (still saved in history).")
    confirm = d3.checkbox("I understand this deletes all saved cases")
    if d3.button("🗑 Delete ALL cases", disabled=not confirm):
        n = storage.delete_all_cases()
        ss.case = None
        st.success(f"Deleted {n} case(s).")

    st.markdown("### Verified legal reference list")
    st.caption("The AI may only name laws from this list; anything else is flagged.")
    for l in VERIFIED_LAWS:
        st.markdown(f"- **{l['name']}** – {l['note']}")
