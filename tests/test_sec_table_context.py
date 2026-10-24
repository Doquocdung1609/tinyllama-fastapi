from hashlib import sha256

from app.financial_ingestion.chunker import chunk_filing
from app.financial_ingestion.html_parser import parse_sec_html
from test_sec_parser import metadata


def parse(body):
    raw = f"<html><body>{body}</body></html>".encode()
    item = metadata()
    item.raw_content_hash = sha256(raw).hexdigest()
    return parse_sec_html(raw, item)


def test_multilevel_td_headers_external_title_units_and_every_row_chunk_context():
    filing = parse('''<div>CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS</div>
    <div>(In millions, except per-share amounts)</div><table>
    <tr><td></td><td></td><td></td></tr>
    <tr><td rowspan="2">Metric</td><td colspan="2">Three Months Ended</td></tr>
    <tr><td>June 27, 2026</td><td>June 28, 2025</td></tr>
    <tr><td>Net sales</td><td>109,417</td><td>94,036</td></tr>
    <tr><td>Operating margin</td><td>12.5%</td><td>11.0%</td></tr>
    <tr><td>Net income (loss)</td><td>(45)</td><td>80</td></tr></table>''')
    table = filing.tables[0]
    assert table.statement_title == "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS"
    assert table.columns == ["Metric", "Three Months Ended / June 27, 2026",
                             "Three Months Ended / June 28, 2025"]
    assert table.row_indices == [3, 4, 5]
    assert "millions" in table.units
    assert len(table.context_locations) == 2
    chunks = [chunk for chunk in chunk_filing(filing) if chunk.kind == "table"]
    assert len(chunks) == 3
    for chunk in chunks:
        assert "Three Months Ended / June 27, 2026" in chunk.text
        assert "In millions, except per-share amounts" in chunk.text
        assert "STATEMENTS OF OPERATIONS" in chunk.text
        assert filing.metadata.cik in chunk.text
        assert filing.metadata.accession_number in chunk.text
        assert filing.metadata.source_url in chunk.text
        assert chunk.source_location.row_index in [3, 4, 5]
    assert "12.5%" in chunks[1].text and "(45)" in chunks[2].text


def test_nested_tables_have_separate_rows_parent_links_and_uncertainty():
    filing = parse('''<table id="outer"><tr><th>Layout</th><th>Contents</th></tr>
    <tr><td>Nested</td><td><table id="inner"><tr><th>Year</th><th>2026</th></tr>
    <tr><td>Revenue</td><td>100</td></tr></table></td></tr></table>''')
    outer, inner = filing.tables
    assert len(outer.row_indices) == 1
    assert inner.rows == [["Revenue", "100"]]
    assert inner.parent_table_id == outer.table_id
    assert outer.extraction_status == "PARTIAL_EXTRACTION"
    assert "NESTED_TABLE_PRESERVED_SEPARATELY" in outer.extraction_warnings


def test_explicit_footnote_references_and_following_note_keep_source_locations():
    filing = parse('''<h2>Statements of Operations</h2><table>
    <tr><th>Metric</th><th>2026</th></tr>
    <tr><td>Revenue <a href="#fn1">(1)</a></td><td>100</td></tr></table>
    <p id="fn1">(1) Revenue excludes discontinued operations.</p>''')
    table = filing.tables[0]
    assert table.footnotes == ["(1) Revenue excludes discontinued operations."]
    assert table.footnote_locations[0].html_anchor == "fn1"
    chunk = next(item for item in chunk_filing(filing) if item.kind == "table")
    assert "excludes discontinued operations" in chunk.text


def test_only_explicit_same_title_continuation_inherits_headers_and_unit_context():
    filing = parse('''<h2>Statements of Cash Flows</h2><p>(In millions)</p>
    <table><tr><th>Metric</th><th>2026</th></tr><tr><td>Cash in</td><td>100</td></tr></table>
    <h2>Statements of Cash Flows (continued)</h2>
    <table><tr><td>Cash out</td><td>(50)</td></tr></table>
    <h2>Other table</h2><table><tr><td>Unknown</td><td>12</td></tr></table>''')
    first, second, third = filing.tables
    assert second.continuation_of == first.table_id
    assert second.columns == first.columns
    assert second.unit_context == "(In millions)"
    assert third.continuation_of is None
    assert third.reporting_periods == []
    assert third.extraction_status == "PARTIAL_EXTRACTION"


