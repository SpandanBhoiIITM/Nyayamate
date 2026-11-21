"""Parsing, schema validation and the legal-citation guard.

AI output is never displayed until it has been:
1. parsed as JSON (tolerating code fences / leading text),
2. coerced to the expected schema (missing required fields -> error -> retry),
3. scanned for unverified legal citations, which are flagged in the UI.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .legal_sources import REPLACED_LAWS, VERIFIED_LAWS


class OutputValidationError(Exception):
    pass


# --------------------------------------------------------------------------- JSON
def extract_json(text: str) -> Any:
    """Parse JSON from raw model text. Raises OutputValidationError."""
    if text is None:
        raise OutputValidationError("Empty response")
    cleaned = text.strip()
    # Some reasoning models leak <think> blocks
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.S)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost {...}
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError as e:
            raise OutputValidationError(f"Invalid JSON: {e}") from e
    raise OutputValidationError("No JSON object found in response")


# ------------------------------------------------------------------------ schemas
# Spec mini-language:
#   "str" | "list_str" | "num" | ("enum", [options], default)
#   ("obj", {schema}) | ("list_obj", {schema})
SCHEMAS: dict[str, dict] = {
    "classification": {
        "_required": ["issue_area", "issue_type"],
        "issue_area": ("enum", ["tenancy", "employment", "consumer", "cyber", "banking",
                                "property", "family", "criminal", "general"], "general"),
        "issue_type": "str",
        "language": "str",
        "summary": "str",
        "urgency": ("enum", ["low", "medium", "high"], "medium"),
        "confidence": ("enum", ["low", "medium", "high"], "medium"),
        "needs_lawyer_urgently": "bool",
    },
    "facts": {
        "_required": ["case_title", "issue_type"],
        "case_title": "str",
        "issue_type": "str",
        "location": "str",
        "people_involved": ("list_obj", {"name": "str", "role": "str"}),
        "timeline": ("list_obj", {"date": "str", "event": "str"}),
        "important_dates": ("list_obj", {"date": "str", "description": "str"}),
        "amount_involved": ("obj", {"value": "num", "currency": "str", "description": "str"}),
        "evidence_available": "list_str",
        "missing_information": "list_str",
    },
    "guidance": {
        "_required": ["issue_overview", "next_steps"],
        "issue_overview": "str",
        "confirmed_facts": "list_str",
        "assumptions": "list_str",
        "legal_options": ("list_obj", {"option": "str", "description": "str",
                                       "considerations": "str"}),
        "next_steps": ("list_obj", {"step": "str", "details": "str"}),
        "documents_to_collect": "list_str",
        "when_to_consult_lawyer": "list_str",
        "laws_referenced": ("list_obj", {"name": "str", "relevance": "str"}),
        "uncertainty_notes": "list_str",
    },
    "document": {
        "_required": ["subject", "body"],
        "title": "str",
        "recipient_name": "str",
        "recipient_address": "str",
        "sender_name": "str",
        "sender_address": "str",
        "date": "str",
        "subject": "str",
        "body": "str",
        "supporting_documents": "list_str",
        "placeholders_to_fill": "list_str",
    },
    "checklist": {
        "_required": ["items"],
        "items": ("list_obj", {"category": "str", "item": "str", "why_needed": "str",
                               "priority": ("enum", ["high", "medium", "low"], "medium")}),
    },
    "chat": {
        "_required": ["reply"],
        "reply": "str",
        "language": "str",
        "follow_up_questions": "list_str",
        "ready_for_case_summary": "bool",
    },
}


def _coerce(value: Any, spec: Any) -> Any:
    if spec == "str":
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return "; ".join(str(v) for v in value)
        return str(value).strip()
    if spec == "bool":
        if isinstance(value, str):
            return value.strip().lower() in ("true", "yes", "1")
        return bool(value)
    if spec == "num":
        if value in (None, "", "null"):
            return None
        if isinstance(value, (int, float)):
            return value
        digits = re.sub(r"[^\d.]", "", str(value))
        try:
            return float(digits) if "." in digits else int(digits)
        except ValueError:
            return None
    if spec == "list_str":
        if value is None:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        out = []
        for v in value:
            if isinstance(v, dict):
                v = " – ".join(str(x) for x in v.values() if x)
            if str(v).strip():
                out.append(str(v).strip())
        return out
    if isinstance(spec, tuple):
        kind = spec[0]
        if kind == "enum":
            options, default = spec[1], spec[2]
            v = str(value or "").strip().lower()
            return v if v in options else default
        if kind == "obj":
            return _coerce_obj(value if isinstance(value, dict) else {}, spec[1])
        if kind == "list_obj":
            if not isinstance(value, list):
                return []
            return [_coerce_obj(v, spec[1]) for v in value if isinstance(v, dict)]
    return value


def _coerce_obj(data: dict, schema: dict) -> dict:
    return {k: _coerce(data.get(k), s) for k, s in schema.items() if not k.startswith("_")}


def validate(data: Any, schema_name: str) -> dict:
    """Coerce to schema; raise if required fields are missing/empty."""
    if not isinstance(data, dict):
        raise OutputValidationError("Expected a JSON object")
    schema = SCHEMAS[schema_name]
    out = _coerce_obj(data, schema)
    missing = [k for k in schema.get("_required", []) if not out.get(k)]
    if missing:
        raise OutputValidationError(f"Missing required field(s): {', '.join(missing)}")
    return out


# ---------------------------------------------------------------- citation guard
_VERIFIED_NAMES = [a for law in VERIFIED_LAWS for a in [law["name"].lower(), *law["aliases"]]]

_CITATION_PATTERNS = [
    (r"\b(?:Section|Sec\.|Sections|धारा)\s*\d+[A-Za-z]?(?:\s*\(\d+\))*", "section number"),
    (r"\bArticle\s+\d+[A-Z]?\b", "constitutional article"),
    (r"\bRule\s+\d+\b", "rule number"),
    (r"\bOrder\s+[IVXLC]+\b", "CPC order"),
    (r"\bAIR\s+\d{4}\b", "law report citation"),
    (r"\(\d{4}\)\s*\d+\s*SCC\b|\b\d{4}\s+SCC\b|\bSCC\s+(?:OnLine\s+)?\d+", "law report citation"),
    (r"\b[A-Z][\w.&]+(?:\s+[A-Z][\w.&]+)*\s+(?:v\.|vs\.?|versus)\s+[A-Z][\w.&]+(?:\s+[A-Z][\w.&]+)*",
     "case name"),
]
_ACT_PATTERN = re.compile(
    r"\b((?:The\s+)?[A-Z][A-Za-z()\-']*(?:\s+(?:of|and|&|the|[A-Z][A-Za-z()\-']*))*\s+"
    r"(?:Act|Code|Rules|Sanhita|Adhiniyam),?\s+\d{4})")


def scan_citations(text: str) -> list[dict]:
    """Return a list of warnings for unverified or outdated legal references."""
    warnings: list[dict] = []
    if not text:
        return warnings
    for pattern, label in _CITATION_PATTERNS:
        for m in re.finditer(pattern, text):
            warnings.append({"text": m.group(0).strip(), "type": label,
                             "message": f"Unverified {label} – this app does not verify "
                                        f"section-level or case-law citations. Check India Code "
                                        f"or a lawyer before relying on it."})
    low = text.lower()
    for old, note in REPLACED_LAWS.items():
        if old in low:
            warnings.append({"text": old.title(), "type": "replaced law",
                             "message": f"Possibly outdated: {note}"})
    for m in _ACT_PATTERN.finditer(text):
        name = re.sub(r"^The\s+", "", m.group(1)).strip()
        lname = name.lower()
        if any(v in lname or lname in v for v in _VERIFIED_NAMES):
            continue
        if any(old in lname for old in REPLACED_LAWS):
            continue  # already reported above
        warnings.append({"text": name, "type": "unlisted law",
                         "message": "This law is not on NyayaMate's verified reference list. "
                                    "It may be correct, but confirm it on India Code."})
    # de-duplicate
    seen, uniq = set(), []
    for w in warnings:
        key = (w["text"].lower(), w["type"])
        if key not in seen:
            seen.add(key)
            uniq.append(w)
    return uniq


def scan_structure(obj: Any) -> list[dict]:
    """Run scan_citations over every string in a nested structure."""
    texts: list[str] = []

    def walk(o):
        if isinstance(o, str):
            texts.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return scan_citations("\n".join(texts))
