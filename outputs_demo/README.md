# ⚠️ Demo-engine outputs – NOT AI

Produced by `python run_tests.py --demo` and `python evaluate.py --demo` using the offline
rule-based engine (`core/demo_engine.py`: keyword matching, regex, fixed templates).

They exist only to show that the pipeline, storage and evaluator work end to end without an
API key. Do not treat them as AI results. Real AI outputs go in `outputs/` after
`python run_tests.py`.

Note that the evaluator correctly reports failures here (e.g. the demo engine cannot put the
order number into the consumer letter, and cannot reply in Hindi) – the checks are not rigged.
