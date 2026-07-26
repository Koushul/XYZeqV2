"""Demultiplex pooled simpleaf GEX+ADT quants by OCM overhang."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import scanpy as sc

from .config import OcmSample, SimpleleafConfig
from .io import (
    attach_adt,
    load_barcode_set,
    load_counts,
    rename_adt_vars,
    rename_gex_vars,
    strip_gem,
    write_mtx,
)
from .ocm import ocm_id_for_barcode, sample_map_tsv


def demux(
    *,
    outdir: Path,
    sample: str,
    gex_h5ad: Path | None = None,
    adt_h5ad: Path | None = None,
    gex_alevin: Path | None = None,
    adt_alevin: Path | None = None,
    feature_ref: Path | None = None,
    min_gex_umi: int = 500,
    ocm_samples: list[OcmSample] | None = None,
    overhang_start: int = 7,
    overhang_len: int = 2,
    cellranger_per_sample_outs: Path | None = None,
) -> dict:
    from .config import DEFAULT_OCM_MAP, _load_sample_map

    if ocm_samples is None:
        ocm_samples = _load_sample_map(DEFAULT_OCM_MAP, None)

    overhang_to_ocm = {s.overhang: s.ocm_id for s in ocm_samples}

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "whitelists").mkdir(parents=True, exist_ok=True)
    (outdir / "whitelists" / "ocm_sample_map.tsv").write_text(sample_map_tsv(ocm_samples))

    gex = load_counts(gex_h5ad, gex_alevin, "gex")
    if "barcodes" in gex.obs.columns:
        gex.obs_names = gex.obs["barcodes"].astype(str).map(strip_gem).values
    else:
        gex.obs_names = pd.Index(gex.obs_names.astype(str).map(strip_gem))
    gex.obs_names_make_unique()
    rename_gex_vars(gex)
    gex.obs["gex_counts"] = np.asarray(gex.X.sum(1)).ravel()
    gex.obs["ocm_barcode_id"] = [
        ocm_id_for_barcode(b, overhang_to_ocm, overhang_start, overhang_len)
        for b in gex.obs_names.astype(str)
    ]
    gex.var["feature_types"] = "Gene Expression"

    adt = None
    if adt_h5ad is not None or adt_alevin is not None:
        try:
            adt = load_counts(adt_h5ad, adt_alevin, "adt")
        except FileNotFoundError:
            adt = None
    if adt is not None:
        if "barcodes" in adt.obs.columns:
            adt.obs_names = adt.obs["barcodes"].astype(str).map(strip_gem).values
        else:
            adt.obs_names = pd.Index(adt.obs_names.astype(str).map(strip_gem))
        adt.obs_names_make_unique()
        rename_adt_vars(adt, feature_ref)
        adt.obs["ocm_barcode_id"] = [
            ocm_id_for_barcode(b, overhang_to_ocm, overhang_start, overhang_len)
            for b in adt.obs_names.astype(str)
        ]

    summary: dict = {"sample": sample, "min_gex_umi": min_gex_umi, "samples": {}}

    for s in ocm_samples:
        ob = s.ocm_id
        sample_id, desc = s.sample_id, s.description or s.sample_id
        sample_dir = outdir / "per_sample_outs" / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)

        gex_s = gex[gex.obs["ocm_barcode_id"].values == ob].copy()
        adt_s = adt[adt.obs["ocm_barcode_id"].values == ob].copy() if adt is not None else None

        raw_bc_dir = sample_dir / "sample_raw_feature_bc_matrix"
        raw_bc_dir.mkdir(parents=True, exist_ok=True)
        import gzip

        with gzip.open(raw_bc_dir / "barcodes.tsv.gz", "wt") as fh:
            for bc in gex_s.obs_names.astype(str):
                fh.write(f"{strip_gem(bc)}-1\n")
        gex_s.write_h5ad(sample_dir / "sample_raw_gex.h5ad", compression="gzip")
        if adt_s is not None:
            adt_s.write_h5ad(sample_dir / "sample_raw_adt.h5ad", compression="gzip")

        indep = gex_s[gex_s.obs["gex_counts"].values >= min_gex_umi].copy()
        indep = attach_adt(indep, adt_s)
        indep.obs["sample_id"] = sample_id
        indep.obs["ocm_barcode_id"] = ob
        indep.obs["description"] = desc
        indep.uns.update(
            {
                "sample": sample,
                "sample_id": sample_id,
                "ocm_barcode_id": ob,
                "filter": f"OCM {ob}; GEX UMI>={min_gex_umi}; ADT left-join",
            }
        )
        write_mtx(sample_dir / "sample_filtered_feature_bc_matrix", indep)
        indep.write_h5ad(sample_dir / "sample_filtered_gex_adt.h5ad", compression="gzip")

        cr_n = None
        cr_inter = None
        if cellranger_per_sample_outs is not None:
            cr_bc_path = (
                Path(cellranger_per_sample_outs)
                / sample_id
                / "sample_filtered_feature_bc_matrix"
                / "barcodes.tsv.gz"
            )
            cr_bcs = load_barcode_set(cr_bc_path)
            cr_n = len(cr_bcs)
            present = [b for b in gex_s.obs_names.astype(str) if b in cr_bcs]
            cr_inter = len(present)
            matched = gex_s[present].copy()
            matched = attach_adt(matched, adt_s)
            matched.obs["sample_id"] = sample_id
            matched.obs["ocm_barcode_id"] = ob
            matched.obs["description"] = desc
            matched.uns.update(
                {
                    "sample": sample,
                    "sample_id": sample_id,
                    "ocm_barcode_id": ob,
                    "filter": f"OCM {ob}; exact Cell Ranger filtered barcodes",
                }
            )
            write_mtx(sample_dir / "sample_filtered_feature_bc_matrix_cr_match", matched)
            matched.write_h5ad(sample_dir / "sample_filtered_gex_adt_cr_match.h5ad", compression="gzip")

        summary["samples"][sample_id] = {
            "ocm_barcode_id": ob,
            "description": desc,
            "n_raw": int(gex_s.n_obs),
            "n_filtered_independent": int(indep.n_obs),
            "n_has_adt": int(indep.obs["has_adt"].sum()) if "has_adt" in indep.obs else 0,
            "n_cellranger_filtered": cr_n,
            "n_cr_barcodes_in_simpleaf": cr_inter,
        }
        print(
            f"{sample_id} ({ob}): raw={gex_s.n_obs} "
            f"filt_umi>={min_gex_umi}={indep.n_obs} "
            f"cr_match={cr_inter}/{cr_n}"
        )

    parts = [
        sc.read_h5ad(outdir / "per_sample_outs" / s.sample_id / "sample_filtered_gex_adt.h5ad")
        for s in ocm_samples
    ]
    combined = sc.concat(parts, join="outer", merge="same")
    combined.obs_names_make_unique()
    combined.uns["sample"] = sample
    combined.uns["ocm"] = f"overhang_pos_{overhang_start}_{overhang_start + overhang_len - 1}"
    combined.write_h5ad(outdir / f"{sample}_gex_adt_ocm.h5ad", compression="gzip")

    if cellranger_per_sample_outs is not None:
        parts = [
            sc.read_h5ad(
                outdir / "per_sample_outs" / s.sample_id / "sample_filtered_gex_adt_cr_match.h5ad"
            )
            for s in ocm_samples
        ]
        matched = sc.concat(parts, join="outer", merge="same")
        matched.obs_names_make_unique()
        matched.uns["sample"] = sample
        matched.uns["filter"] = "exact Cell Ranger filtered barcodes + simpleaf counts"
        matched.write_h5ad(outdir / f"{sample}_gex_adt_ocm_cr_match.h5ad", compression="gzip")

    (outdir / "demux_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def demux_from_config(cfg: SimpleleafConfig, outdir: Path | None = None) -> dict:
    return demux(
        outdir=outdir or (cfg.outdir / "ocm"),
        sample=cfg.sample,
        gex_h5ad=cfg.gex_h5ad,
        adt_h5ad=cfg.adt_h5ad,
        gex_alevin=cfg.gex_alevin,
        adt_alevin=cfg.adt_alevin,
        feature_ref=cfg.feature_ref,
        min_gex_umi=cfg.ocm_min_gex_umi,
        ocm_samples=cfg.ocm_samples,
        overhang_start=cfg.ocm_overhang_start,
        overhang_len=cfg.ocm_overhang_len,
        cellranger_per_sample_outs=cfg.cellranger_per_sample_outs,
    )
