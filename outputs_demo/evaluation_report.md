# NyayaMate AI – Evaluation Report
Generated 2026-11-20T20:34:13 from `outputs_demo/`.

**Overall: 41 checks passed, 4 failed across 4 cases.**

> Automatic checks are heuristics (string matching and regex). They can miss paraphrased facts or flag harmless text. Read the raw outputs in `outputs_demo/raw/` and complete the reviewer notes below.

> ⚠️ **These outputs come from the rule-based DEMO engine, not from AI.** They only show that the pipeline and evaluator run end to end.

## tc01_security_deposit  —  11 pass / 0 fail
Mode: demo (rule-based, NOT AI)

| Check | Result | Detail |
|---|---|---|
| Issue area classified correctly | ✅ PASS | got 'tenancy', expected 'tenancy' |
| Amount extracted correctly | ✅ PASS | got 25000, expected 25000 |
| Key facts present in summary | ✅ PASS | all present |
| No invented people/names | ✅ PASS | none found |
| No section numbers / case-law citations | ✅ PASS | none detected |
| Only verified-list laws named | ✅ PASS | none flagged |
| Next steps cover expected actions | ✅ PASS | all themes present |
| Lawyer / legal aid recommendation present | ✅ PASS | 3 item(s) |
| Facts vs assumptions separated | ✅ PASS | 5 facts, 1 assumptions |
| Document contains correct key facts | ✅ PASS | all present |
| Document has no amounts absent from input | ✅ PASS | ok |

**Reviewer notes (manual):**
- Facts extracted correctly? _…_
- Any unsupported legal claim? _…_
- Next steps relevant and practical? _…_
- Document facts correct? _…_

## tc02_unpaid_salary  —  9 pass / 2 fail
Mode: demo (rule-based, NOT AI)

| Check | Result | Detail |
|---|---|---|
| Issue area classified correctly | ✅ PASS | got 'employment', expected 'employment' |
| Amount extracted correctly | ❌ FAIL | got 32000, expected 64000 |
| Key facts present in summary | ✅ PASS | all present |
| No invented people/names | ✅ PASS | none found |
| No section numbers / case-law citations | ✅ PASS | none detected |
| Only verified-list laws named | ✅ PASS | none flagged |
| Next steps cover expected actions | ✅ PASS | all themes present |
| Lawyer / legal aid recommendation present | ✅ PASS | 3 item(s) |
| Facts vs assumptions separated | ✅ PASS | 5 facts, 1 assumptions |
| Document contains correct key facts | ❌ FAIL | missing: 64,000/64000, August, September |
| Document has no amounts absent from input | ✅ PASS | ok |

**Reviewer notes (manual):**
- Facts extracted correctly? _…_
- Any unsupported legal claim? _…_
- Next steps relevant and practical? _…_
- Document facts correct? _…_

## tc03_defective_product  —  10 pass / 1 fail
Mode: demo (rule-based, NOT AI)

| Check | Result | Detail |
|---|---|---|
| Issue area classified correctly | ✅ PASS | got 'consumer', expected 'consumer' |
| Amount extracted correctly | ✅ PASS | got 8000, expected 8000 |
| Key facts present in summary | ✅ PASS | all present |
| No invented people/names | ✅ PASS | none found |
| No section numbers / case-law citations | ✅ PASS | none detected |
| Only verified-list laws named | ✅ PASS | none flagged |
| Next steps cover expected actions | ✅ PASS | all themes present |
| Lawyer / legal aid recommendation present | ✅ PASS | 3 item(s) |
| Facts vs assumptions separated | ✅ PASS | 4 facts, 1 assumptions |
| Document contains correct key facts | ❌ FAIL | missing: HK-558213 |
| Document has no amounts absent from input | ✅ PASS | ok |

**Reviewer notes (manual):**
- Facts extracted correctly? _…_
- Any unsupported legal claim? _…_
- Next steps relevant and practical? _…_
- Document facts correct? _…_

## tc04_security_deposit_hindi  —  11 pass / 1 fail
Mode: demo (rule-based, NOT AI)

| Check | Result | Detail |
|---|---|---|
| Issue area classified correctly | ✅ PASS | got 'tenancy', expected 'tenancy' |
| Amount extracted correctly | ✅ PASS | got 25000, expected 25000 |
| Key facts present in summary | ✅ PASS | all present |
| No invented people/names | ✅ PASS | none found |
| No section numbers / case-law citations | ✅ PASS | none detected |
| Only verified-list laws named | ✅ PASS | none flagged |
| Next steps cover expected actions | ✅ PASS | all themes present |
| Lawyer / legal aid recommendation present | ✅ PASS | 3 item(s) |
| Facts vs assumptions separated | ✅ PASS | 2 facts, 1 assumptions |
| Document contains correct key facts | ✅ PASS | all present |
| Document has no amounts absent from input | ✅ PASS | ok |
| Chat reply in user's language | ❌ FAIL | detected 'English' |

**Reviewer notes (manual):**
- Facts extracted correctly? _…_
- Any unsupported legal claim? _…_
- Next steps relevant and practical? _…_
- Document facts correct? _…_
