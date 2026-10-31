"""Reproduce the author's returned-only relevance denominator on a tiny case.

Execute with the isolated author virtualenv. This is a code-path audit, not a
retrieval-quality score or a production benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path

from hybrid_search.evaluation.benchmark import BenchmarkRunner
from hybrid_search.evaluation.metrics import IRMetrics


def main() -> None:
    # A and B are independently relevant. Only A was retrieved.
    retrieved = ["A"]
    relevant_terms = ["revenue", "assets"]
    returned_text = {"A": "revenue assets"}
    runner = BenchmarkRunner.__new__(BenchmarkRunner)
    author_relevant = [
        result_id for result_id in retrieved
        if runner.score_query_relevance(returned_text[result_id], relevant_terms) >= 0.5
    ]
    author_recall = IRMetrics.recall_at_k(retrieved, author_relevant, k=10)
    source_judged_recall = IRMetrics.recall_at_k(retrieved, ["A", "B"], k=10)
    assert author_relevant == ["A"] and author_recall == 1.0 and source_judged_recall == 0.5
    output = {
        "status": "AUTHOR_BENCHMARK_DENOMINATOR_COUNTEREXAMPLE",
        "retrieved_ids": retrieved,
        "independently_relevant_ids": ["A", "B"],
        "author_relevant_ids_from_returned_only": author_relevant,
        "author_style_recall_at_10": author_recall,
        "source_judged_recall_at_10": source_judged_recall,
        "scope": "metric-code audit, synthetic counterexample; not empirical retrieval",
    }
    path = Path("docs/topic3/00_AUDIT/AUTHOR_METRIC_COUNTEREXAMPLE.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
