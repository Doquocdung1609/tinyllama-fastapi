# P11 official SEC acquisition ledger

The source-selection rule and nine issuer partitions were committed at `d04fd4b53c104cbc5208ff33bcf876ae7bcbc03e` **before** the first P11 SEC request. `scripts/p11_acquire_official_sec.py` used the repository SEC client with a private validated contact User-Agent, 1 request/second, zero retries, one recent-submissions lookup and at most one primary filing per issuer. It wrote only into the new owned `t3-p11-new-sec-20261027-v1` research namespace. The contact identity and raw bytes are absent from Git.

Seven of nine fixed filings were acquired, totaling **16,488,585 bytes**. ORCL 10-K and DE 10-K exceeded the preregistered 6 MiB per-file cap; neither was replaced. No HTTP 403/429 occurred. Actual accession, official URL, response metadata, raw SHA256 and size are in `p11_source_registry.json`. All acquired sources are 10-Q except SBUX 10-K. This is a smaller and less form-diverse sample than planned.

| Split | Issuer | Accession | Raw SHA256 prefix | Bytes | Result |
|---|---|---|---|---:|---|
| Dev | ORCL | 0001193125-26-277521 | — | — | Over 6 MiB |
| Dev | MCD | 0000063908-26-000073 | 5a11b7e43689 | 1,522,002 | Acquired |
| Dev | CAT | 0000018230-26-000046 | abefe0510b34 | 4,580,621 | Acquired |
| Validation | SBUX | 0000829224-25-000114 | 38c18be57efc | 3,127,120 | Acquired |
| Validation | UPS | 0001628280-26-053249 | 4da382ec0ce2 | 2,170,773 | Acquired |
| Validation | TXN | 0000097476-26-000169 | 6230433eb888 | 1,249,533 | Acquired |
| Held-out | DE | 0001104659-25-122321 | — | — | Over 6 MiB |
| Held-out | AMGN | 0000318154-26-000126 | cba4ad1d4d8c | 2,509,095 | Acquired, sealed |
| Held-out | BKNG | 0001075531-26-000037 | aef0447d4672 | 1,329,441 | Acquired, sealed |

The accepted parser/chunker processed MCD (876 parents), CAT (2,011), SBUX (1,772), UPS (1,175) and TXN (598) in isolated storage. Each derived artifact records raw, structured and chunk hashes in `p11_parsed_sources.json`. All five reported `PARTIAL_TABLE_EXTRACTION`; those warnings remain attached to evidence. Held-out AMGN/BKNG bytes were hashed for identity but **not parsed, indexed, labeled or scored**. HTTPS delivery plus a pinned local SHA256 is not an SEC cryptographic signature; the trust boundary is documented accordingly.
