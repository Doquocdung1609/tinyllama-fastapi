"""Prepare source-first, unjudged SEC review packets without retrieval results."""

from __future__ import annotations

import csv
import argparse
import hashlib
import html
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup

from topic3_v5r_restore import REPO, SOURCE

QUEUE = REPO / "docs/topic3_v5/recovery_live/holdout_30_review_queue.csv"
SNAPSHOTS = REPO / "tmp/topic3_v5r/sec_html"
OUT = REPO / "docs/topic3_v6/V6_SOURCE_FIRST_REVIEW_PACKETS"
STOP = {"what", "were", "was", "did", "the", "a", "an", "of", "in", "for", "at", "how", "much", "from",
        "with", "and", "between", "report", "reported", "compare", "compared", "change", "differ", "difference",
        "fy2022", "fy2023", "fy2024", "fy2025", "fy2037", "fiscal", "year", "end", "total", "portion", "will",
        "to", "be", "do", "its", "its'", "attributed", "locate", "filing", "annual",
        "apple", "microsoft", "nvidia", "amazon", "meta", "tesla", "intel", "amd", "s", "s'", "activities"}
ALIASES = {"revenues": "revenue", "sales": "sales", "purchases": "purchase", "expenses": "expense",
           "equivalents": "equivalent", "operating": "operating", "expenditures": "expenditure"}


def terms(value: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9]+", value.casefold())
    return {ALIASES.get(w, w) for w in words if w not in STOP and not re.fullmatch(r"20\d{2}", w)}


def compact(value: str, limit: int = 800) -> str:
    return re.sub(r"\s+", " ", value).strip()[:limit]


def table_candidates(soup: BeautifulSoup, query_terms: set[str]) -> list[dict]:
    choices = []
    for index, table in enumerate(soup.find_all("table")):
        rows = []
        for tr in table.find_all("tr"):
            cells = [compact(c.get_text(" ", strip=True), 300) for c in tr.find_all(["th", "td"], recursive=False)]
            if cells and any(cells):
                rows.append(cells)
        if not rows:
            continue
        for row_index, cells in enumerate(rows):
            row_text = " | ".join(cells)
            overlap = query_terms & terms(row_text)
            if not overlap:
                continue
            score = len(overlap) * 10 + (6 if len(overlap) == len(query_terms) else 0)
            score += min(3, len(re.findall(r"\b\d[\d,.]*\b", row_text)))
            choices.append({"kind": "SEC_HTML_TABLE_ROW", "table_index_zero_based": index,
                            "row_index_zero_based": row_index, "score": score,
                            "matched_terms": sorted(overlap), "row_cells": cells,
                            "candidate_row_label": cells[0],
                            "candidate_header_rows": rows[:min(4, row_index)],
                            "neighbor_before": rows[row_index - 1] if row_index else None,
                            "neighbor_after": rows[row_index + 1] if row_index + 1 < len(rows) else None,
                            "numeric_tokens_unassigned": re.findall(r"(?<!\w)\(?-?\$?\d[\d,.]*\)?%?", row_text)[:20]})
    return sorted(choices, key=lambda x: (-x["score"], x["table_index_zero_based"], x["row_index_zero_based"]))[:6]


def prose_candidates(soup: BeautifulSoup, query_terms: set[str]) -> list[dict]:
    choices = []
    for index, node in enumerate(soup.find_all(["p", "div"])):
        if node.find(["table", "p", "div"]):
            continue
        value = compact(node.get_text(" ", strip=True), 1100)
        if not 40 <= len(value) <= 1100:
            continue
        overlap = query_terms & terms(value)
        if len(overlap) < min(2, len(query_terms)):
            continue
        choices.append({"kind": "SEC_HTML_PROSE", "node_index_zero_based": index,
                        "score": len(overlap) * 10, "matched_terms": sorted(overlap), "text": value})
    return sorted(choices, key=lambda x: (-x["score"], x["node_index_zero_based"]))[:3]


