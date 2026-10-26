# Baseline RAG test isolation

Reproduction on PR #15 with no `SCORE_THRESHOLD` override: `test_rag_defaults` asserted 0.55 while `app/config.py` defines the application's actual environment-free default as 0.7 and `RAGRequest` obtains `get_settings().score_threshold`. The accepted GitHub core workflow explicitly sets `SCORE_THRESHOLD=0.55`; that was a CI fixture assumption, not the application default. An explicit request value overrides either environment.

The minimum test-only repair replaces the ambient-dependent fixed assertion with an assertion against the active configured setting and separately checks an explicit 0.55 override. It does not modify `app/config.py`, `RAGRequest`, production defaults or the CI environment. A new regression checks D1's previously unsupported “three months ended” duration phrase. Full default and CI-configured test counts are recorded in `p6_test_results.json`; both must be reported separately.
