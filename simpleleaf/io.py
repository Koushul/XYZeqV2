"""I/O helpers for alevin-fry / AnnData matrices."""
from __future__ import annotations

import gzip
from pathlib import Path

import pandas as pd
import scanpy as sc
from scipy import sparse


def strip_gem(bc: str) -> str:
    return bc.split("-")[0]


def _read_lines(path: Path) -> list[str]:
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def load_alevin_mtx(alevin_dir: Path) -> sc.AnnData:
    import scipy.io

    d = Path(alevin_dir)
    mtx = d / "quants_mat.mtx"
    rows = d / "quants_mat_rows.txt"
    cols = d / "quants_mat_cols.txt"
    if not mtx.exists():
        raise FileNotFoundError(f"missing {mtx}")
    barcodes = _read_lines(rows)
    features = _read_lines(cols)
    X = sparse.csr_matrix(scipy.io.mmread(mtx))
    if X.shape == (len(features), len(barcodes)):
        X = X.T
    elif X.shape != (len(barcodes), len(features)):
        raise ValueError(
            f"unexpected MTX shape {X.shape} for {len(barcodes)} barcodes x {len(features)} features"
        )
    adata = sc.AnnData(X.tocsr())
    adata.obs_names = pd.Index(barcodes)
    adata.var_names = pd.Index(features)
    adata.obs["barcodes"] = barcodes
    return adata


def load_counts(h5ad: Path | None, alevin_dir: Path | None, label: str) -> sc.AnnData:
    if h5ad is not None and Path(h5ad).exists():
        return sc.read_h5ad(h5ad)
    if alevin_dir is not None and Path(alevin_dir).exists():
        h5 = Path(alevin_dir) / "quants.h5ad"
        if h5.exists():
            return sc.read_h5ad(h5)
        return load_alevin_mtx(Path(alevin_dir))
    raise FileNotFoundError(f"No {label} input found (need --{label}-h5ad or --{label}-alevin)")


def rename_gex_vars(adata: sc.AnnData) -> None:
    if "gene_symbol" not in adata.var.columns:
        return
    sym = adata.var["gene_symbol"].astype(str).values
    gid = adata.var["gene_id"].astype(str).values
    names, seen = [], set()
    for s, g in zip(sym, gid):
        n = s if s and s != "nan" and s not in seen else g
        if n in seen:
            n = g
        seen.add(n)
        names.append(n)
    adata.var_names = names


def rename_adt_vars(adata: sc.AnnData, feat_csv: Path | None) -> None:
    if feat_csv is None or not Path(feat_csv).exists():
        return
    feat = pd.read_csv(feat_csv)
    id_to_name = dict(zip(feat["id"].astype(str), feat["name"].astype(str)))
    name_to_id = dict(zip(feat["name"].astype(str), feat["id"].astype(str)))
    ids, names = [], []
    for v in adata.var_names.astype(str):
        if v in name_to_id:
            names.append(v)
            ids.append(name_to_id[v])
        elif v in id_to_name:
            ids.append(v)
            names.append(id_to_name[v])
        else:
            ids.append(v)
            names.append(v)
    adata.var["feature_id"] = ids
    adata.var["feature_name"] = names
    adata.var_names = pd.Index(names)
    adata.var_names_make_unique()


def write_mtx(outdir: Path, adata: sc.AnnData) -> None:
    import scipy.io

    outdir.mkdir(parents=True, exist_ok=True)
    X = adata.X.T.tocsr() if sparse.issparse(adata.X) else sparse.csr_matrix(adata.X).T
    tmp = outdir / "matrix.mtx"
    scipy.io.mmwrite(tmp, X)
    with open(tmp, "rb") as fin, gzip.open(outdir / "matrix.mtx.gz", "wb") as fout:
        fout.writelines(fin)
    tmp.unlink(missing_ok=True)
    with gzip.open(outdir / "barcodes.tsv.gz", "wt") as fh:
        for bc in adata.obs_names.astype(str):
            fh.write(f"{strip_gem(bc)}-1\n")
    with gzip.open(outdir / "features.tsv.gz", "wt") as fh:
        for i, name in enumerate(adata.var_names.astype(str)):
            fid = str(adata.var["gene_id"].iloc[i]) if "gene_id" in adata.var.columns else name
            ftype = (
                str(adata.var["feature_types"].iloc[i])
                if "feature_types" in adata.var.columns
                else "Gene Expression"
            )
            fh.write(f"{fid}\t{name}\t{ftype}\n")


def load_barcode_set(path: Path) -> set[str]:
    opener = gzip.open if str(path).endswith(".gz") else open
    out = set()
    with opener(path, "rt") as fh:
        for line in fh:
            tok = line.strip().split(",")[-1].strip()
            if not tok or tok.lower().startswith("barcode"):
                continue
            out.add(strip_gem(tok))
    return out


def attach_adt(gex: sc.AnnData, adt: sc.AnnData | None) -> sc.AnnData:
    out = gex.copy()
    if adt is None or adt.n_obs == 0:
        out.obs["adt_counts"] = 0.0
        out.obs["has_adt"] = 0
        return out
    n_adt = adt.n_vars
    adt_mat = sparse.lil_matrix((out.n_obs, n_adt), dtype="float32")
    common = out.obs_names.intersection(adt.obs_names)
    if len(common):
        adt_c = adt[common]
        X = adt_c.X.tocsr() if sparse.issparse(adt_c.X) else sparse.csr_matrix(adt_c.X)
        rows = pd.Index(out.obs_names).get_indexer(common)
        adt_mat[rows] = X
    adt_mat = adt_mat.tocsr()
    out.obsm["ADT"] = adt_mat
    out.obs["adt_counts"] = __import__("numpy").asarray(adt_mat.sum(1)).ravel()
    out.obs["has_adt"] = (out.obs["adt_counts"] > 0).astype(int)
    out.uns["ADT_var"] = {
        "feature_id": adt.var["feature_id"].tolist()
        if "feature_id" in adt.var.columns
        else adt.var_names.astype(str).tolist(),
        "feature_name": adt.var["feature_name"].tolist()
        if "feature_name" in adt.var.columns
        else adt.var_names.astype(str).tolist(),
    }
    return out
