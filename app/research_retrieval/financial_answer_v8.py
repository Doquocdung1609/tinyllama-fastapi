"""Common source-grounded answerer for author and A5 retrieval arms.

The optional source-enriched track reads SEC iXBRL only for an accession that
was returned by an original-chunk retriever. It never reads evaluation gold.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import zipfile

from app.research_retrieval.faith_r_a5 import A5Plan, plan_query
from scripts.topic3_c4r_freeze_new_eval import source_facts


@dataclass(frozen=True)
class FinancialAnswerV8:
    status: str
    final_answer_literal: str | None
    value_decimal: str | None
    unit: str | None
    currency: str | None
    period_start: str | None
    period_end: str | None
    duration_type: str | None
    scope: str | None
    accession: str | None
    original_chunk_id: str | None
    source_locator: str | None
    source_sha256: str | None
    error_code: str | None
    confidence: float


def abstain(code: str) -> FinancialAnswerV8:
    return FinancialAnswerV8("ABSTAIN", None, None, None, None, None, None, None,
                             None, None, None, None, None, code, 0.0)


class SourceArchiveAnswererV8:
    def __init__(self, source_manifest: Path):
        manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
        if manifest["verified"] != 47:
            raise ValueError("SEC47 source manifest incomplete")
        self.sources = {s["accession"]: s for s in manifest["sources"]}
        self.package_paths = {key: Path(item["path"]) for key, item in
                              manifest.get("source_packages", {}).items()}
        self._facts: dict[str, list[dict]] = {}
        self._archives: dict[str, zipfile.ZipFile] = {}

    def close(self) -> None:
        for archive in self._archives.values():
            archive.close()

    def _source_facts(self, accession: str) -> list[dict]:
        if accession not in self._facts:
            source = self.sources[accession]
            package = source["origin_package"]
            if package not in self._archives:
                self._archives[package] = zipfile.ZipFile(self.package_paths[package])
            raw = self._archives[package].read(source["source_zip_member"])
            self._facts[accession] = source_facts(source, raw)
        return self._facts[accession]

    @staticmethod
    def _match_period(fact: dict, plan: A5Plan) -> bool:
        if plan.period_end and fact["period_end"] != plan.period_end:
            return False
        if not plan.period_end and plan.fiscal_year and not fact["period_end"].startswith(str(plan.fiscal_year)):
            return False
        if plan.statement == "BALANCE":
            return fact["duration_type"] == "INSTANT"
        if plan.duration_months == 12:
            return fact["duration_type"] == "FY"
        if plan.duration_months == 3:
            return fact["duration_type"] == "3M"
        return True

    def answer(self, question: str, hits: list[dict], track: str = "SOURCE_ENRICHED_V1") -> FinancialAnswerV8:
        if track not in {"SOURCE_ENRICHED_V1", "ORIGINAL_CHUNK_ONLY"}:
            raise ValueError("INVALID_ANSWER_TRACK")
        plan = plan_query(question)
        if plan.metric is None or plan.intent != "FINANCIAL_NUMERIC" or plan.issuer is None:
            return abstain("UNSUPPORTED_OR_AMBIGUOUS_QUERY")
        if plan.scope == "PARENT":
            return abstain("PARENT_SCOPE_NOT_VERIFIABLE_IN_THIS_SEC_TRACK")
        if len(plan.requested_years) > 1:
            return abstain("MULTI_PERIOD_SET_NOT_VERIFIABLE")
        if track == "ORIGINAL_CHUNK_ONLY":
            # Flattened original text loses the iXBRL context/column binding.
            # A pipe and nearby number are not a verified cell.
            return abstain("ORIGINAL_CHUNK_COLUMN_CONTEXT_NOT_VERIFIED")
        seen = set()
        for hit in hits[:5]:
            accession = hit.get("accession_number") or hit.get("document_id", "").split("_")[-1]
            if accession in seen or accession not in self.sources:
                continue
            seen.add(accession)
            source = self.sources[accession]
            if source["ticker"] != plan.issuer or (plan.form and source["form"] != plan.form):
                continue
            if plan.period_end and source["report_date"] != plan.period_end:
                continue
            eligible = [f for f in self._source_facts(accession)
                        if f["metric"] == plan.metric and self._match_period(f, plan)]
            values = {(f["value_decimal"], f["unit"], f["period_start"], f["period_end"])
                      for f in eligible}
            if len(values) > 1:
                return abstain("SOURCE_CELL_AMBIGUOUS_MULTIPLE_VALUES")
            if not eligible:
                continue
            fact = eligible[0]
            vietnamese = bool(re.search(r"\b(?:báo cáo|bao nhiêu|triệu|tỷ|ngày|quý)\b",
                                         plan.matching_view))
            literal = (f"Giá trị được xác minh: {fact['value_literal']} triệu USD "
                       f"(kỳ kết thúc {fact['period_end']})." if vietnamese else
                       f"{fact['value_literal']} USD millions ({fact['period_end']})")
            return FinancialAnswerV8(
                "VERIFIED_SOURCE_CELL", literal, fact["value_decimal"],
                fact["unit"], fact["currency"], fact["period_start"], fact["period_end"],
                fact["duration_type"], "CONSOLIDATED_UNSEGMENTED_XBRL_CONTEXT",
                accession, hit["chunk_id"], source["source_url"] + "#" + str(fact["source_element_id"]),
                source["sha256"], None, 1.0)
        return abstain("NO_MATCHING_SOURCE_CELL_FROM_RETRIEVED_TOP5")
