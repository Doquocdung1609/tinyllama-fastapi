"""Run persistent multi-turn document chats through the real FastAPI API."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from time import perf_counter, sleep
import requests

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8002")
    parser.add_argument("--documents", default=str(ROOT / "reports" / "final_product_fixture_documents.json"))
    args = parser.parse_args()
    api = args.api.rstrip("/")
    docs = json.loads(Path(args.documents).read_text(encoding="utf-8"))
    did = lambda name: docs[name]["document_id"]
    transcripts: list[dict] = []
    rows: list[dict] = []

    def create(scope, title):
        response = requests.post(api + "/conversations", json={"active_document_ids": scope, "title": title}, timeout=30)
        response.raise_for_status()
        return response.json()

    def ask(conversation_id, content):
        started = perf_counter()
        response = requests.post(f"{api}/conversations/{conversation_id}/messages",
            json={"content": content, "top_k": 5, "score_threshold": .55, "model": "qwen2.5:3b"}, timeout=360)
        elapsed = round((perf_counter() - started) * 1000, 1)
        data = response.json()
        transcripts.append({"conversation_id": conversation_id, "question": content,
                            "status_code": response.status_code, "elapsed_ms": elapsed, "response": data})
        return response, data, elapsed

    code_commit = __import__("subprocess").run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()

    def record(case_id, description, passed, data, elapsed, note="", *, expected_claims="",
               expected_numeric_values="", answer_correct=None, answer_complete=None,
               numerical_correct=None, citation_correct=None, refusal_correct=None,
               context_resolution_correct=None, extraction_correct=None, failure_category=""):
        assistant = data.get("assistant_message", {}) if isinstance(data, dict) else {}
        rag = data.get("rag", {}) if isinstance(data, dict) else {}
        dimensions = {
            "answer_correct": bool(passed if answer_correct is None else answer_correct),
            "answer_complete": bool(passed if answer_complete is None else answer_complete),
            "numerical_correct": bool(passed if numerical_correct is None else numerical_correct),
            "citation_correct": bool(passed if citation_correct is None else citation_correct),
            "refusal_correct": bool(passed if refusal_correct is None else refusal_correct),
            "context_resolution_correct": bool(passed if context_resolution_correct is None else context_resolution_correct),
            "extraction_correct": bool(passed if extraction_correct is None else extraction_correct),
        }
        strict_pass = bool(passed) and all(dimensions.values())
        rows.append({"test_id": case_id, "description": description,
                     "document_id": ",".join((assistant.get("retrieval_metadata") or {}).get("active_document_ids", [])),
                     "document_hash": "", "conversation_id": assistant.get("conversation_id", ""),
                     "source_pages": ",".join(str(item.get("page")) for item in assistant.get("citations", [])),
                     "expected_claims": expected_claims, "expected_numeric_values": expected_numeric_values,
                     "actual_answer": assistant.get("content", data.get("detail", "") if isinstance(data, dict) else ""),
                     "selected_evidence": json.dumps((assistant.get("retrieval_metadata") or {}).get("selected_evidence", []), ensure_ascii=False),
                     "included_prompt_evidence": json.dumps([
                         {"evidence_id": item.get("evidence_id"), "source_id": item.get("source_id"), "page": item.get("page")}
                         for item in rag.get("included_prompt_context", [])], ensure_ascii=False),
                     **dimensions, "strict_status": "PASS" if strict_pass else "FAIL",
                     "failure_category": "" if strict_pass else (failure_category or "ASSERTION_FAILURE"),
                     "explanation": note,
                     "resolved_question": assistant.get("resolved_question", ""),
                     "latency_ms": elapsed, "model": assistant.get("model", ""), "code_commit": code_commit})

    # C01: carry metric/year into a deterministic follow-up calculation.
    c = create([did("B_mixed_text_table.pdf")], "C01 revenue growth")
    ask(c["conversation_id"], "Doanh thu năm 2024 là bao nhiêu?")
    _, result, elapsed = ask(c["conversation_id"], "So với năm trước tăng bao nhiêu phần trăm?")
    resolved = result.get("resolution", {}).get("resolved_question", "")
    answer = result.get("assistant_message", {}).get("content", "")
    record("C01", "revenue then prior-year growth", "2024" in resolved and "2023" in resolved and "25%" in answer,
           result, elapsed)

    # C02: calculation method remains tied to the active ratio and year.
    c = create([did("C_financial_statement.pdf")], "C02 ratio formula")
    ask(c["conversation_id"], "Tỷ lệ thanh toán hiện hành năm 2024 là bao nhiêu?")
    _, result, elapsed = ask(c["conversation_id"], "Tỷ lệ đó được tính như thế nào?")
    answer = result.get("assistant_message", {}).get("content", "")
    record("C02", "ratio then formula", "750" in answer and "375" in answer and "2" in answer, result, elapsed)

    # C03: chart follow-up must retain and enumerate both series.
    c = create([did("D_bar_line_charts.pdf")], "C03 chart series")
    ask(c["conversation_id"], "Biểu đồ đường có những chuỗi dữ liệu nào?")
    _, result, elapsed = ask(c["conversation_id"], "So sánh chuỗi thứ hai với chuỗi thứ nhất.")
    answer = result.get("assistant_message", {}).get("content", "")
    record("C03", "second chart series vs first", all(term in answer for term in ("Chuỗi A", "Chuỗi B", "tăng", "giảm")), result, elapsed)

    # C04: two-document scope, then explicitly refer to the bilingual report.
    scope = [did("B_mixed_text_table.pdf"), did("J_mixed_vi_en.pdf")]
    c = create(scope, "C04 two reports")
    ask(c["conversation_id"], "Trong bảng tiếng Việt, doanh thu năm 2024 là bao nhiêu?")
    _, result, elapsed = ask(c["conversation_id"], "Thế còn tài liệu song ngữ?")
    cited_docs = {item.get("document_id") for item in result.get("assistant_message", {}).get("citations", [])}
    record("C04", "follow-up across two selected PDFs", did("J_mixed_vi_en.pdf") in cited_docs and cited_docs <= set(scope), result, elapsed)

    # C05: resolve ordinal table reference on the previously cited page.
    c = create([did("L_mixed_text_table_chart.pdf")], "C05 second table")
    ask(c["conversation_id"], "Trang 1 có các bảng và biểu đồ nào?")
    _, result, elapsed = ask(c["conversation_id"], "Giải thích bảng thứ hai trên trang đó.")
    assistant = result.get("assistant_message", {})
    answer = assistant.get("content", "")
    selected = (assistant.get("retrieval_metadata") or {}).get("selected_evidence", [])
    citations = assistant.get("citations", [])
    structural = result.get("rag", {}).get("structural_validation", {})
    source_ok = any(item.get("source_id") == "table:p1:t2" for item in selected)
    citation_ok = any(item.get("source_id") == "table:p1:t2" for item in citations)
    content_ok = all(term in answer for term in ("Dòng tiền", "2023", "2024", "20", "28"))
    complete = structural.get("status") == "FULL" and set(structural.get("required_facets", [])) <= set(structural.get("covered_facets", []))
    record("C05", "second table on cited page", source_ok and citation_ok and content_ok and complete, result, elapsed,
           expected_claims="table:p1:t2; Dòng tiền; Kinh doanh; periods 2023/2024; unit status",
           expected_numeric_values="20;28", answer_correct=content_ok, answer_complete=complete,
           numerical_correct=("20" in answer and "28" in answer), citation_correct=citation_ok,
           context_resolution_correct=("table:p1:t2" in result.get("resolution", {}).get("resolved_question", "")),
           extraction_correct=source_ok, refusal_correct=True, failure_category="TABLE_COMPLETENESS")

    # C06: explicit year switch becomes the active period.
    c = create([did("B_mixed_text_table.pdf")], "C06 year switch")
    ask(c["conversation_id"], "Doanh thu năm 2024 là bao nhiêu?")
    ask(c["conversation_id"], "Chuyển sang năm 2023.")
    _, result, elapsed = ask(c["conversation_id"], "Chỉ tiêu đó là bao nhiêu?")
    resolved = result.get("resolution", {}).get("resolved_question", "")
    record("C06", "explicit active-period switch", "2023" in resolved and "2024" not in resolved, result, elapsed)

    # C07: alternate between conversations and assert their scopes never cross.
    first = create([did("B_mixed_text_table.pdf")], "C07 A")
    second = create([did("C_financial_statement.pdf")], "C07 B")
    _, r1, e1 = ask(first["conversation_id"], "Doanh thu năm 2024?")
    _, r2, e2 = ask(second["conversation_id"], "Tổng tài sản năm 2024?")
    _, r3, e3 = ask(first["conversation_id"], "Lợi nhuận thì sao?")
    scopes = [(item.get("assistant_message", {}).get("retrieval_metadata") or {}).get("active_document_ids") for item in (r1, r2, r3)]
    record("C07", "conversation switching isolation", scopes == [[did("B_mixed_text_table.pdf")], [did("C_financial_statement.pdf")], [did("B_mixed_text_table.pdf")]], r3, e1+e2+e3)

    # C08: a fresh GET restores the server-persisted session and all turns.
    restored = requests.get(f"{api}/conversations/{first['conversation_id']}", timeout=30).json()
    record("C08", "persistent restoration", len(restored.get("messages", [])) == 4 and restored.get("last_message_id"),
           {"assistant_message": restored["messages"][-1]}, 0.0, "GET after independent requests")

    # C09: correction explicitly rechecks the earlier question against evidence.
    c = create([did("B_mixed_text_table.pdf")], "C09 correction")
    ask(c["conversation_id"], "Lợi nhuận năm 2024 là 15 triệu đồng đúng không?")
    _, result, elapsed = ask(c["conversation_id"], "Hãy sửa câu trả lời trước và kiểm tra lại nguồn.")
    resolved = result.get("resolution", {}).get("resolved_question", "")
    assistant = result.get("assistant_message", {})
    answer = assistant.get("content", "")
    citations = assistant.get("citations", [])
    calculations = assistant.get("referenced_calculations", [])
    verification = next((item for item in calculations if item.get("operation") == "claim_verification"), {})
    status_ok = verification.get("verification_status") == "CONTRADICTED"
    answer_ok = "Không đúng" in answer and "16" in answer and "15" in answer
    citation_ok = any(item.get("source_id") == "table:p1:t1" for item in citations)
    context_ok = "kiểm tra lại" in resolved.casefold() and "15" in resolved
    record("C09", "evidence-based correction", status_ok and answer_ok and citation_ok and context_ok, result, elapsed,
           expected_claims="claimed 15 is contradicted; source profit 2024 is 16",
           expected_numeric_values="claim=15;source=16", answer_correct=answer_ok,
           answer_complete=status_ok and answer_ok, numerical_correct=verification.get("source_value") == 16,
           citation_correct=citation_ok, refusal_correct=True, context_resolution_correct=context_ok,
           extraction_correct=bool(verification.get("source_cells")) and
               verification["source_cells"][0].get("row", "").casefold().startswith("lợi nhuận") and
               verification["source_cells"][0].get("column") == "2024" and
               verification["source_cells"][0].get("value") == "16",
           failure_category="CLAIM_VERIFICATION")

    # C10: deleted source produces a conflict, never stale evidence reuse.
    fixture = ROOT / "tests" / "fixtures" / "pdfs" / "A_text_only_vi.pdf"
    with fixture.open("rb") as stream:
        uploaded = requests.post(api + "/documents/upload", files={"file": (fixture.name, stream, "application/pdf")}, timeout=60).json()
    temporary_id = uploaded["document_id"]
    for _ in range(120):
        status = requests.get(f"{api}/documents/{temporary_id}", timeout=20).json()
        if status.get("status") in {"READY", "PARTIAL", "FAILED"}:
            break
        sleep(.5)
    c = create([temporary_id], "C10 removed document")
    requests.delete(f"{api}/documents/{temporary_id}", timeout=30).raise_for_status()
    response, result, elapsed = ask(c["conversation_id"], "Năng lực hấp thụ là gì?")
    record("C10", "removed-document handling", response.status_code == 409 and "không còn tồn tại" in result.get("detail", ""), result, elapsed)

    # C11: unresolved elliptical question asks one concise clarification.
    c = create([did("B_mixed_text_table.pdf")], "C11 clarification")
    _, result, elapsed = ask(c["conversation_id"], "So với năm trước thì sao?")
    assistant = result.get("assistant_message", {})
    record("C11", "ambiguous follow-up clarification", assistant.get("processing_status") == "NEEDS_CLARIFICATION", result, elapsed)

    # C12: one answer must cite both sides of a multi-page boundary.
    c = create([did("I_multipage_table.pdf")], "C12 multi-page")
    _, result, elapsed = ask(c["conversation_id"], "So sánh giá trị của mã A15 và A16 trong bảng nhiều trang.")
    pages = {item.get("page") for item in result.get("assistant_message", {}).get("citations", [])}
    answer = result.get("assistant_message", {}).get("content", "")
    record("C12", "multi-page evidence", pages == {1, 2} and "150" in answer and "160" in answer, result, elapsed)

    reports = ROOT / "reports"
    for name in ("conversation_api_tests.csv", "multiturn_rag_benchmark.csv"):
        with (reports / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    (reports / "multiturn_rag_benchmark_details.json").write_text(
        json.dumps(transcripts, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Actual multi-turn transcripts", ""]
    for item in transcripts:
        response = item["response"]
        lines += [f"## {item['conversation_id'][:8]} · {item['elapsed_ms']} ms", "",
                  f"**User:** {item['question']}", "",
                  f"**Resolved:** {response.get('resolution', {}).get('resolved_question', '')}", "",
                  f"**Assistant:** {response.get('assistant_message', {}).get('content', response.get('detail', ''))}", ""]
    (reports / "multiturn_transcripts.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"total": len(rows), "pass": sum(row["strict_status"] == "PASS" for row in rows),
                      "failures": [row["test_id"] for row in rows if row["strict_status"] != "PASS"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
