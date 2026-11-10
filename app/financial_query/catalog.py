"""Pure metadata adapter. Caller supplies already verified SEC snapshot objects.

Does not open FinancialRegistry (whose constructor writes SQLite), files, network,
or any index. Raw table labels are not promoted to typed column-period evidence.
"""
from app.financial_ingestion.schemas import DatasetManifest, StructuredFiling
from app.financial_query.contracts import CatalogFilingV1, CorpusCatalogV1, IssuerV1


def catalog_from_verified_metadata(manifest: DatasetManifest, filings: list[StructuredFiling],
                                   generation_id: str | None = None, *,
                                   filing_model=CatalogFilingV1, catalog_model=CorpusCatalogV1,
                                   omit_overlong_labels: bool = False) -> CorpusCatalogV1:
    if manifest.manifest_hash != manifest.content_hash():
        raise ValueError("MANIFEST_HASH_MISMATCH")
    if len(filings) != len(manifest.filing_ids) or {f.metadata.filing_id for f in filings} != set(manifest.filing_ids):
        raise ValueError("MANIFEST_MEMBERSHIP_MISMATCH")
    issuers, entries = {}, []
    for item in sorted(filings, key=lambda f: f.metadata.filing_id):
        m = item.metadata
        if m.raw_content_hash is None or manifest.raw_hashes.get(m.filing_id) != m.raw_content_hash:
            raise ValueError("RAW_METADATA_HASH_MISMATCH")
        if manifest.normalized_hashes.get(m.filing_id) != m.normalized_content_hash:
            raise ValueError("NORMALIZED_METADATA_HASH_MISMATCH")
        if (m.parser_version, m.chunker_version) != (manifest.parser_version, manifest.chunker_version):
            raise ValueError("METADATA_VERSION_MISMATCH")
        if m.cik in issuers and issuers[m.cik].company_name != m.company_name:
            raise ValueError("ISSUER_NAME_CONFLICT")
        existing = issuers.get(m.cik)
        tickers = sorted(set((existing.tickers if existing else []) + ([m.ticker] if m.ticker else [])))
        issuers[m.cik] = IssuerV1(cik=m.cik, company_name=m.company_name, tickers=tickers)
        labels = {p for table in item.tables for p in table.reporting_periods}
        if omit_overlong_labels:
            labels = {label for label in labels if len(label)<=4000}
        entries.append(filing_model(filing_id=m.filing_id, cik=m.cik, accession=m.accession_number,
            form=m.form_type, filing_date=m.filing_date, report_end=m.report_date, fiscal_year=m.fiscal_year,
            fiscal_period=m.fiscal_period, amendment_of=m.amendment_of,
            extraction_status='PARTIAL_EXTRACTION' if m.filing_id in manifest.partial_documents else m.document_status.value,
            raw_column_labels=sorted(labels)))
    return catalog_model(dataset_id=manifest.dataset_id, manifest_hash=manifest.manifest_hash,
        generation_id=generation_id, provenance="Caller-verified SEC metadata; no source-byte verification by D1",
        issuers=sorted(issuers.values(), key=lambda i: i.cik), filings=entries)
