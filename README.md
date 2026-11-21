# ⚖️ NyayaMate AI – Indian Everyday Legal Assistant

NyayaMate AI helps ordinary people in India understand a legal problem: describe it in plain
English, Hindi or another Indian language, and the app organises it into a case summary,
explains possible options and next steps, drafts a letter, and builds an evidence checklist.

> **Disclaimer:** NyayaMate AI gives general legal *information*, not legal advice. It is not a
> law firm and does not represent anyone. Always verify laws on
> [India Code](https://www.indiacode.nic.in) and consult a qualified lawyer, or get free legal
> aid through [NALSA](https://nalsa.gov.in) (helpline 15100), for urgent or complex matters.

---

## 1. Quick start (local, about 5 minutes)

Requirements: Python 3.10+ and an OpenRouter API key (free at https://openrouter.ai/keys).
Runs comfortably on an 8 GB laptop. There is no local model.

```bash
# 1. Get the code and enter the folder
cd nyayamate

# 2. Create a virtual environment
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
cp .env.example .env          # Windows: copy .env.example .env
# open .env and set OPENROUTER_API_KEY=sk-or-v1-...

# 5. Run
streamlit run app.py
```

The app opens at http://localhost:8501. Go to **Settings → Test connection** to confirm
the key works.

**No key?** Switch on **Settings → Demo mode**. This runs an offline, rule-based engine and
labels every result "DEMO ENGINE · not AI". It is never switched on automatically.

---

## 2. Features

| Section | What it does |
|---|---|
| 🏠 **Home** | Dashboard with Start New Case, recent cases, assistance categories and stats |
| 💬 **Legal Chat** | Natural conversation. Detects the user's language and replies in it. Asks at most 3 follow-up questions per turn, and only about missing facts |
| 🗂️ **Case Builder** | Classifies the issue and extracts title, type, people, timeline, dates, amount, evidence and missing info into an editable form |
| 🧭 **Legal Guidance** | Issue overview, **confirmed facts vs assumptions**, options, next steps, documents to collect, when to see a lawyer, laws (verified list only), curated official resources, and uncertainty notes |
| 📝 **Document Generator** | Editable drafts: deposit refund request, salary payment request, consumer refund complaint. Stamped DRAFT, with placeholders highlighted and .txt/.md download |
| ✅ **Evidence Checklist** | AI-generated, grouped by category, tick-to-collect with saved progress, and your own items can be added |
| 📚 **Case History** | Local JSON storage (`data/cases/`). Open, search, export or delete cases |
| ⚙️ **Settings** | Session API key override, connection test, model picker (any OpenRouter id), language preference, demo mode, clear data |

Every AI result shows which model answered, a timestamp, a citation-check badge and an
**"Raw AI output (unedited)"** expander.

---

## 3. Architecture

```
app.py                    Streamlit UI (all pages)
core/
  config.py               key lookup (.env → Streamlit secrets → session), model defaults
  ai_client.py            OpenRouter client (OpenAI SDK) + error mapping
  prompts.py              one prompt per task + shared safety rules
  legal_ai.py             classify_legal_issue(), extract_case_facts(),
                          generate_legal_guidance(), generate_legal_document(),
                          generate_evidence_checklist(), chat_reply()
  validation.py           JSON extraction, schema coercion, citation guard
  legal_sources.py        curated list of laws and official portals the AI may name
  demo_engine.py          offline rule-based engine (clearly labelled, not AI)
  storage.py              JSON case storage
  ui_styles.py            theme CSS
run_tests.py              runs all test cases through the real pipeline, saves raw outputs
evaluate.py               automatic checks → outputs/evaluation_report.md
tests/test_cases/*.json   4 test cases with expected facts
outputs/raw/              raw, unedited model text (filled by run_tests.py)
outputs/structured/       validated outputs per test
outputs/documents/        generated letters
outputs_demo/             same pipeline run with the demo engine (NOT AI)
```

**Separate prompts per task, minimal context.** Only the chat step sees the conversation
(last 12 turns). Classification and extraction see only the user's own narrative. Guidance,
documents and the checklist see only the structured (user-reviewed) case summary JSON. This
keeps token use low and stops earlier model replies from leaking into the facts.

**Validation pipeline:** raw text → `extract_json()` (handles code fences, `<think>` blocks
and leading prose) → `validate()` (schema coercion with required fields) → **one automatic
retry** with a correction message if it's invalid → otherwise an `invalid_json` error showing
the raw text. Nothing is displayed until it validates.

**Error handling:** missing key, invalid key (401/403), rate limit (429), network/timeout,
model unavailable (404/502/503/empty reply), models without `response_format` support (retried
without it), and invalid JSON. Each one shows a clear message, technical details and a link to
Settings. **No fake output is ever shown when the API fails.**

---

## 4. Legal accuracy safeguards

1. **Allow-list of laws** (`core/legal_sources.py`): Consumer Protection Act 2019, Consumer
   Protection (E-Commerce) Rules 2020, Code on Wages 2019, Indian Contract Act 1872, Model
   Tenancy Act 2021 (marked as model law, state adoption needed), Legal Services Authorities Act
   1987, Bharatiya Nyaya Sanhita 2023 and IT Act 2000. These are names only, with **no section
   numbers**. The guidance prompt receives only the list that fits the issue area.
2. **Prompt rules:** no section numbers, no case law, say when something is uncertain, separate
   facts from assumptions, no guaranteed outcomes, not a law firm, and recommend a lawyer or
   legal aid for complex, urgent or high-risk matters.
3. **Citation guard** (`validation.scan_citations`) runs over every AI output and flags:
   - section, article, rule or CPC-order numbers,
   - case names (`X v. Y`) and law-report citations (AIR, SCC),
   - **replaced laws** (e.g. Payment of Wages Act → Code on Wages 2019, in force from
     21 Nov 2025; IPC → BNS 2023),
   - any "… Act, YYYY" that is not on the allow-list.
   Flags appear in the UI as "needs verification". Text is not silently changed.
4. Official resources (India Code, National Consumer Helpline 1915, e-Daakhil, NALSA 15100,
   cybercrime.gov.in 1930, Ministry of Labour, RBI CMS) come from the curated list, not
   from the AI.
5. A visible disclaimer appears on the dashboard, chat, guidance and document pages, and in the
   sidebar. Downloaded documents carry a DRAFT header.

---

## 5. Testing

Four test cases are in `tests/test_cases/`: the three required scenarios plus a Hindi version of
the deposit case to test language handling. Each includes the user input and the expected facts
used for evaluation.

```bash
python run_tests.py                 # real AI run (needs OPENROUTER_API_KEY), ~18 calls
python evaluate.py                  # writes outputs/evaluation_report.md + evaluation.json
```

Options: `--model <id>` (pin a model for reproducibility), `--only tc02_unpaid_salary`,
`--delay 5` (more time between calls when free-tier rate limits are tight), `--demo` (offline
engine, written to `outputs_demo/`).

For each test the runner saves the **unedited** model text for every step and attempt
(`outputs/raw/<id>/`), the structured case summary and all validated outputs
(`outputs/structured/<id>.json`), and the generated letter (`outputs/documents/`).

### Evaluation

`evaluate.py` runs these automatic checks for each case:

| Requirement | Automatic check |
|---|---|
| Case facts extracted correctly | issue area matches; amount matches exactly; key names, places and dates present; no people invented that aren't in the input; flags amounts not in the input |
| Unsupported legal citations avoided | no section, article or case-law hits from the citation guard; only allow-listed laws named |
| Next steps relevant | expected themes present (e.g. written demand + legal aid, Labour Department, 1915 / e-Daakhil); lawyer guidance present; facts and assumptions separated |
| Document has correct facts | required facts present (amount, months, ticket no.); no amounts that aren't in the input |
| Language | chat reply is in Hindi for the Hindi case |
| Incorrect / uncertain output | listed under each case, plus API errors |

The report includes a **Reviewer notes** block for each case for the manual review the
assignment asks for. String-matching checks can miss paraphrases, so read the raw outputs too.

**Status of the included outputs:** this package was built in an environment with no access
to OpenRouter, so **`outputs/raw/` is intentionally empty**. No AI responses were written by
hand or simulated. Run `python run_tests.py && python evaluate.py` with your key to produce the
real AI outputs and report. The included `outputs_demo/` shows the pipeline working end to end
with the rule-based engine (41/45 checks pass). The 4 failures are real limits of that engine:
it can't name the months or the ticket number in letters, can't reply in Hindi, and puts a
per-month salary instead of the total. This shows the checks are not rigged to pass.

---

## 6. Deploying for a demo

**Streamlit Community Cloud (free):**
1. Push this folder to a GitHub repo. `.env` is git-ignored, so never commit your key.
2. Go to https://share.streamlit.io, click **New app**, pick the repo, and set the main file to `app.py`.
3. Under **Advanced settings → Secrets**, paste
   `OPENROUTER_API_KEY = "sk-or-v1-..."` (see `.streamlit/secrets.toml.example`).
4. Deploy.

**Other hosts (Render, Railway, a VM):**
`pip install -r requirements.txt && streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
and set `OPENROUTER_API_KEY` as an environment variable.

The key stays on the server. Streamlit runs Python on the server, so the key is never sent to
the browser, and the Settings field is a masked password input that is never shown back.

---

## 7. Known limitations

- **Not legal advice.** The allow-list and citation guard reduce invented law, but can't
  guarantee accurate legal information. The guard uses pattern matching and can miss unusual
  phrasing or flag harmless text.
- **`openrouter/free` varies:** it routes to whichever free model is available, so quality,
  JSON reliability and Indian-language support change between runs. The model that answered is
  recorded every time. Pin a model in Settings or with `--model` for consistent results.
- **Free-tier rate limits** can interrupt runs. The app reports this and doesn't retry endlessly.
- **State-specific law:** tenancy and labour procedures differ by state. The app says so rather
  than resolving it.
- **Shared local storage:** cases are saved as JSON on the server. On a public deployment all
  visitors share the same Case History, and Streamlit Cloud storage resets on restart. Use public
  deployments for demos only, with no real personal data.
- **Documents:** only three letter types; .txt/.md export (no PDF/Word).
- **Demo mode** is template-based and doesn't analyse the user's facts.
- Language detection uses the script (Devanagari, Tamil and so on) plus the model's own report.
  Romanised Hindi ("Hinglish") is detected only by a small word list.
