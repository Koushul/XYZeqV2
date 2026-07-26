"""Merge GEX + ADT AnnData without OCM demultiplexing."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import scanpy as sc
from scipy import sparse

from .config import SimpleleafConfig
from .io import load_counts, rename_adt_vars, rename_gex_vars, strip_gem


def merge_gex_adt(
    *,
    gex_h5ad: Path | None = None,
    adt_h5ad: Path | None = None,
    gex_alevin: Path | None = None,
    adt_alevin: Path | None = None,
    feature_ref: Path | None = None,
    min_gex_umi: int = 100,
    sample: str = "sample",
    out_h5ad: Path,
) -> dict:
    gex = load_counts(gex_h5ad, gex_alevin, "gex")
    if "barcodes" in gex.obs.columns:
        gex.obs_names = gex.obs["barcodes"].astype(str).map(strip_gem).values
    else:
        gex.obs_names = gex.obs_names.astype(str).map(strip_gem)
    gex.obs_names_make_unique()
    rename_gex_vars(gex)

    adt = None
    if adt_h5ad is not None or adt_alevin is not None:
        adt = load_counts(adt_h5ad, adt_alevin, "adt")
        if "barcodes" in adt.obs.columns:
            adt.obs_names = adt.obs["barcodes"].astype(str).map(strip_gem).values
        else:
            adt.obs_names = adt.obs_names.astype(str).map(strip_gem)
        adt.obs_names_make_unique()
        rename_adt_vars(adt, feature_ref)

    gex_counts = np.asarray(gex.X.sum(1)).ravel()
    gex_c = gex[gex_counts >= min_gex_umi].copy()

    if adt is not None:
        n_adt = adt.n_vars
        adt_mat = sparse.lil_matrix((gex_c.n_obs, n_adt), dtype=np.float32)
        common = gex_c.obs_names.intersection(adt.obs_names)
        if len(common):
            adt_c = adt[common]
            X = adt_c.X.tocsr() if sparse.issparse(adt_c.X) else sparse.csr_matrix(adt_c.X)
            import pandas as pd

            rows = pd.Index(gex_c.obs_names).get_indexer(common)
            adt_mat[rows] = X
        adt_mat = adt_mat.tocsr()
        gex_c.obsm["ADT"] = adt_mat
        gex_c.obs["adt_counts"] = np.asarray(adt_mat.sum(1)).ravel()
        gex_c.obs["has_adt"] = (gex_c.obs["adt_counts"] > 0).astype(int)
        gex_c.uns["ADT_var"] = {
            "feature_id": adt.var["feature_id"].tolist()
            if "feature_id" in adt.var.columns
            else adt.var_names.astype(str).tolist(),
            "feature_name": adt.var["feature_name"].tolist()
            if "feature_name" in adt.var.columns
            else adt.var_names.astype(str).tolist(),
        }
        n_adt_out = n_adt
        n_has_adt = int(gex_c.obs["has_adt"].sum())
    else:
        n_adt_out = 0
        n_has_adt = 0

    gex_c.obs["gex_counts"] = np.asarray(gex_c.X.sum(1)).ravel()
    gex_c.var["feature_types"] = "Gene Expression"
    gex_c.uns.update(
        {
            "sample": sample,
            "cell_filter": f"GEX UMI>={min_gex_umi}; ADT left-join",
        }
    )

    out_h5ad = Path(out_h5ad)
    out_h5ad.parent.mkdir(parents=True, exist_ok=True)
    gex_c.write_h5ad(out_h5ad, compression="gzip")

    summary = {
        "sample": sample,
        "n_obs": int(gex_c.n_obs),
        "n_vars": int(gex_c.n_vars),
        "n_adt": int(n_adt_out),
        "n_has_adt": n_has_adt,
        "median_gex_umi": float(np.median(gex_c.obs.gex_counts)),
        "median_adt_umi": float(np.median(gex_c.obs.adt_counts)) if "adt_counts" in gex_c.obs else 0.0,
        "output": str(out_h5ad),
    }
    (out_h5ad.parent / "merge_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def merge_from_config(cfg: SimpleleafConfig, out_h5ad: Path | None = None) -> dict:
    out = out_h5ad or (cfg.outdir / f"{cfg.sample}_gex_adt.h5ad")
    return merge_gex_adt(
        gex_h5ad=cfg.gex_h5ad,
        adt_h5ad=cfg.adt_h5ad,
        gex_alevin=cfg.gex_alevin,
        adt_alevin=cfg.adt_alevin,
        feature_ref=cfg.feature_ref,
        min_gex_umi=cfg.min_gex_umi_merge,
        sample=cfg.sample,
        out_h5ad=out,
    )
