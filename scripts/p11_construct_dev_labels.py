"""Build provisional source-inspection labels without looking at retrieval ranks."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.p11_acquire_official_sec import OWNER, file_hash


SPEC = (
    ("p11-dev-mcd-assets-exact", "MCD", "What were McDonald's total assets as of June 30, 2026?", "INSTANT_BALANCE", "table_f8a8a01491e69b5fca6b84b2", 5, "June 30, 2026", "Total Assets"),
    ("p11-dev-mcd-assets-paraphrase", "MCD", "How large was McDonald's asset base at June 30, 2026?", "SEMANTIC_PARAPHRASE", "table_f8a8a01491e69b5fca6b84b2", 5, "June 30, 2026", "Total Assets"),
    ("p11-dev-mcd-revenue-current", "MCD", "Find McDonald's total revenues for the six months ended June 30, 2026.", "INCOME_STATEMENT", "table_76f4cf3ea0256b1604845887", 6, "2026", "Total revenues"),
    ("p11-dev-mcd-revenue-prior", "MCD", "Find McDonald's total revenues for the six months ended June 30, 2025.", "COMPARATIVE_PERIOD", "table_76f4cf3ea0256b1604845887", 6, "2025", "Total revenues"),
    ("p11-dev-cat-sales-quarter", "CAT", "What were Caterpillar's total sales and revenues for the three months ended June 30, 2026?", "INCOME_STATEMENT", "table_b891b8ad2f9e518484d7b9c4", 6, "Three Months Ended June 30, / 2026", "Total sales and revenues"),
    ("p11-dev-cat-sales-paraphrase", "CAT", "How much did Caterpillar sell in the June 2026 quarter, including financial products revenue?", "SEMANTIC_PARAPHRASE", "table_b891b8ad2f9e518484d7b9c4", 6, "Three Months Ended June 30, / 2026", "Total sales and revenues"),
    ("p11-dev-cat-sales-sixmonths", "CAT", "Locate Caterpillar total sales and revenues for the six months ended June 30, 2026.", "COMPARATIVE_PERIOD", "table_a09da0ea30c7e827d4e6ce05", 6, "Six Months Ended June 30, / 2026", "Total sales and revenues"),
    ("p11-dev-cat-cash", "CAT", "What was Caterpillar's cash and cash equivalents as of June 30, 2026?", "BALANCE_SHEET", "table_9a187831f64484472d744d41", 4, "June 30, 2026", "Cash and cash equivalents"),
    ("p11-dev-cat-basic-eps", "CAT", "Find Caterpillar profit per common share before dilution for the three months ended June 30, 2026.", "BASIC_EPS", "table_b891b8ad2f9e518484d7b9c4", 34, "Three Months Ended June 30, / 2026", "Profit per common share"),
    ("p11-dev-cat-diluted-eps", "CAT", "Find Caterpillar diluted profit per common share for the three months ended June 30, 2026.", "DILUTED_EPS", "table_b891b8ad2f9e518484d7b9c4", 36, "Three Months Ended June 30, / 2026", "Profit per common share \u2013 diluted 2"),
)

REFUSALS = (
    ("p11-dev-wrong-issuer", "What were McDonald's total assets in Caterpillar's June 2026 10-Q?", "WRONG_ISSUER", "CONFLICT_OR_CLARIFICATION"),
    ("p11-dev-wrong-period", "What were Caterpillar's total sales and revenues for the three months ended June 30, 2027?", "WRONG_PERIOD", "NO_VERIFIED_EVIDENCE"),
    ("p11-dev-ambiguous", "What was revenue last year?", "AMBIGUOUS", "NEEDS_CLARIFICATION"),
    ("p11-dev-unsupported-duration", "What was McDonald's full-year 2026 revenue in its June 2026 10-Q?", "UNSUPPORTED_DURATION", "NO_VERIFIED_EVIDENCE"),
)


def run(root):
    root = root.resolve(strict=True)
    if root.name != "t3-p11-new-sec-20261027-v1" or json.loads(
        (root / "ownership.json").read_text(encoding="utf-8"))["owner"] != OWNER:
        raise ValueError("P11_OWNED_ROOT_REQUIRED")
    acquisition = json.loads((root / "acquisition.json").read_text(encoding="utf-8"))
    records = {r["ticker"]: r for r in acquisition["records"]}
    source = {}
    for ticker in ("MCD", "CAT"):
        item = records[ticker]
        if (item["status"] != "ACQUIRED_OFFICIAL_SOURCE"
            or file_hash(root / item["relative_path"]) != item["raw_sha256"]):
            raise ValueError("P11_SOURCE_HASH_OR_STATUS_MISMATCH")
        folder = root / "derived" / ticker
        manifest = json.loads((folder / "parse_manifest.json").read_text(encoding="utf-8"))
        if (manifest["raw_sha256"] != item["raw_sha256"]
            or file_hash(folder / "structured.json") != manifest["structured_sha256"]
            or file_hash(folder / "chunks.jsonl") != manifest["chunks_sha256"]):
            raise ValueError("P11_CANONICAL_DERIVATION_MISMATCH")
        structured = json.loads((folder / "structured.json").read_text(encoding="utf-8"))
        tables = {t["table_id"]: t for t in structured["tables"]}
        chunks = [json.loads(line) for line in (folder / "chunks.jsonl").open(encoding="utf-8")]
        source[ticker] = (item, manifest, tables, chunks)
    queries, qrels, review = [], [], []
    for qid, ticker, question, category, table_id, row_index, period, row_label in SPEC:
        item, manifest, tables, chunks = source[ticker]
        table = tables[table_id]
        if period not in table["reporting_periods"]:
            raise ValueError("P11_PERIOD_NOT_IN_VERIFIED_TABLE_CONTEXT:" + qid)
        row_offset = table["row_indices"].index(row_index)
        row = table["rows"][row_offset]
        if row[0].casefold() != row_label.casefold():
            raise ValueError("P11_ROW_LABEL_MISMATCH:" + qid)
        matches = [c for c in chunks if c["kind"] == "table"
                   and c["metadata"].get("table_id") == table_id
                   and c["source_location"].get("row_index") == row_index]
        if len(matches) != 1:
            raise ValueError("P11_PARENT_NOT_UNIQUE:" + qid)
        parent = matches[0]
        locator = parent["source_location"]["structural_path"]
        reason = ("Canonical table row contains the specified accounting label in the "
                  "pinned official filing; table header includes the requested period. "
                  "Alternative relevant rows may remain unjudged pending human review.")
        query = {"query_id": qid, "partition": "development", "issuer": ticker,
                 "cik": item["cik"], "accession": item["metadata"]["accession_number"],
                 "form": item["metadata"]["form_type"], "source_url": item["metadata"]["source_url"],
                 "raw_sha256": item["raw_sha256"], "question": question,
                 "category": category, "expected_evidence_group": table_id + ":row:" + str(row_index),
                 "eligible_parent_ids": [parent["chunk_id"]], "source_locator": locator,
                 "row_index": row_index, "reporting_period": period,
                 "units_observed": table["units"], "evidence_rationale": reason,
                 "labeling_method": "CODEX_SOURCE_INSPECTION_FIXED_SPEC_NO_RANKINGS",
                 "reviewer_status": "NO_INDEPENDENT_HUMAN_REVIEW",
                 "ambiguity": "qrel exhaustiveness and column-level financial semantics unadjudicated",
                 "extraction_status": manifest["document_status"]}
        queries.append(query)
        qrels.append({"query_id": qid, "parent_id": parent["chunk_id"], "grade": 2,
                      "status": "PROVISIONAL_SOURCE_ROW_LABEL"})
        review.append({"query_id": qid, "question": question,
                       "proposed_parent_id": parent["chunk_id"], "proposed_grade": 2,
                       "source_excerpt": parent["text"][:900], "table_id": table_id,
                       "row_index": row_index, "row_cells": row[:14],
                       "table_headers": table["header_rows"][:3],
                       "periods": table["reporting_periods"],
                       "units": table["units"], "source_locator": locator,
                       "rationale": reason,
                       "human_review_status": "UNREVIEWED",
                       "review_questions": ["Is this the complete eligible evidence group?",
                                            "Does the header bind this specific financial period?",
                                            "Are unit, entity and EPS qualifier correct?"]})
    for qid, question, category, expected in REFUSALS:
        queries.append({"query_id": qid, "partition": "development", "question": question,
                        "category": category, "expected_status": expected,
                        "eligible_parent_ids": [], "qrel_status": "NOT_A_NEGATIVE_QREL",
                        "labeling_method": "ADVERSARIAL_SCOPE_CONTROL",
                        "reviewer_status": "NO_INDEPENDENT_HUMAN_REVIEW"})
    return ({"schema_version": "topic3-p11-dev-query-registry/v1",
             "source_selection_commit": "d04fd4b53c104cbc5208ff33bcf876ae7bcbc03e",
             "status": "PROVISIONAL_DEVELOPMENT_ONLY", "queries": queries,
             "positive_count": len(SPEC), "refusal_count": len(REFUSALS)},
            {"schema_version": "topic3-p11-dev-qrels/v1", "status": "PROVISIONAL_NOT_HUMAN_ADJUDICATED",
             "qrels": qrels, "human_reviewers": 0, "rankings_used_for_labels": False},
            {"schema_version": "topic3-p11-label-review-queue/v1",
             "status": "AWAITING_HUMAN_REVIEW", "items": review,
             "human_reviewers": 0, "automated_consistency_checks_passed": True})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    results = run(args.root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in zip(("p11_query_registry.json", "p11_qrels.json",
                            "p11_label_review_queue.json"), results):
        (args.output_dir / name).write_text(json.dumps(value, indent=2) + "\n",
                                             encoding="utf-8")
    print(json.dumps({"positive": results[0]["positive_count"],
                      "refusal": results[0]["refusal_count"],
                      "review_items": len(results[2]["items"])}))
