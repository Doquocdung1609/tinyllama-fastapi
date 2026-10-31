# Artifact integrity

`RELEASE_ARTIFACT_MANIFEST.json` records SHA-256 and byte size of committed Topic 3 research reports, raw SEC snapshots, derived source chunks, per-query results, chart and browser screenshots. It excludes itself and local private models, tokens, owner PDF workspaces and Qdrant files. Generate from the repository root with `python -m scripts.topic3_release_manifest`. A changed input will change its listed hash; this manifest records one checked state of the branch and does not certify human review.
