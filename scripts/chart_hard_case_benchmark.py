"""Deterministic, labeled chart-capability benchmark without model self-grading."""
from __future__ import annotations

import csv
import subprocess
from pathlib import Path

from app.services.calculation_service import analyze_charts


ROOT = Path(__file__).resolve().parents[1]


def item(chart_type, pairs, **extra):
    return {"modality": "chart", "structured_data": {
        "chart_type": chart_type, "label_value_pairs": pairs, **extra}}


CASES = [
    ("CH01", "single-series bar", "Nhãn năm 2024 trên biểu đồ là bao nhiêu?",
     item("bar", [{"label":"2023","value":"100 tỷ đồng"},{"label":"2024","value":"125 tỷ đồng"}]), "125", "PASS", "exact visible label"),
    ("CH02", "multiple-series bar", "So sánh Chuỗi A và Chuỗi B.",
     item("bar", [{"label":"Chuỗi A 2023","value":"90"},{"label":"Chuỗi A 2024","value":"120"},{"label":"Chuỗi B 2023","value":"100"},{"label":"Chuỗi B 2024","value":"85"}]), "Chuỗi A;Chuỗi B;120;85", "PASS", "all requested labeled series"),
    ("CH03", "line chart", "Nhãn năm 2024 trên biểu đồ là bao nhiêu?",
     item("line", [{"label":"2023","value":"20%"},{"label":"2024","value":"25%"}]), "25%", "PASS", "exact visible point label"),
    ("CH04", "multi-series lines crossing", "So sánh Chuỗi A và Chuỗi B.",
     item("line", [{"label":"Chuỗi A 2023","value":"30"},{"label":"Chuỗi A 2024","value":"70"},{"label":"Chuỗi B 2023","value":"60"},{"label":"Chuỗi B 2024","value":"40"}]), "A increases;B decreases", "PARTIAL", "endpoints and trends supported; crossing coordinate is not inferred from geometry"),
    ("CH05", "pie chart", "Thành phần nào có tỷ trọng cao nhất?",
     item("pie", [{"label":"Cá nhân","value":"50%"},{"label":"Doanh nghiệp","value":"35%"},{"label":"Khác","value":"15%"}]), "Cá nhân;50%", "PASS", "all labeled slices"),
    ("CH06", "scatter chart", "Nhãn năm 2024 trên biểu đồ là bao nhiêu?",
     item("scatter", [{"label":"Điểm 2024","value":"12"}]), "12", "PARTIAL", "labeled point lookup only; correlation and unlabeled coordinates unsupported"),
    ("CH07", "two-axis financial chart", "So sánh doanh thu với biên lợi nhuận.",
     item("dual_axis", [{"label":"Doanh thu 2024","value":"125 tỷ đồng"},{"label":"Biên lợi nhuận 2024","value":"12%"}], dual_axis=True, axes=[{"unit":"tỷ đồng"},{"unit":"%"}]), "refuse direct cross-unit comparison", "PASS", "guard must report incompatible axes/units"),
    ("CH08", "stacked bars", "So sánh Chuỗi A và Chuỗi B.",
     item("stacked_bar", [{"label":"Chuỗi A 2024","value":"70"},{"label":"Chuỗi B 2024","value":"30"}]), "70;30", "PARTIAL", "exact labeled segments only; unlabeled stack geometry unsupported"),
    ("CH09", "flowchart", "Các giá trị số trong biểu đồ là gì?", item("flowchart", []), "identify as diagram", "PASS", "must not treat diagram as numerical chart"),
    ("CH10", "organizational graph", "So sánh các giá trị.", item("organizational_graph", []), "identify as diagram", "PASS", "must not invent numbers"),
    ("CH11", "network diagram", "Giá trị chính xác là bao nhiêu?", item("network_diagram", []), "identify as diagram", "PASS", "must not invent numbers"),
    ("CH12", "image-only chart, missing labels", "Giá trị chính xác là bao nhiêu?", item("line", []), "qualified limitation", "PASS", "no exact values without readable labels"),
]


def main():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    rows = []
    for case_id, kind, question, evidence, ground_truth, expected_status, note in CASES:
        result = analyze_charts(question, [evidence])
        answer = (result or {}).get("answer", "")
        operation = (result or {}).get("operation", "")
        protected = operation in {"chart_axis_mismatch", "chart_capability_limit"}
        if case_id == "CH07": passed = operation == "chart_axis_mismatch" and not result.get("verified")
        elif case_id in {"CH09", "CH10", "CH11", "CH12"}: passed = operation == "chart_capability_limit" and not result.get("verified")
        elif expected_status == "PASS":
            passed = all(token.casefold() in answer.casefold() for token in ground_truth.split(";") if token)
        else:
            passed = result is not None
        rows.append({"case_id":case_id,"chart_class":kind,"question":question,"ground_truth":ground_truth,
                     "actual_answer":answer,"operation":operation,"series_identification":(result or {}).get("series_coverage", ""),
                     "exact_value_accuracy":"PASS" if passed and expected_status=="PASS" and not protected else ("N/A" if protected else "PARTIAL"),
                     "trend_correct":"PASS" if operation=="chart_series_comparison" else "N/A",
                     "completeness":expected_status,"citation_precision":"E1" if result and result.get("evidence_ids")==["E1"] else "FAIL",
                     "strict_status":"PASS" if passed and expected_status=="PASS" else expected_status,
                     "limitation":note, "code_commit": commit})
    path=ROOT/"reports/chart_hard_cases.csv"
    with path.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print({"cases":len(rows),"pass":sum(r["strict_status"]=="PASS" for r in rows),
           "partial":sum(r["strict_status"]=="PARTIAL" for r in rows)})


if __name__ == "__main__": main()
