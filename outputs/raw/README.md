# Raw, unedited AI outputs

This folder is filled by `python run_tests.py`. For each test case you get:

- `NN_<task>_attemptK.txt` – the model's response text exactly as received from OpenRouter
  (no cleaning, no edits). If the first attempt was invalid JSON, both attempts are kept.
- `NN_<task>_attemptK_INVALID.txt` – responses that failed validation on every attempt.
- `run_meta.json` – which model actually answered each step (`openrouter/free` can route to
  different models), timestamps and any API errors.

These files were intentionally NOT pre-filled: AI outputs must come from a real run with your
own API key. Re-running overwrites the raw files for that test case.
