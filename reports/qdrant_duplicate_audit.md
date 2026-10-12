# Qdrant duplicate and document identity audit

## Production snapshot

- Collection: `knowledgebase`, 1,947 vectors, dimension 768, cosine distance.
- No production points or document metadata were changed.
- Point IDs were read with a filtered Qdrant scroll; the full IDs are retained in `qdrant_duplicate_audit_data.json`.

| document_id | file | SHA-256 bytes | pages | chunks/points | normalized chunk-text SHA-256 | indexed UTC | conversations |
|---|---|---|---:|---:|---|---|---:|
| `17be69dfe9e84f9bb2a34fb5d9f89671` | Bài giảng Đổi mới sáng tạo Tài chính 2023 (18.12).pdf | `568b24d8063d5c580cd3c3515b982cddc2adc53085ad58da6dab37a105aa7810` | 249 | 971/971 | `c29d8dae7e789d502e7efa851e9516c29c15cbc99135b274d98dcfe13a4e5be4` | 2026-10-10 03:22:14 | 0 |
| `aedb60bc088e4242970a43da1e897bde` | Bài giảng Đổi mới sáng tạo Tài chính 2023 (18.12).pdf | `568b24d8063d5c580cd3c3515b982cddc2adc53085ad58da6dab37a105aa7810` | 249 | 971/971 | `c29d8dae7e789d502e7efa851e9516c29c15cbc99135b274d98dcfe13a4e5be4` | 2026-10-09 18:02:35 | 0 |
| `b7d5be30d6014424bf81f54011e0cdb1` | CV_Do_Quoc_Dung_TTS_QHKH_LPS.pdf | `badbbe6d2798dc26062cd0277f3f2f52dc7a3b024fcfce134af517aaf21840f4` | 1 | 5/5 | `90733d9e24a04dea37c464b7b5faf770a622840174d7790e78e92a2b64ad29fa` | 2026-10-10 03:51:56 | 0 |

## Classification

The two 971-point lecture records are **A: identical PDF bytes**. Their byte hash and extracted-text fingerprint both match. Equal chunk counts were not used as proof. The CV is a distinct document.

Current upload behavior derives identity from a streaming SHA-256 and document ID from its first 32 hex characters:

- Same file: reuse the existing document and index.
- Same bytes under a different filename: reuse the existing document and index.
- Same rendered/text content with changed PDF metadata: byte hash changes, so it becomes a separate byte-level version. The text fingerprint can identify it as a content-equivalent candidate in a future review flow.
- Revised content: byte hash and normally text fingerprint change, so a new version is retained.

An isolated real upload repeated the same scanned PDF: `duplicate=true`, document ID unchanged, vector count 36 → 36. This confirms current prevention for exact-byte duplicates.

## Dry-run action

Candidate duplicate group: keep either lecture record as canonical and map the other as an alias/version. Estimated removable duplicate points: 971. The dry run proposes no automatic deletion because old citations or external clients may hold either document ID. There are currently no SQLite conversations referencing these IDs, but absence of local conversation rows does not prove absence of external references.

Before any cleanup, export the duplicate point IDs, add an alias table, rewrite citation/document references transactionally, test document-scope isolation, and obtain explicit approval for deletion.