def test_ix_numeric_sign_scale_attributes_are_preserved_in_retrieval_context():
    filing = parse('''<table><tr><th>Metric</th><th>2026</th></tr>
    <tr><td>Loss</td><td><ix:nonFraction name="us-gaap:NetIncomeLoss"
    contextRef="FY2026" unitRef="USD" sign="-" scale="6">45</ix:nonFraction></td></tr></table>''')
    fact = filing.tables[0].cells[-1].numeric_facts[0]
    assert fact["sign"] == "-" and fact["scale"] == "6"
    chunk = next(item for item in chunk_filing(filing) if item.kind == "table")
    assert '"sign": "-"' in chunk.text and '"scale": "6"' in chunk.text


def test_body_th_row_labels_do_not_consume_data_as_headers():
    filing = parse('''<table><tr><th>Metric</th><th>2026</th></tr>
    <tr><th>Revenue</th><td>100</td></tr><tr><th>Profit</th><td>20</td></tr></table>''')
    assert filing.tables[0].rows == [["Revenue", "100"], ["Profit", "20"]]


def test_plain_td_column_labels_and_explicit_row_periods_do_not_bleed_between_rows():
    filing = parse('''<h2>Note 8 - Share-Based Compensation</h2>
    <p>RSU activity for the nine months ended June 27, 2026 is as follows:</p>
    <table><tr><td></td><td>Number of RSUs (in thousands)</td><td>Fair Value Per RSU</td></tr>
    <tr><td>Balance as of September 27, 2025</td><td>151,574</td><td>189.75</td></tr>
    <tr><td>RSUs granted</td><td>72,400</td><td>258.16</td></tr></table>''')
    table = filing.tables[0]
    assert table.columns[1:] == ["Number of RSUs (in thousands)", "Fair Value Per RSU"]
    assert table.reporting_periods == ["nine months ended June 27, 2026"]
    assert table.row_context[1] == "Balance as of September 27, 2025"
    assert 2 not in table.row_context


def test_row_axis_periods_and_units_are_preserved_without_invented_column_titles():
    filing = parse('''<h2>Note 9 - Commitments</h2><p>Future payments (in millions):</p>
    <table><tr><td>2026 (remaining three months)</td><td><ix:nonFraction
    name="us-gaap:Commitments" unitRef="USD" scale="6">2,053</ix:nonFraction></td></tr>
    <tr><td>2027</td><td><ix:nonFraction unitRef="USD">7,652</ix:nonFraction></td></tr>
    <tr><td>Thereafter</td><td>615</td></tr></table>''')
    table = filing.tables[0]
    assert not any(table.columns)
    assert table.row_context == {0: "2026 (remaining three months)", 1: "2027", 2: "Thereafter"}
    assert "millions" in table.units
    chunks = [chunk for chunk in chunk_filing(filing) if chunk.kind == "table"]
    assert "Row period/group: Thereafter" in chunks[-1].text


def test_header_only_and_empty_layout_rows_do_not_create_phantom_evidence():
    filing = parse('''<table><tr><th>Metric</th><th>2026</th></tr></table>
    <table><tr><td></td><td></td></tr><tr><td></td><td></td></tr></table>''')
    assert not [chunk for chunk in chunk_filing(filing) if chunk.kind == "table"]


def test_adjacent_tables_share_only_context_that_explicitly_names_the_second_topic():
    filing = parse('''<div><span style="font-weight:700">Gross Margin</span></div>
    <p>Gross margin and gross margin percentage were as follows (dollars in millions):</p>
    <table><tr><th>Metric</th><th>2026</th><th>2025</th></tr>
    <tr><td>Gross margin</td><td>100</td><td>90</td></tr></table>
    <table><tr><td>Gross margin percentage:</td><td></td><td></td></tr>
    <tr><td>Products</td><td>40.1<span>%</span></td><td>34.5<span>%</span></td></tr></table>''')
    first, second = filing.tables
    assert second.statement_title == "Gross Margin"
    assert second.continuation_of == first.table_id
    assert second.reporting_periods == ["2025", "2026"]
    assert second.unit_context == "%" and "%" in second.units
    assert "EXPLICIT_SHARED_INTRODUCTION" in second.extraction_warnings


def test_unrelated_adjacent_table_does_not_inherit_previous_periods():
    filing = parse('''<p>Revenue was as follows:</p><table>
    <tr><th>Metric</th><th>2026</th></tr><tr><td>Revenue</td><td>100</td></tr></table>
    <table><tr><td>Unrelated cash flow</td><td>20</td></tr></table>''')
    assert filing.tables[1].continuation_of is None
    assert filing.tables[1].reporting_periods == []
