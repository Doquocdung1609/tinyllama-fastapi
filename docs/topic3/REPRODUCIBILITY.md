# Milestone C — reproducibility

## Core commands

```powershell
$env:OLLAMA_BASE_URL='http://127.0.0.1:11434'
.\.venv-review\Scripts\python.exe -m scripts.evaluate_persistent_financial `
  --queries docs/topic3/MILESTONE_C_ISSUER_HELDOUT_QUERIES.json `
  --index-root C:\msch\index --split development `
  --output reports/milestone_c_issuer_development.json

# Held-out chỉ để audit/reproduction; không dùng output để tune.
.\.venv-review\Scripts\python.exe -m scripts.evaluate_persistent_financial `
  --queries docs/topic3/MILESTONE_C_ISSUER_HELDOUT_QUERIES.json `
  --index-root C:\msch\index --split held_out `
  --output reports/milestone_c_issuer_heldout.json

.\.venv-review\Scripts\python.exe -m scripts.benchmark_financial_hardening `
  --queries docs/topic3/MILESTONE_C_ISSUER_HELDOUT_QUERIES.json `
  --index-root C:\msch\index --output reports/milestone_c_hardening_latency.json

$env:SCORE_THRESHOLD='0.55'
.\.venv-review\Scripts\python.exe -m pytest -q
```

Runner từ chối chạy nếu query SHA-256 khác `c8aedd…792a`, đồng thời kiểm tra dataset/generation/manifest/embedding identity. Outputs chứa parameters, per-query IDs/ranks/RRF scores, provenance, stage timings và deterministic bootstrap CI seed `20261025`.

## CI boundary

`.github/workflows/core.yml` chạy Python 3.13, compileall và `pytest -m "not integration"` trên Ubuntu, không gọi SEC/Ollama/GPU. Real image, Windows SAPI và ffmpeg là local integration gate riêng; CI không giả lập chúng và không download model.

## Evidence files

- `reports/milestone_c_issuer_development.json`
- `reports/milestone_c_issuer_heldout.json`
- `reports/milestone_c_hardening_latency.json`
- `reports/milestone_c_ollama_endpoint_latency.json`

Không sửa historical `MILESTONE_C_MEASUREMENTS.json`. Corpus paths là local evidence; raw source hashes/manifests trong frozen corpus file mới là reproducibility anchor.
