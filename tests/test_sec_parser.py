from hashlib import sha256
from pathlib import Path

from app.financial_ingestion import INGESTION_VERSION, PARSER_VERSION
from app.financial_ingestion.chunker import chunk_filing
from app.financial_ingestion.html_parser import normalized_filing_text, parse_sec_html
from app.financial_ingestion.schemas import FilingMetadata

FIXTURE = Path(__file__).parent / "fixtures" / "sec" / "filing_sample.htm"


def metadata(form_type="10-K", accession="0000123456-24-000001"):
    return FilingMetadata(
        filing_id=f"sec:0000123456:{accession}",
        company_name="Example Financial Corporation", cik="0000123456",
        ticker="EXM", form_type=form_type, accession_number=accession,
        filing_date="2024-03-01", report_date="2023-12-31",
        primary_document="example-20231231x10k.htm",
        source_url=("https://www.sec.gov/Archives/edgar/data/123456/"
                    "000012345624000001/example-20231231x10k.htm"),
        parser_version=PARSER_VERSION, ingestion_version=INGESTION_VERSION,
        raw_content_hash=sha256(FIXTURE.read_bytes()).hexdigest(),
        unknown_reasons={"fiscal_year": "pending", "fiscal_period": "pending"},
    )


def test_html_parser_preserves_sections_tables_units_periods_and_values():
    filing = parse_sec_html(FIXTURE.read_bytes(), metadata())
    assert filing.metadata.fiscal_year == 2023
    assert filing.metadata.fiscal_period == "FY"
    assert len(filing.tables) == 1
    table = filing.tables[0]
    assert table.columns == ["Year ended December 31", "2023", "2022"]
    assert ["Revenue", "1,250", "1,100"] in table.rows
    assert ["Net income (loss)", "(45)", "80"] in table.rows
    assert ["Operating margin", "12.5%", "11.0%"] in table.rows
    assert "USDm" in table.units and "millions" in table.units
    assert table.reporting_periods == ["2022", "2023"]
    assert table.footnotes == ["Amounts may not sum due to rounding."]
    assert table.source_location.pdf_page is None
    assert table.source_location.structural_path.startswith("/document[1]/html[1]")


def test_chunk_ids_are_stable_and_table_rows_keep_relationships():
    first = parse_sec_html(FIXTURE.read_bytes(), metadata())
    first.metadata.normalized_content_hash = sha256(
        normalized_filing_text(first).encode()).hexdigest()
    second = parse_sec_html(FIXTURE.read_bytes(), metadata())
    second.metadata.normalized_content_hash = sha256(
        normalized_filing_text(second).encode()).hexdigest()
    chunks_a = chunk_filing(first)
    chunks_b = chunk_filing(second)
    assert [item.chunk_id for item in chunks_a] == [item.chunk_id for item in chunks_b]
    revenue = next(item for item in chunks_a if item.kind == "table" and "Revenue" in item.text)
    assert "Columns: Year ended December 31 | 2023 | 2022" in revenue.text
    assert "Row 1: Revenue | 1,250 | 1,100" in revenue.text
    assert revenue.source_location.table_id
    assert revenue.source_location.row_index == 1
    assert revenue.metadata["accession_number"] == "0000123456-24-000001"


def test_chunk_ids_change_for_a_new_raw_document_version():
    first = parse_sec_html(FIXTURE.read_bytes(), metadata())
    first.metadata.raw_content_hash = "a" * 64
    second = parse_sec_html(FIXTURE.read_bytes(), metadata())
    second.metadata.raw_content_hash = "b" * 64
    first_ids = {item.chunk_id for item in chunk_filing(first)}
    second_ids = {item.chunk_id for item in chunk_filing(second)}
    assert first_ids.isdisjoint(second_ids)
