# Windows demo guide

From PowerShell in the repository root, after the documented Python, Node, Ollama, Qdrant and Tesseract setup in `docs/topic3/07_DEMO/WINDOWS_SETUP_AND_DEMO_GUIDE.md`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Mode Prebuilt -Workspace .\tmp\topic3\demo-workspace -ApiPort 18110
```

Open `http://127.0.0.1:18110/app/`. The launcher prints the path of the private local access token; enter its contents in the login screen without putting it on slides, in screenshots or in a repository. The isolated demo workspace contains the already indexed Hòa Phát and BIDV PDFs on the owner machine only. Its path is not a committed distributable corpus. If using a fresh checkout, create a new workspace and upload authorized local PDFs; wait for READY before searching. READY indicates extraction/indexing, not verified table cells.

Before class: confirm at least 2 PDF READY, OCR `vie+eng`, SEC READY, Ollama online, and enough free RAM/disk. The historical Research Lab can be shown without loading a SPLADE document embedder. On low-memory laptops, avoid simultaneous fresh OCR, model download and research indexing. If Ollama/Qdrant is unavailable, use the source-first capabilities that still respond and state the missing dependency; do not present an unavailable method as live.

Demo order: BIDV source-backed narrative → open page 1 → Hòa Phát unit page → verified Home Depot SEC cell → BIDV 2037 refusal → live BM25/Dense/Hybrid → clearly marked saved Topic 3 experiment. Stop only the launcher-owned processes with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Stop
```

Troubleshooting: a port conflict requires a new unused `-ApiPort`; an empty document list means the wrong `-Workspace`; missing OCR needs Tesseract `vie+eng`; incomplete index requires waiting for READY. Preserve existing workspaces, model files and research indices.
