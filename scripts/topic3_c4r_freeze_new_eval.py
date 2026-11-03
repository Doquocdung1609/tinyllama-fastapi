"""Freeze source-first XBRL reference facts before any C4R method outputs.

The private manifest has reference answers. Public JSON has counts/hashes only.
No ranking or retriever output is read by this script.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import warnings
import zipfile

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

PACKAGES = {
    "G3_NINE": r"C:\Users\Admin\Downloads\V7A_G3_SEC_SOURCE_HANDOFF_20261102.zip",
    "G3R_EIGHT": r"C:\Users\Admin\Downloads\V7A_G3R_EIGHT_DISPUTE_SEC_PRIMARY_20261102.zip",
    "G3S_THIRTY": r"C:\Users\Admin\Downloads\V7A_G3S_SEC47_SOURCE_RECOVERY_20261102_SOURCE_HANDOFF.zip",
}
CONCEPTS = {
    "NET_INCOME": ("NetIncomeLoss", "net income"),
    "TOTAL_ASSETS": ("Assets", "total assets"),
    "CASH_EQUIVALENTS": ("CashAndCashEquivalentsAtCarryingValue", "cash and cash equivalents"),
    "CURRENT_ASSETS": ("AssetsCurrent", "total current assets"),
    "CURRENT_LIABILITIES": ("LiabilitiesCurrent", "total current liabilities"),
    "ACCOUNTS_RECEIVABLE": ("AccountsNotesAndOtherReceivablesNetCurrent", "accounts receivable"),
    "COST_OF_SALES": ("CostOfRevenue", "cost of sales"),
    "TOTAL_REVENUE": ("RevenueFromContractWithCustomerExcludingAssessedTax", "total net sales"),
    "OPERATING_INCOME": ("OperatingIncomeLoss", "operating income"),
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _context(tag) -> tuple[str | None, str | None, bool]:
    if tag is None:
        return None, None, False
    if tag.find(lambda t: t.name and (t.name.endswith("explicitmember") or t.name.endswith("typedmember"))):
        return None, None, False
    start = tag.find(lambda t: t.name and t.name.endswith("startdate"))
    end = tag.find(lambda t: t.name and (t.name.endswith("enddate") or t.name.endswith("instant")))
    return (start.get_text(strip=True) if start else None,
            end.get_text(strip=True) if end else None, True)


def source_facts(source: dict, raw: bytes) -> list[dict]:
    if sha(raw) != source["sha256"] or len(raw) != source["byte_size"]:
        raise ValueError("Source bytes do not match SEC47 frozen manifest")
    soup = BeautifulSoup(raw, "lxml")
    contexts = {t.get("id"): t for t in soup.find_all(lambda t: t.name and t.name.endswith("context"))}
    facts = []
    for tag in soup.find_all(lambda t: t.name and t.name.endswith("nonfraction")):
        full_name = tag.get("name", "")
        if not full_name.startswith("us-gaap:"):
            continue
        match = [(code, phrase) for code, (concept, phrase) in CONCEPTS.items()
                 if full_name == "us-gaap:" + concept]
        if not match:
            continue
        start, end, unsegmented = _context(contexts.get(tag.get("contextref")))
        if not unsegmented or end != source["report_date"]:
            continue
        if start:
            span = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
            if source["form"] == "10-K" and not 300 <= span <= 380:
                continue
            if source["form"] == "10-Q" and not 70 <= span <= 110:
                continue
        if tag.get("unitref", "").lower() != "usd" or tag.get("scale") != "6":
            continue
        literal = tag.get_text(" ", strip=True).replace("$", "").strip()
        if not re.fullmatch(r"\(?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?|\d+(?:\.\d+)?", literal):
            continue
        numeric = Decimal(literal.strip("()").replace(",", ""))
        if literal.startswith("(") or tag.get("sign") == "-":
            numeric = -numeric
        code, phrase = match[0]
        facts.append({"metric": code, "phrase": phrase, "value_decimal": str(numeric),
                      "value_literal": literal, "period_start": start, "period_end": end,
                      "duration_type": "INSTANT" if not start else "FY" if source["form"] == "10-K" else "3M",
                      "unit": "USD_MILLIONS", "currency": "USD", "scale": 6,
                      "context_ref": tag.get("contextref"), "source_element_id": tag.get("id"),
                      "concept": full_name})
    return facts


def freeze(source_manifest: Path, private_path: Path, public_path: Path) -> dict:
    if private_path.exists() or public_path.exists():
        raise FileExistsError("New evaluation already frozen")
    source_data = json.loads(source_manifest.read_text(encoding="utf-8"))
    if source_data["verified"] != 47:
        raise ValueError("SEC47 source register incomplete")
    archives = {key: zipfile.ZipFile(path) for key, path in PACKAGES.items()}
    try:
        for key, archive in archives.items():
            if archive.testzip() is not None:
                raise ValueError(f"Source ZIP CRC failed: {key}")
        per_form = {"10-K": [], "10-Q": []}
        for source in source_data["sources"]:
            if source["form"] not in per_form:
                continue
            raw = archives[source["origin_package"]].read(source["source_zip_member"])
            facts = source_facts(source, raw)
            if not facts:
                continue
            # Stable source-only choice, independent of any retrieval output.
            facts.sort(key=lambda f: sha((source["accession"] + f["concept"]).encode()))
            fact = facts[0]
            period = (f"for the fiscal year ended {fact['period_end']}" if fact["duration_type"] == "FY"
                      else f"for the three months ended {fact['period_end']}" if fact["duration_type"] == "3M"
                      else f"as of {fact['period_end']}")
            question = (f"What {fact['phrase']} did {source['ticker']} report {period} "
                        f"in its {source['form']}, in USD millions?")
            per_form[source["form"]].append({
                "question_id": "C4R_N_" + source["accession"], "question": question,
                "ticker": source["ticker"], "form": source["form"],
                "accession": source["accession"], "source_url": source["source_url"],
                "source_sha256": source["sha256"], "source_zip_member": source["source_zip_member"],
                "source_package": source["origin_package"], "source_locator":
                source["source_url"] + "#" + str(fact["source_element_id"]),
                "reference_status": "SOURCE_XBRL_MACHINE_VERIFIED_UNREVIEWED",
                "scope": "CONSOLIDATED_UNSEGMENTED_XBRL_CONTEXT",
                **fact,
            })
    finally:
        for archive in archives.values():
            archive.close()
    # Eight annual and eight quarterly facts; four dev and twelve new holdout.
    selected = sorted(per_form["10-K"], key=lambda r: sha(r["accession"].encode()))[:8]
    selected += sorted(per_form["10-Q"], key=lambda r: sha(r["accession"].encode()))[:8]
    if len(selected) != 16 or len({r["accession"] for r in selected}) != 16:
        raise ValueError(f"Insufficient distinct source-first XBRL facts: {len(selected)}")
    selected.sort(key=lambda r: sha(r["question_id"].encode()))
    for i, row in enumerate(selected):
        row["split"] = "DEV" if i < 4 else "HOLDOUT"
    private = {"schema": "c4r_source_first_reference/v1", "created_utc": datetime.now(timezone.utc).isoformat(),
               "source_manifest_sha256": sha(source_manifest.read_bytes()), "selection":
               "One unsegmented USD-millions primary iXBRL fact per filing, source-hash verified, stable hash choice; no retriever output read",
               "facts": selected}
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_text(json.dumps(private, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    public = {"schema": "c4r_new_evaluation_public_lock/v1",
              "private_manifest_sha256": sha(private_path.read_bytes()),
              "source_manifest_sha256": private["source_manifest_sha256"],
              "facts": len(selected), "dev": 4, "holdout": 12,
              "forms": {form: sum(r["form"] == form for r in selected) for form in per_form},
              "reference_status": "SOURCE_XBRL_MACHINE_VERIFIED_UNREVIEWED",
              "query_new_not_document_unseen": True,
              "original_chunk_qrels": "NOT_CREATED",
              "question_answer_fields_committed": False}
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    return public


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-manifest", required=True, type=Path)
    p.add_argument("--private", required=True, type=Path)
    p.add_argument("--public", required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(freeze(a.source_manifest, a.private, a.public), indent=2))
