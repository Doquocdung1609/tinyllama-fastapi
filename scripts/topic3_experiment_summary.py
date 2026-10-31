"""Rebuild the exposed experiment table and plot from preserved JSON outputs."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/topic3/03_IMPROVEMENTS"
OUT = ROOT / "docs/topic3/04_ABLATION"
VARIANTS = [
    ("Full structure", "STRUCTURE_BM25_RESULTS.json"),
    ("Row only", "STRUCTURE_BM25_ROW_ONLY_RESULTS.json"),
    ("Without issuer", "STRUCTURE_BM25_NO_ISSUER_RESULTS.json"),
    ("Without period", "STRUCTURE_BM25_NO_PERIOD_RESULTS.json"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, name in VARIANTS:
        data = json.loads((BASE / name).read_text(encoding="utf-8"))
        rows.append({"variant": label, "file": name, "index_points": data["index_points"], **data["summary"]})
    (OUT / "MEASURED_SUMMARY.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("MATPLOTLIB_UNAVAILABLE: summary JSON saved; plot skipped")
        return
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    labels = [r["variant"] for r in rows]
    values = [r["known_target_at_1"] for r in rows]
    bars = ax.bar(labels, values, color=["#176cff", "#a9b9d0", "#6c8dbc", "#9ab0cf"])
    ax.bar_label(bars, labels=[f"{v}/4" for v in values], padding=3)
    ax.set_ylim(0, 4.5)
    ax.set_ylabel("Known source target at rank 1 (of 4 exposed questions)")
    ax.set_title("Structure-aware BM25 ablation — provisional development set")
    ax.grid(axis="y", alpha=0.2)
    fig.text(0.02, 0.01, "Two SEC filings; machine-prepared targets; not independent gold or numeric accuracy.", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "structure_bm25_ablation.png", dpi=150)
    plt.close(fig)
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
