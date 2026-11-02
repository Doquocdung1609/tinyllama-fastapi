# Executed checkpoint tests

Python: existing project virtual environment, Windows. No model download or research retrieval evaluation.

- `python -m pytest -q tests/test_v7p_context_safety.py tests/test_topic3_product_assistant.py`: 12 passed, 3.25 s.
- First `python -m pytest -q`: 740 passed, 3 failed, one existing Starlette warning, 56.39 s. Failures were historical V4/V6/G2 checksum checks caused by Windows CRLF checkout.
- Compared the V6 sealed CSV via Git blob bytes only: canonical SHA256 `01e841d14692477512f1029f2638f353765a9a59f44379dc09783e78bcdcab79`; converted checkout `28983cf8ec1bc9a08721369f8bc68cb41e6fddfc385fdba873139cb34b1b229c`. Added exact-file `-text` attributes and restored the existing committed bytes. Frozen Git blobs are unchanged.
- `python -m pytest -q tests/test_topic3_v4_research_lab.py tests/test_topic3_v6_evidence.py tests/test_topic3_v7a_g2_freeze.py`: 8 passed, 0.19 s after byte-preservation repair.
- `python -m compileall -q app scripts` and `git diff --check`: passed.
- Final `python -m pytest -q`: **743 passed, 1 existing warning, 47.90 s** after checkout-byte preservation.

Apple financial-answer acceptance is NOT_PASSED. React build, frontend tests and browser demonstrations are NOT_TESTED in this partial checkpoint. Synthetic plan tests demonstrate routing safety, not real financial answer correctness.
