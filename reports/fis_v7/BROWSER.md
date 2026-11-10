# Browser and API acceptance

Product code commit `2ef7e694f9d0061da8f338064c8ccd1a2c70de85`.

- The [browser log](browser.json) records the nine BIDV questions, the eight comparative and protection prompts, restored multi-PDF selection, the two HPG V6 workflows, the historical capital cell and HPG-only selection after reload.
- Chromium opened the BIDV adjusted retained earnings cell on PDF p. 4 and the HPG capital cell on p. 20. The rendered highlight boxes were approximately 24.3 × 9.7 and 71.3 × 7.7 CSS pixels respectively. The PDF source re-read matched 57/57 native citation rectangle observations including repetitions across runs and selected scopes.
- The [regression browser log](browser-controls.json) covers Apple Services revenue with a p. 32 highlight, the prior BIDV 1,114 million VND case, the Apple–BIDV evidence flow, PG filings from separate index generations and the mobile source picker.
- The [API probes](api-probes.json) cover four reworded BIDV prompts, Search B09, the existing HPG liability review and the OCR reread discrepancy. The HPG review returns the previously reviewed value. The reread returns an OCR candidate with separate raw and reread provenance.
- The [resource profile](RESOURCE_PROFILE.json) records wall-clock and sampled working-set measurements. The test ran on a host with 8 CPU threads and approximately 7.84 GiB physical RAM.
- Screenshots are in [screenshots](screenshots). The 125% capture uses Chromium CDP page scaling. The original user-reported failure is preserved as reply text in the baseline logs.

Both Python and frontend jobs passed on the exact product code commit in [GitHub Actions run 42193050752](https://github.com/Doquocdung1609/tinyllama-fastapi/actions/runs/42193050752).

See [independent evaluation](INDEPENDENT_EVALUATION.md) for the release gate that remains open.
