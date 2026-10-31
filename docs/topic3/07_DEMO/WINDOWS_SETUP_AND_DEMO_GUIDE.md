# Windows setup and reproducible demonstration

From the repository root, use the existing `.venv`, install `requirements.txt` if missing, run `cd frontend; npm ci; npm run build; cd ..`, then start the isolated demo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Mode Prebuilt -Workspace .\tmp\topic3\demo-workspace -ApiPort 18110
```

Open `http://127.0.0.1:18110/app/`. Read the local access key from `tmp/studio-runtime/access-token.txt` on this machine and enter it in the local login page; never copy it into slides, chat, Git or screenshots. The launcher checks the pinned Nomic digest, Ollama, OCR, dependencies, port ownership and API readiness. The existing SEC roots are used only when configured; the launcher does not fetch or replace models or owner data. Port 18110 avoids the owner's normal 8110 session.

This run used the two locally available source PDFs named in `../06_PRODUCT_QA/PRODUCT_END_TO_END_QA.md`; they are public financial documents, and the isolated workspace stores its own copies. In Search, select `PDF tải lên`, the named document, then run one question. In Compare, run the same question/scope across BM25, Dense and Hybrid. The source viewer shows PDF page and OCR text overlay. In Analysis, choose SEC for the HD verified-cell example and the 2037 refusal; choose PDF for excerpt retrieval. Do not describe an OCR search hit as a verified numeric answer.

To reproduce the author-method research run, use the pinned author clone and isolated environment described in `../01_REPRODUCTION/REPRODUCTION_COMMANDS.md`. Models were cached locally; never rerun SPLADE document embedding concurrently with OCR on low RAM. The measured source-structure ablations are regenerated from the preserved query vectors by `python -m scripts.topic3_structure_bm25 --variant <full|row_only|no_issuer|no_period>` with a fresh local index directory, and the plot by `python -m scripts.topic3_experiment_summary`.

Stop only this managed service with `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_financial_studio.ps1 -Stop`. The script matches PID and creation time, so it does not stop unrelated Python, Node or Ollama processes. The isolated workspace and evidence remain for restart or rollback.
