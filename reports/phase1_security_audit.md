# Phase 1 security and data-integrity audit

Tested commit: `fe0462bbd777740138dd50488572dde2950d090a`

## Implemented controls

- Uploads require a PDF signature, reject empty files, enforce `MAX_UPLOAD_MB`, check reserve disk space, and remove failed temporary uploads after the file handle closes.
- Uploaded filenames are reduced to a safe basename and storage names are content-hash keyed.
- Corrupt and password-protected PDFs fail with explicit states; interrupted jobs become retryable `INTERRUPTED` records.
- CORS defaults to `http://127.0.0.1:8501` and `http://localhost:8501`; methods and headers are bounded.
- API and Streamlit were restarted bound to loopback only.
- RAG prompts state that instructions embedded in document content are data. The real prompt-injection resilience case returned the supported revenue value and did not follow the injected command.
- `.env`, production Qdrant, uploads, processed data and SQLite files are ignored. A tracked-file scan found no `.env`, PEM or key files and no obvious assigned API credential outside excluded reports/tests/docs.
- `pip check` found no broken package requirements.

## Deployment assumptions and open risks

- APIs are unauthenticated. Loopback use is the supported Phase 1 deployment; public or LAN exposure requires authentication and authorization first.
- Eighteen Tiny-SD files, including model weights, are historically tracked under `models/tiny-sd`. They were preserved to avoid breaking the existing image module. This conflicts with the desired policy of keeping model assets out of GitHub and requires a separately approved history/LFS migration.
- Free disk after all holdout runs was 4.51 GB, below a comfortable ingestion margin. The 256 MB reserve guard prevents a full disk but does not provide long-term capacity management.
- Intentional disk exhaustion and RAM exhaustion were not performed. Those resilience rows remain `BLOCKED` for safe simulation.

## Commands

```powershell
git ls-files | Select-String -Pattern '(^|/)(\.env|.*\.pem|.*\.key)$'
git grep -n -I -E '(api[_-]?key|secret|password)\s*=\s*[^\s$<{]+'
.\.venv\Scripts\python.exe -m pip check
```

