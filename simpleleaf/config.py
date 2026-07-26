"""Config loading and validation for simpleleaf pipelines."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .yaml_lite import load as load_yaml


DEFAULT_OCM_MAP = [
    {"overhang": "GT", "ocm_id": "OB1", "sample_id": "edge_gfp_plus", "description": "OB1"},
    {"overhang": "CA", "ocm_id": "OB2", "sample_id": "edge_gfp_minus", "description": "OB2"},
    {"overhang": "TC", "ocm_id": "OB3", "sample_id": "core_gfp_plus", "description": "OB3"},
    {"overhang": "AG", "ocm_id": "OB4", "sample_id": "core_gfp_minus", "description": "OB4"},
]


@dataclass
class OcmSample:
    overhang: str
    ocm_id: str
    sample_id: str
    description: str = ""


@dataclass
class SimpleleafConfig:
    sample: str
    outdir: Path
    gex_index: Path | None = None
    adt_index: Path | None = None
    gex_r1: Path | None = None
    gex_r2: Path | None = None
    adt_r1: Path | None = None
    adt_r2: Path | None = None
    gex_h5ad: Path | None = None
    adt_h5ad: Path | None = None
    gex_alevin: Path | None = None
    adt_alevin: Path | None = None
    feature_ref: Path | None = None
    gex_chemistry: str = "10xv4-3p"
    adt_chemistry: str = "e14s-adt-10xv4"
    threads: int = 16
    min_reads: int = 10
    resolution: str = "cr-like"
    min_gex_umi_merge: int = 100
    ocm_enabled: bool = False
    ocm_min_gex_umi: int = 500
    ocm_overhang_start: int = 7
    ocm_overhang_len: int = 2
    ocm_samples: list[OcmSample] = field(default_factory=list)
    cellranger_per_sample_outs: Path | None = None
    alevin_fry_home: Path | None = None
    conda_bin: Path | None = None
    scratch: Path | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def overhang_to_ocm(self) -> dict[str, str]:
        return {s.overhang: s.ocm_id for s in self.ocm_samples}

    @property
    def ocm_to_sample(self) -> dict[str, tuple[str, str]]:
        return {s.ocm_id: (s.sample_id, s.description or s.sample_id) for s in self.ocm_samples}


def _p(val: Any) -> Path | None:
    if val is None or val == "":
        return None
    return Path(str(val)).expanduser()


def _load_sample_map(raw: Any, path: Path | None) -> list[OcmSample]:
    rows: list[dict[str, Any]]
    if path is not None:
        text = Path(path).read_text().splitlines()
        header = None
        rows = []
        for line in text:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if header is None:
                header = [p.strip().lower() for p in parts]
                continue
            row = dict(zip(header, parts))
            rows.append(row)
    elif isinstance(raw, list) and raw:
        rows = raw
    else:
        rows = DEFAULT_OCM_MAP

    out: list[OcmSample] = []
    for r in rows:
        out.append(
            OcmSample(
                overhang=str(r.get("overhang", "")).upper(),
                ocm_id=str(r.get("ocm_id") or r.get("ocm_barcode_id") or ""),
                sample_id=str(r.get("sample_id") or r.get("sample") or ""),
                description=str(r.get("description") or r.get("sample_id") or ""),
            )
        )
    for s in out:
        if len(s.overhang) != 2 or not s.ocm_id or not s.sample_id:
            raise ValueError(f"Invalid OCM sample map entry: {s}")
    return out


def load_config(path: str | Path) -> SimpleleafConfig:
    path = Path(path)
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")

    paths = data.get("paths") or {}
    indices = data.get("indices") or {}
    fastq = data.get("fastq") or {}
    quant = data.get("quant") or {}
    chem = data.get("chemistry") or {}
    ocm = data.get("ocm") or {}
    inputs = data.get("inputs") or {}

    gex_fq = fastq.get("gex") or {}
    adt_fq = fastq.get("adt") or {}

    sample_map_path = _p(ocm.get("sample_map_tsv"))
    ocm_samples = _load_sample_map(ocm.get("sample_map"), sample_map_path)

    cfg = SimpleleafConfig(
        sample=str(data.get("sample") or path.stem),
        outdir=_p(data.get("outdir")) or Path("simpleleaf_out"),
        gex_index=_p(indices.get("gex")),
        adt_index=_p(indices.get("adt")),
        gex_r1=_p(gex_fq.get("r1")),
        gex_r2=_p(gex_fq.get("r2")),
        adt_r1=_p(adt_fq.get("r1")),
        adt_r2=_p(adt_fq.get("r2")),
        gex_h5ad=_p(inputs.get("gex_h5ad")),
        adt_h5ad=_p(inputs.get("adt_h5ad")),
        gex_alevin=_p(inputs.get("gex_alevin")),
        adt_alevin=_p(inputs.get("adt_alevin")),
        feature_ref=_p(data.get("feature_ref") or ocm.get("feature_ref")),
        gex_chemistry=str(chem.get("gex") or "10xv4-3p"),
        adt_chemistry=str(chem.get("adt") or "e14s-adt-10xv4"),
        threads=int(quant.get("threads") or data.get("threads") or 16),
        min_reads=int(quant.get("min_reads") or 10),
        resolution=str(quant.get("resolution") or "cr-like"),
        min_gex_umi_merge=int(quant.get("min_gex_umi") or 100),
        ocm_enabled=bool(ocm.get("enabled", False)),
        ocm_min_gex_umi=int(ocm.get("min_gex_umi") or 500),
        ocm_overhang_start=int(ocm.get("overhang_start") or 7),
        ocm_overhang_len=int(ocm.get("overhang_len") or 2),
        ocm_samples=ocm_samples,
        cellranger_per_sample_outs=_p(ocm.get("cellranger_per_sample_outs")),
        alevin_fry_home=_p(paths.get("alevin_fry_home")),
        conda_bin=_p(paths.get("conda_bin")),
        scratch=_p(paths.get("scratch")),
        raw=data,
    )
    return cfg


def validate_config(cfg: SimpleleafConfig, mode: str = "demux") -> list[str]:
    """Return list of problems; empty means OK."""
    errs: list[str] = []
    if mode in ("quant", "pipeline"):
        if not cfg.gex_index:
            errs.append("indices.gex is required for quant")
        if not cfg.gex_r1 or not cfg.gex_r2:
            errs.append("fastq.gex.r1/r2 are required for quant")
        if cfg.adt_r1 or cfg.adt_r2 or cfg.adt_index:
            if not cfg.adt_index:
                errs.append("indices.adt required when ADT FASTQs are set")
            if not cfg.adt_r1 or not cfg.adt_r2:
                errs.append("fastq.adt.r1/r2 required when ADT is enabled")
    if mode in ("demux", "pipeline"):
        if cfg.ocm_enabled:
            if not cfg.ocm_samples:
                errs.append("ocm.sample_map is empty")
            has_gex = bool(
                (cfg.gex_h5ad and cfg.gex_h5ad.exists())
                or (cfg.gex_alevin and cfg.gex_alevin.exists())
            )
            if mode == "demux" and not has_gex:
                # allow missing if pipeline will produce them
                if not (cfg.gex_h5ad or cfg.gex_alevin):
                    errs.append("inputs.gex_h5ad or inputs.gex_alevin required for demux")
    return errs
