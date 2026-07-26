"""Compare simpleleaf OCM demux barcodes to Cell Ranger multi per_sample_outs."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .io import load_barcode_set


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def compare(
    simpleaf_ocm_outdir: Path,
    cellranger_per_sample_outs: Path,
    out_json: Path,
    sample_ids: list[str] | None = None,
) -> dict:
    simpleaf_ocm_outdir = Path(simpleaf_ocm_outdir)
    cellranger_per_sample_outs = Path(cellranger_per_sample_outs)

    if sample_ids is None:
        sample_ids = sorted(
            p.name for p in (simpleaf_ocm_outdir / "per_sample_outs").iterdir() if p.is_dir()
        )

    rows = []
    for s in sample_ids:
        sf_raw = (
            simpleaf_ocm_outdir
            / "per_sample_outs"
            / s
            / "sample_raw_feature_bc_matrix"
            / "barcodes.tsv.gz"
        )
        sf_filt = (
            simpleaf_ocm_outdir
            / "per_sample_outs"
            / s
            / "sample_filtered_feature_bc_matrix"
            / "barcodes.tsv.gz"
        )
        sf_match = (
            simpleaf_ocm_outdir
            / "per_sample_outs"
            / s
            / "sample_filtered_feature_bc_matrix_cr_match"
            / "barcodes.tsv.gz"
        )
        cr_raw = (
            cellranger_per_sample_outs / s / "sample_raw_feature_bc_matrix" / "barcodes.tsv.gz"
        )
        cr_filt = (
            cellranger_per_sample_outs
            / s
            / "sample_filtered_feature_bc_matrix"
            / "barcodes.tsv.gz"
        )

        A_raw, B_raw = load_barcode_set(sf_raw), load_barcode_set(cr_raw)
        A_filt, B_filt = load_barcode_set(sf_filt), load_barcode_set(cr_filt)
        row = {
            "sample_id": s,
            "sf_raw": len(A_raw),
            "cr_raw": len(B_raw),
            "raw_intersection": len(A_raw & B_raw),
            "raw_only_sf": len(A_raw - B_raw),
            "raw_only_cr": len(B_raw - A_raw),
            "raw_jaccard": jaccard(A_raw, B_raw),
            "sf_filtered": len(A_filt),
            "cr_filtered": len(B_filt),
            "filt_intersection": len(A_filt & B_filt),
            "filt_recall_of_cr": len(A_filt & B_filt) / len(B_filt) if B_filt else 0.0,
            "filt_precision": len(A_filt & B_filt) / len(A_filt) if A_filt else 0.0,
            "filt_jaccard": jaccard(A_filt, B_filt),
            "cr_filt_in_sf_raw": len(B_filt & A_raw) / len(B_filt) if B_filt else 0.0,
        }
        if sf_match.exists():
            M = load_barcode_set(sf_match)
            row["cr_match_n"] = len(M)
            row["cr_match_exact"] = M == B_filt
        rows.append(row)

    df = pd.DataFrame(rows)
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "samples": rows,
        "all_cr_filtered_recovered_in_sf_raw": all(r["cr_filt_in_sf_raw"] == 1.0 for r in rows),
    }
    out_json.write_text(json.dumps(payload, indent=2) + "\n")
    print(df.to_string(index=False))
    print(f"\nWrote {out_json}")
    print("all_cr_filtered_recovered_in_sf_raw:", payload["all_cr_filtered_recovered_in_sf_raw"])
    return payload
