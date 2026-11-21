"""Reusable AI task functions.

Each function:
- builds its own task-specific prompt from only the input it needs,
- calls the model (or the clearly-labelled offline demo engine),
- validates the JSON output and retries once on invalid JSON,
- scans for unverified legal citations,
- returns a TaskResult with the RAW, unedited model text preserved.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime

from . import demo_engine, prompts
from .ai_client import ERROR_HELP, AIServiceError, OpenRouterClient
from .config import MAX_RETRIES_INVALID_JSON
from .legal_sources import allowlist_prompt_block, laws_for_area
from .validation import OutputValidationError, extract_json, scan_structure, validate


@dataclass
class TaskResult:
    task: str
    data: dict
    source: str                      # "ai" or "demo"
    model: str
    raw_outputs: list[str] = field(default_factory=list)   # unedited model text, every attempt
    citation_warnings: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return asdict(self)


# ----------------------------------------------------------------- helpers
_SCRIPTS = [
    (r"[ऀ-ॿ]", "Hindi"), (r"[ঀ-৿]", "Bengali"),
    (r"[਀-੿]", "Punjabi"), (r"[઀-૿]", "Gujarati"),
    (r"[஀-௿]", "Tamil"), (r"[ఀ-౿]", "Telugu"),
    (r"[ಀ-೿]", "Kannada"), (r"[ഀ-ൿ]", "Malayalam"),
]
_HINGLISH = {"mera", "meri", "mujhe", "nahi", "nahin", "kya", "hai", "paise", "wapas",
             "kiraya", "makan", "malik", "tankhwah", "kar", "raha", "diya"}


def detect_language(text: str) -> str:
    """Cheap script-based detection used as a hint; the model also reports language."""
    for pattern, lang in _SCRIPTS:
        if len(re.findall(pattern, text or "")) >= 3:
            return lang
    words = set(re.findall(r"[a-z]+", (text or "").lower()))
    if len(words & _HINGLISH) >= 3:
        return "Hinglish (Hindi in Latin script)"
    return "English"


def resolve_language(preference: str, text: str) -> str:
    return detect_language(text) if preference in ("", "Auto-detect", None) else preference


def _run_json_task(client: OpenRouterClient, task: str, schema: str, system: str,
                   user_content: str, temperature: float = 0.2,
                   max_tokens: int = 1800) -> TaskResult:
    messages = [{"role": "user", "content": user_content}]
    raw_outputs: list[str] = []
    last_error = ""
    for attempt in range(MAX_RETRIES_INVALID_JSON + 1):
        resp = client.complete(system, messages, temperature=temperature, json_mode=True,
                               max_tokens=max_tokens)
        raw_outputs.append(resp.text)
        try:
            data = validate(extract_json(resp.text), schema)
            return TaskResult(task=task, data=data, source="ai", model=resp.model,
                              raw_outputs=raw_outputs, citation_warnings=scan_structure(data))
        except OutputValidationError as e:
            last_error = str(e)
            messages = messages + [
                {"role": "assistant", "content": resp.text},
                {"role": "user", "content": prompts.JSON_RETRY_NUDGE.format(error=last_error)},
            ]
    err = AIServiceError("invalid_json", ERROR_HELP["invalid_json"], last_error)
    err.raw_outputs = raw_outputs  # keep raw text for debugging / test logs
    raise err


def _facts_for_prompt(facts: dict) -> str:
    return json.dumps(facts, ensure_ascii=False, indent=2)


# ------------------------------------------------------------- public API
def chat_reply(client: OpenRouterClient | None, history: list[dict], language_pref: str,
               demo: bool = False) -> TaskResult:
    """Conversational turn. Only the chat step receives the conversation history."""
    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    lang = resolve_language(language_pref, last_user)
    if demo:
        return demo_engine.chat_reply(history, lang)
    rule = (f"the user's preference is {lang}" if language_pref not in ("Auto-detect", "")
            else f"detected: {lang}; if the user switches language, follow them")
    system = prompts.CHAT_SYSTEM.format(language_rule=rule, safety=prompts.SAFETY_RULES)
    # Keep only the last 12 turns to bound token use
    trimmed = [{"role": m["role"], "content": m["content"]} for m in history[-12:]]
    raw_outputs: list[str] = []
    resp = client.complete(system, trimmed, temperature=0.3, json_mode=True, max_tokens=1500)
    raw_outputs.append(resp.text)
    try:
        data = validate(extract_json(resp.text), "chat")
    except OutputValidationError:
        # For chat, a plain-text answer is still usable – show it as-is, but labelled.
        text = re.sub(r"<think>.*?</think>", "", resp.text, flags=re.S).strip()
        data = {"reply": text, "language": lang, "follow_up_questions": [],
                "ready_for_case_summary": False}
    return TaskResult(task="chat", data=data, source="ai", model=resp.model,
                      raw_outputs=raw_outputs, citation_warnings=scan_structure(data["reply"]))


def classify_legal_issue(client: OpenRouterClient | None, narrative: str,
                         demo: bool = False) -> TaskResult:
    if demo:
        return demo_engine.classify(narrative)
    return _run_json_task(client, "classify", "classification", prompts.CLASSIFY_SYSTEM,
                          f"User's description:\n\"\"\"\n{narrative}\n\"\"\"", max_tokens=800)


def extract_case_facts(client: OpenRouterClient | None, narrative: str,
                       demo: bool = False) -> TaskResult:
    if demo:
        return demo_engine.extract_facts(narrative)
    today = datetime.now().strftime("%d %B %Y")
    return _run_json_task(client, "extract_facts", "facts", prompts.EXTRACT_SYSTEM,
                          f"Today's date: {today}\nUser's description:\n\"\"\"\n{narrative}\n\"\"\"",
                          temperature=0.0, max_tokens=1400)


def generate_legal_guidance(client: OpenRouterClient | None, facts: dict, issue_area: str,
                            language: str = "English", demo: bool = False) -> TaskResult:
    if demo:
        return demo_engine.guidance(facts, issue_area)
    system = prompts.GUIDANCE_SYSTEM.format(safety=prompts.SAFETY_RULES,
                                            allowlist=allowlist_prompt_block(issue_area),
                                            language=language)
    return _run_json_task(client, "guidance", "guidance", system,
                          f"Issue area: {issue_area}\nCase summary (JSON):\n"
                          f"{_facts_for_prompt(facts)}", max_tokens=2200)


def generate_legal_document(client: OpenRouterClient | None, facts: dict, doc_key: str,
                            issue_area: str, language: str = "English",
                            sender_details: str = "", demo: bool = False) -> TaskResult:
    if doc_key not in prompts.DOCUMENT_TYPES:
        raise ValueError(f"Unknown document type: {doc_key}")
    if demo:
        return demo_engine.document(facts, doc_key, sender_details)
    allowed = ", ".join(l["name"] for l in laws_for_area(issue_area)) or "none"
    system = prompts.DOCUMENT_SYSTEM.format(doc_type=prompts.DOCUMENT_TYPES[doc_key],
                                            allowed_laws=allowed, language=language)
    extra = f"\nSender details provided by the user: {sender_details}" if sender_details else ""
    return _run_json_task(client, f"document:{doc_key}", "document", system,
                          f"Case summary (JSON):\n{_facts_for_prompt(facts)}{extra}",
                          temperature=0.2, max_tokens=1600)


def generate_evidence_checklist(client: OpenRouterClient | None, facts: dict,
                                demo: bool = False) -> TaskResult:
    if demo:
        return demo_engine.checklist(facts)
    return _run_json_task(client, "checklist", "checklist", prompts.CHECKLIST_SYSTEM,
                          f"Case summary (JSON):\n{_facts_for_prompt(facts)}", max_tokens=1200)


def suggest_document_type(issue_area: str, facts: dict) -> str:
    text = json.dumps(facts).lower()
    if issue_area == "tenancy" or "deposit" in text:
        return "deposit_refund"
    if issue_area == "employment" or "salary" in text:
        return "salary_request"
    return "consumer_refund"