def render_packet(packet: dict) -> str:
    source = html.escape(packet["source_url"], quote=True)
    rows = []
    for item in packet["source_first_table_candidates"]:
        locator = f"table {item['table_index_zero_based']}, row {item['row_index_zero_based']} (zero-based)"
        context = "\n".join(" | ".join(row).rstrip() for row in item["candidate_header_rows"][-3:])
        rows.append("<tr><td>" + html.escape(locator) + "</td><td><pre>" + html.escape(context) +
                    "</pre></td><td><pre>" + html.escape(" | ".join(item["row_cells"]).rstrip()) + "</pre></td></tr>")
    prose = "".join("<li><p>" + html.escape(item["text"]) + "</p></li>" for item in packet["source_first_prose_candidates"])
    warnings = "".join("<li>" + html.escape(warning) + "</li>" for warning in packet["warnings"])
    return ("<!doctype html><html lang='en'><meta charset='utf-8'><title>" + html.escape(packet["question_id"]) +
            " source review</title><style>body{font:16px system-ui;max-width:1300px;margin:2rem auto;padding:1rem}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:.6rem;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere}code{overflow-wrap:anywhere}.warn{background:#fff4dc;padding:1rem}</style>" +
            "<h1>" + html.escape(packet["question_id"]) + " · source-first review</h1><p class='warn'>Machine-prepared candidates; label UNJUDGED. Do not treat a row below as verified gold.</p>" +
            "<h2>Question</h2><p>" + html.escape(packet["question"]) + "</p><p>" +
            html.escape(packet["issuer"] + " · " + packet["form"] + " · " + packet["report_date"] + " · " + packet["accession"]) +
            " · <a href='" + source + "'>Open original SEC filing</a></p>" +
            "<h2>Review cautions</h2><ul>" + warnings + "</ul><h2>Candidate original HTML rows</h2><table><tr><th>Original locator</th><th>Header context</th><th>Row cells in source order</th></tr>" +
            "".join(rows) + "</table><h2>Candidate original prose</h2><ul>" + prose + "</ul>" +
            "<h2>Reviewer decision</h2><p>Record exact SEC source span, metric definition, row, period column, value, unit/scale and label in the review sheet. If multiple plausible rows conflict, mark UNCERTAIN and request a second reviewer. Confirm the requested period exists in the frozen filing.</p>" +
            "<p>Official HTML SHA-256: <code>" + packet["official_html_sha256"] + "</code></p></html>")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=QUEUE)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    queue_path, out = args.queue, args.out
    queue = list(csv.DictReader(queue_path.open(encoding="utf-8", newline="")))
    if len(queue) != 30 or any(r["label"] != "UNJUDGED" for r in queue):
        raise ValueError("Review queue changed or labels exposed")
    corpus = defaultdict(list)
    with zipfile.ZipFile(SOURCE) as archive:
        with archive.open("corpus/chunks_frozen.jsonl") as stream:
            for line in stream:
                row = json.loads(line)
                corpus[row["accession_number"]].append(row)
    out.mkdir(parents=True, exist_ok=True)
    packets = []
    for question in queue:
        accession = question["source_accession"]
        source = SNAPSHOTS / f"{accession}.html"
        if not source.is_file() or not corpus[accession]:
            raise ValueError(f"Missing source snapshot or frozen corpus: {accession}")
        soup = BeautifulSoup(source.read_bytes(), "html.parser")
        query_terms = terms(question["question"])
        candidates = table_candidates(soup, query_terms)
        prose = prose_candidates(soup, query_terms)
        first = corpus[accession][0]
        packet = {
            "question_id": question["question_id"], "question": question["question"],
            "category": question.get("category") or "FRESH_HOLDOUT_PENDING_REVIEW", "issuer": question["source_ticker"],
            "accession": accession, "form": first["document_type"],
            "filing_date": first["filing_date"], "report_date": question["sec_report_date"],
            "source_url": question["source_url"],
            "official_html_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "frozen_corpus_chunk_count": len(corpus[accession]),
            "frozen_corpus_period_labels": sorted({c["fiscal_period"] for c in corpus[accession]}),
            "query_terms_for_packet_search": sorted(query_terms),
            "source_first_table_candidates": candidates,
            "source_first_prose_candidates": prose,
            "machine_prepared_only": True, "label": "UNJUDGED",
            "review_fields": {"metric_definition": None, "statement_scope": None,
                              "selected_source_locator": None, "row_label": None,
                              "column_header": None, "period_year": None, "value": None,
                              "unit": None, "scale": None, "source_span": None,
                              "answerable_in_frozen_corpus": None, "reviewer": None,
                              "review_decision": None, "ambiguity_notes": None},
            "warnings": (["FY2037 is outside the filing period; verify unsupported status"]
                         if question.get("category") == "UNSUPPORTED_FUTURE" else []) +
                        (["Comparative question: check every requested year column"]
                         if question.get("category") == "COMPARATIVE_COLUMN" else []) +
                        (["Frozen source chunk header fiscal year differs from SEC report-date year; inspect original SEC header and corrected B metadata"]
                         if first["document_type"] == "10-K" and
                         first["fiscal_period"] != "FY" + question["sec_report_date"][:4] else []),
        }
        path = out / f"{question['question_id']}.json"
        path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (out / f"{question['question_id']}.html").write_text(render_packet(packet), encoding="utf-8")
        packets.append({"id": question["question_id"], "question": question["question"],
                        "url": question["source_url"], "accession": accession,
                        "table_candidates": len(candidates), "prose_candidates": len(prose),
                        "packet_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    rows = []
    for p in packets:
        rows.append("<tr><td><a href='" + html.escape(p["id"] + ".html") + "'>" + p["id"] + "</a> · <a href='" + html.escape(p["id"] + ".json") + "'>JSON</a></td><td>" +
                    html.escape(p["question"]) + "</td><td><a href='" + html.escape(p["url"]) +
                    "'>SEC " + html.escape(p["accession"]) + "</a></td><td>" +
                    str(p["table_candidates"]) + " table / " + str(p["prose_candidates"]) + " prose</td><td>UNJUDGED</td></tr>")
    (out / "index.html").write_text("<!doctype html><html lang='en'><meta charset='utf-8'><title>V6 SEC source-first review</title>"
                                    "<style>body{font:16px system-ui;max-width:1400px;margin:2rem auto;padding:1rem}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:.6rem;vertical-align:top}tr:nth-child(even){background:#f5f7fa}</style>"
                                    "<h1>V6 source-first review packets</h1><p>Machine-prepared candidates only. 0 independently reviewed. Open the official SEC page and packet JSON; choose the exact source row, period column, value and unit before labeling. No retrieval result was used to select these snippets.</p>"
                                    "<table><tr><th>ID</th><th>Question</th><th>Official source</th><th>Candidate snippets</th><th>Label</th></tr>" +
                                    "".join(rows) + "</table></html>", encoding="utf-8")
    manifest = {"status": "MACHINE_PREPARED_UNJUDGED", "question_count": len(packets),
                "independently_reviewed": 0, "packet_selection": "SEC original HTML table/prose lexical search; no Qdrant ranking or qrels",
                "queue_sha256": hashlib.sha256(queue_path.read_bytes()).hexdigest(), "packets": packets}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"packets": len(packets), "table_candidates": sum(p["table_candidates"] for p in packets),
                      "prose_candidates": sum(p["prose_candidates"] for p in packets),
                      "manifest_sha256": hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
