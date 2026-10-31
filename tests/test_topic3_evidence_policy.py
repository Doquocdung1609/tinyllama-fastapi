from app.topic3.evidence_policy import assess_candidate, requested_date


def row(period="August 2, 2026", label="Total assets", filing="hd", kind="table"):
    return {"chunk_id": "row-1", "filing_id": filing, "kind": kind, "text": f"Row 14: {label} | $ | 109,384", "source_text_hash": "source-row-hash", "metadata": {"reporting_periods": [period], "raw_content_hash": "raw-html-hash"}}


def test_explicit_date_parses_portably_on_windows():
    assert requested_date("assets on August 2, 2026") == "August 2, 2026"
    assert requested_date("assets in 2026") is None


def test_source_candidate_never_becomes_verified_numeric_answer():
    result = assess_candidate("What were total assets on August 2, 2026?", "HD", ["row-1"], {"row-1": row()}, {"hd": "HD"})
    assert result["status"] == "SOURCE_SUPPORTED_UNREVIEWED"
    assert result["numeric_answer_eligible"] is False


def test_wrong_issuer_period_metric_and_unresolved_row_abstain():
    chunks = {"row-1": row()}
    issuers = {"hd": "HD"}
    assert assess_candidate("Apple total assets on August 2, 2026?", "AAPL", ["row-1"], chunks, issuers)["status"] == "UNSUPPORTED_REQUEST"
    assert assess_candidate("Total assets on August 2, 2037?", "HD", ["row-1"], chunks, issuers)["reason"] == "PERIOD_NOT_IN_LOCKED_CORPUS"
    assert assess_candidate("Cash equivalents on August 2, 2026?", "HD", ["row-1"], chunks, issuers)["reason"] == "TOP1_METRIC_MISMATCH"
    chunks["row-1"] = row(label="Assets")
    assert assess_candidate("Assets on August 2, 2026?", "HD", ["row-1"], chunks, issuers)["reason"] == "ROW_LABEL_UNRESOLVED"
