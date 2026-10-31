"""Derive source-linked failure cases from the frozen provisional run."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/topic3/01_REPRODUCTION"
OUT = ROOT / "docs/topic3/02_FAILURES"
CASES = [
    ("F01", "t3-pg-net-sales-2026", "R0_BM25", "WRONG_FINANCIAL_ROW_PRIORITY", "The target consolidated NET SALES row is absent from Top-10 while segment discussion leads.", "Structure-aware table-row candidate ranking"),
    ("F02", "t3-pg-assets-2026", "R0_BM25", "WRONG_METRIC_TOP1", "Goodwill/narrative material leads; the balance-sheet TOTAL ASSETS row is Rank 2.", "Exact metric and statement-row compatibility"),
    ("F03", "t3-hd-assets-2026", "R4_SPLADE_DENSE_RRF", "STAGE1_CANDIDATE_MISSED_TOP10", "The correct balance-sheet row is absent from Top-10 despite related financial content.", "Larger bounded candidate pool plus source-aware Stage-2"),
    ("F04", "t3-negative-pg-2037", "R0_BM25", "UNSUPPORTED_PERIOD_RETRIEVAL", "A 2026/2025 P&G filing returns for an unavailable 2037 period.", "Explicit period guard and numeric abstention"),
    ("F05", "t3-negative-issuer", "R3_BM25_DENSE_RRF", "WRONG_ISSUER_RETRIEVAL", "The corpus has no Apple filing, yet the hybrid retriever returns a Home Depot chunk.", "Issuer/document availability guard before financial answer"),
]


def main() -> None:
    run = json.loads((DATA / "RETRIEVAL_RESULTS.json").read_text(encoding="utf-8"))
    qrels = {q["id"]: q for q in map(json.loads, (DATA / "PROVISIONAL_SOURCE_QRELS.jsonl").read_text(encoding="utf-8").splitlines())}
    records = {r["id"]: r for r in run["records"]}
    chunks = {c["chunk_id"]: c for c in map(json.loads, (DATA / "author_chunks.jsonl").read_text(encoding="utf-8").splitlines())}
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for case_id, qid, arm, category, observation, candidate in CASES:
        q = qrels[qid]
        run_record = records[qid]
        results = run_record["arms"][arm]["results"]
        top = results[0]
        target_rank = next((r["rank"] for r in results if r["chunk_id"] in q["relevant_chunk_ids"]), None)
        rows.append({
            "case_id": case_id,
            "category": category,
            "question_id": qid,
            "question": q["query"],
            "method": arm,
            "corpus_sha256": run["corpus_sha256"],
            "qrels_sha256": run["qrels_sha256"],
            "source_document_id": q["expected_document_id"],
            "source_html_sha256": q["source_sha256"],
            "source_url": q["source_url"],
            "source_locator": q["source_locator"],
            "expected_chunk_ids": q["relevant_chunk_ids"],
            "observed_target_rank_top10": target_rank,
            "actual_top1": {"chunk_id": top["chunk_id"], "ticker": top["ticker"], "text_excerpt": chunks[top["chunk_id"]]["text"][:320]},
            "observation": observation,
            "root_cause_hypothesis": observation,
            "repair_candidate": candidate,
            "regression_query_id": qid,
            "review_status": "PROVISIONAL_UNREVIEWED",
            "limitations": "The target list is source-located by Codex but may omit additional relevant chunks; negative retrieval does not prove a wrong numeric answer.",
        })
    with (OUT / "FAILURE_CATALOG.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"cases": len(rows), "categories": sorted({r["category"] for r in rows})}))


if __name__ == "__main__":
    main()
