"""Automatic evaluation of saved test outputs -> outputs/evaluation_report.md

Usage:
    python evaluate.py          # evaluates outputs/structured/*.json (AI run)
    python evaluate.py --demo   # evaluates outputs_demo/ (rule-based engine)

Automatic checks are heuristics. A human reviewer should still read every output and fill in
the "Reviewer notes" section of the report.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime

from core.config import BASE_DIR, TEST_CASES_DIR
from core.legal_ai import detect_language


def any_of(pattern_alts: str, text: str) -> bool:
    return any(alt.lower() in text.lower() for alt in pattern_alts.split("|"))


def amounts_in(text: str) -> set[int]:
    vals = set()
    for m in re.finditer(r"(?:₹|rs\.?|inr)\s*([\d,]+)", text, flags=re.I):
        try:
            vals.add(int(m.group(1).replace(",", "")))
        except ValueError:
            pass
    return vals


def evaluate_case(tc: dict, rec: dict) -> dict:
    exp = tc.get("expected", {})
    steps = rec.get("steps", {})
    res = {"test_id": tc["id"], "mode": rec.get("mode"), "checks": [], "issues": []}

    def check(name, passed, detail=""):
        res["checks"].append({"check": name, "result": "PASS" if passed else
                              ("FAIL" if passed is False else "N/A"), "detail": detail})

    for e in rec.get("errors", []):
        res["issues"].append(f"Step '{e['step']}' failed: {e['kind']} – {e['message']}")

    # 1. Fact extraction
    cls = (steps.get("classify") or {}).get("data")
    facts = (steps.get("extract_facts") or {}).get("data")
    if cls:
        check("Issue area classified correctly", cls["issue_area"] == exp.get("issue_area"),
              f"got '{cls['issue_area']}', expected '{exp.get('issue_area')}'")
    else:
        check("Issue area classified correctly", None, "classification missing")
    if facts:
        amt = (facts.get("amount_involved") or {}).get("value")
        check("Amount extracted correctly", amt is not None and float(amt) == exp.get("amount"),
              f"got {amt}, expected {exp.get('amount')}")
        blob = json.dumps(facts, ensure_ascii=False)
        missing = [m for m in exp.get("facts_must_mention", []) if not any_of(m, blob)]
        check("Key facts present in summary", not missing,
              "missing: " + ", ".join(missing) if missing else "all present")
        # hallucinated names: people names not present in the input
        inp = tc["user_input"].lower()
        invented = [p["name"] for p in facts.get("people_involved", [])
                    if p["name"] and p["name"].lower() not in ("not stated", "unknown", "user", "")
                    and not any(tok in inp for tok in p["name"].lower().replace(".", " ").split()
                                if len(tok) > 2)]
        check("No invented people/names", not invented,
              "possible invented: " + ", ".join(invented) if invented else "none found")
        extra_amts = amounts_in(blob) - amounts_in(tc["user_input"])
        if extra_amts:
            res["issues"].append(f"Facts contain amounts not in input: {sorted(extra_amts)} "
                                 "(may be a computed total – review)")
    else:
        for n in ("Amount extracted correctly", "Key facts present in summary",
                  "No invented people/names"):
            check(n, None, "fact extraction missing")

    # 2. Unsupported citations
    all_warn = []
    for name in ("chat_reply", "guidance", "document"):
        for w in (steps.get(name) or {}).get("citation_warnings", []):
            all_warn.append(f"{name}: {w['text']} ({w['type']})")
    hard = [w for w in all_warn if any(t in w for t in ("section number", "case name",
                                                         "law report", "article", "rule number"))]
    check("No section numbers / case-law citations", not hard,
          "; ".join(hard) if hard else "none detected")
    soft = [w for w in all_warn if w not in hard]
    check("Only verified-list laws named", not soft, "; ".join(soft) if soft else "none flagged")

    # 3. Next steps relevance
    g = (steps.get("guidance") or {}).get("data")
    if g:
        gtext = json.dumps({k: g[k] for k in ("legal_options", "next_steps")}, ensure_ascii=False)
        missing_kw = [k for k in exp.get("relevant_next_step_keywords", []) if not any_of(k, gtext)]
        check("Next steps cover expected actions", not missing_kw,
              "missing themes: " + ", ".join(missing_kw) if missing_kw else "all themes present")
        check("Lawyer / legal aid recommendation present", bool(g["when_to_consult_lawyer"]),
              f"{len(g['when_to_consult_lawyer'])} item(s)")
        check("Facts vs assumptions separated", bool(g["confirmed_facts"]),
              f"{len(g['confirmed_facts'])} facts, {len(g['assumptions'])} assumptions")
    else:
        check("Next steps cover expected actions", None, "guidance missing")

    # 4. Document correctness
    d = (steps.get("document") or {}).get("data")
    if d:
        dtext = d["subject"] + "\n" + d["body"]
        miss = [m for m in exp.get("document_must_contain", []) if not any_of(m, dtext)]
        check("Document contains correct key facts", not miss,
              "missing: " + ", ".join(miss) if miss else "all present")
        bad_amts = amounts_in(dtext) - amounts_in(tc["user_input"])
        check("Document has no amounts absent from input", not bad_amts,
              f"unexpected: {sorted(bad_amts)}" if bad_amts else "ok")
    else:
        check("Document contains correct key facts", None, "document missing")

    # 5. Language handling
    if exp.get("chat_reply_language"):
        reply = ((steps.get("chat_reply") or {}).get("data") or {}).get("reply", "")
        got = detect_language(reply)
        check("Chat reply in user's language", exp["chat_reply_language"] in got,
              f"detected '{got}'")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    root = BASE_DIR / ("outputs_demo" if args.demo else "outputs")
    results = []
    for p in sorted(TEST_CASES_DIR.glob("*.json")):
        tc = json.loads(p.read_text(encoding="utf-8"))
        sp = root / "structured" / f"{tc['id']}.json"
        if not sp.exists():
            print(f"skip {tc['id']}: no output at {sp} – run run_tests.py first")
            continue
        results.append(evaluate_case(tc, json.loads(sp.read_text(encoding="utf-8"))))
    if not results:
        raise SystemExit("Nothing to evaluate.")

    lines = [f"# NyayaMate AI – Evaluation Report",
             f"Generated {datetime.now().isoformat(timespec='seconds')} from `{root.name}/`.",
             "",
             "> Automatic checks are heuristics (string matching and regex). They can miss "
             "paraphrased facts or flag harmless text. Read the raw outputs in "
             f"`{root.name}/raw/` and complete the reviewer notes below.", ""]
    if args.demo:
        lines += ["> ⚠️ **These outputs come from the rule-based DEMO engine, not from AI.** "
                  "They only show that the pipeline and evaluator run end to end.", ""]
    tp = tf = 0
    for r in results:
        p = sum(c["result"] == "PASS" for c in r["checks"])
        f = sum(c["result"] == "FAIL" for c in r["checks"])
        tp, tf = tp + p, tf + f
        lines += [f"## {r['test_id']}  —  {p} pass / {f} fail", f"Mode: {r['mode']}", "",
                  "| Check | Result | Detail |", "|---|---|---|"]
        lines += [f"| {c['check']} | {'✅' if c['result']=='PASS' else '❌' if c['result']=='FAIL' else '➖'} "
                  f"{c['result']} | {c['detail'].replace('|', '/')} |" for c in r["checks"]]
        if r["issues"]:
            lines += ["", "**Incorrect or uncertain output:**"] + [f"- {i}" for i in r["issues"]]
        lines += ["", "**Reviewer notes (manual):**",
                  "- Facts extracted correctly? _…_",
                  "- Any unsupported legal claim? _…_",
                  "- Next steps relevant and practical? _…_",
                  "- Document facts correct? _…_", ""]
    lines.insert(3, f"**Overall: {tp} checks passed, {tf} failed across {len(results)} cases.**\n")
    (root / "evaluation_report.md").write_text("\n".join(lines), encoding="utf-8")
    (root / "evaluation.json").write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved {root / 'evaluation_report.md'}")


if __name__ == "__main__":
    main()
