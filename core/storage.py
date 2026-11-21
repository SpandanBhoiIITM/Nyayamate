"""Local JSON case storage (one file per case in data/cases/)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from .config import CASES_DIR


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_case() -> dict:
    return {
        "id": datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6],
        "created_at": _now(),
        "updated_at": _now(),
        "title": "Untitled case",
        "status": "Gathering facts",
        "messages": [],            # chat history [{role, content, source}]
        "classification": None,    # TaskResult dict
        "facts": None,             # TaskResult dict (AI output, unedited)
        "facts_edited": None,      # user-reviewed version
        "guidance": None,
        "documents": {},           # doc_key -> TaskResult dict
        "documents_edited": {},    # doc_key -> edited text
        "checklist": None,
        "checklist_state": {},     # item index -> bool collected
        "ai_log": [],              # every raw AI output, unedited
    }


def _path(case_id: str) -> Path:
    safe = "".join(c for c in case_id if c.isalnum() or c in "-_")
    return CASES_DIR / f"{safe}.json"


def save_case(case: dict) -> None:
    case["updated_at"] = _now()
    tmp = _path(case["id"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_path(case["id"]))


def load_case(case_id: str) -> dict | None:
    p = _path(case_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def list_cases() -> list[dict]:
    cases = []
    for p in CASES_DIR.glob("*.json"):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
            cases.append({"id": c["id"], "title": c.get("title", "Untitled"),
                          "status": c.get("status", ""), "updated_at": c.get("updated_at", ""),
                          "issue_area": ((c.get("classification") or {}).get("data") or {})
                          .get("issue_area", "")})
        except (json.JSONDecodeError, KeyError):
            continue
    return sorted(cases, key=lambda c: c["updated_at"], reverse=True)


def delete_case(case_id: str) -> None:
    p = _path(case_id)
    if p.exists():
        p.unlink()


def delete_all_cases() -> int:
    n = 0
    for p in CASES_DIR.glob("*.json"):
        p.unlink()
        n += 1
    return n


def export_case(case: dict) -> str:
    return json.dumps(case, ensure_ascii=False, indent=2)
