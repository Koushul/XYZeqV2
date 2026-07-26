#!/usr/bin/env python3
"""Generate simpleleaf YAML configs for organized_experiments libraries."""
from __future__ import annotations

import gzip
from pathlib import Path

LIBS = Path("/ix1/ylee/shared/organized_experiments/libraries")
OUT_CFG = Path("/ix1/ylee/kor11/tools/XYZeqV2/configs/organized")
OUT_RUNS = Path("/ix1/ylee/shared/organized_experiments/simpleleaf_runs")

CONDA_BIN = "/ix1/ylee/kor11/tools/af_tutorial/conda_env/bin"
AF_HOME = "/ix1/ylee/kor11/tools/af_tutorial/E28S_simpleaf/af_home"
GEX_INDEX = "/ix1/ylee/kor11/tools/af_tutorial/E14S_simpleaf/mouse-2024-A_splici/index"
ADT_INDEX = "/ix1/ylee/kor11/tools/af_tutorial/E28S_simpleaf/adt_feature_index_quant/index"
FEATURE_REF = "/ix1/ylee/kor11/tools/af_tutorial/E28S_simpleaf/new_feature_ref_quant.csv"

# ADT living under a different library id than GEX
ADT_PAIR = {
    "E30": "E30S",
    "E31S": "E318S",
}

OCM = {
    "E28S": {
        "enabled": True,
        "min_gex_umi": 500,
        "cellranger_per_sample_outs": "/ix1/ylee/kor11/tools/af_tutorial/E28S_cellranger/E28S_ocm/outs/per_sample_outs",
        "sample_map": [
            {"overhang": "GT", "ocm_id": "OB1", "sample_id": "edge_gfp_plus", "description": "Edge GFP+ hypoxia A223"},
            {"overhang": "CA", "ocm_id": "OB2", "sample_id": "edge_gfp_minus", "description": "Edge GFP- hypoxia A223"},
            {"overhang": "TC", "ocm_id": "OB3", "sample_id": "core_gfp_plus", "description": "Core GFP+ hypoxia A223"},
            {"overhang": "AG", "ocm_id": "OB4", "sample_id": "core_gfp_minus", "description": "Core GFP- hypoxia A223"},
        ],
    },
    "E27": {
        "enabled": True,
        "min_gex_umi": 500,
        "cellranger_per_sample_outs": "/ix1/ylee/kor11/tools/af_tutorial/E27_cellranger/E27_ocm/outs/per_sample_outs",
        "sample_map": [
            {"overhang": "GT", "ocm_id": "OB1", "sample_id": "hypoxia_plus", "description": "Hypoxia+ A223 tumor"},
            {"overhang": "CA", "ocm_id": "OB2", "sample_id": "lactate_plus", "description": "Lactate+ A223 tumor"},
            {"overhang": "TC", "ocm_id": "OB3", "sample_id": "dn", "description": "DN A223 tumor"},
            {"overhang": "AG", "ocm_id": "OB4", "sample_id": "dp", "description": "DP A223 tumor"},
        ],
    },
}

MIN_ADT_BYTES = 10_000


def r1_len(path: Path) -> int:
    with gzip.open(path, "rt") as f:
        next(f)
        return len(next(f).strip())


def paired_fastqs(fastq_dir: Path) -> tuple[list[Path], list[Path]]:
    r1 = sorted(fastq_dir.glob("*_R1_*.fastq.gz")) + sorted(fastq_dir.glob("*_R1.fastq.gz"))
    # organized layout uses *_R1_001.fastq.gz
    r1 = sorted({p.resolve(): p for p in fastq_dir.glob("*R1*.fastq.gz")}.values(), key=lambda p: p.name)
    r2 = []
    for a in r1:
        b = Path(str(a).replace("_R1_", "_R2_").replace("_R1.", "_R2."))
        if not b.exists():
            # try name replace
            cand = a.parent / a.name.replace("R1", "R2")
            b = cand if cand.exists() else None
        if b is None or not Path(b).exists():
            raise FileNotFoundError(f"No R2 for {a}")
        r2.append(Path(b))
    return r1, r2


def usable_adt(adt_dir: Path) -> bool:
    if not adt_dir.is_dir():
        return False
    r1s = list(adt_dir.glob("*R1*.fastq.gz"))
    if not r1s:
        return False
    try:
        return all(p.stat().st_size >= MIN_ADT_BYTES for p in r1s)
    except OSError:
        return False


def join_paths(paths: list[Path]) -> str:
    return ",".join(str(p.resolve()) for p in paths)


def write_config(sample: str, gex_r1: list[Path], gex_r2: list[Path], adt_r1: list[Path] | None, adt_r2: list[Path] | None) -> Path:
    chem_gex = "10xv4-3p" if r1_len(gex_r1[0]) <= 30 else "10xv3"
    chem_adt = "e14s-adt-10xv4" if chem_gex == "10xv4-3p" else "e14s-adt-10xv3"
    outdir = OUT_RUNS / sample
    lines = [
        f"sample: {sample}",
        f"outdir: {outdir}",
        "",
        "paths:",
        f"  conda_bin: {CONDA_BIN}",
        f"  alevin_fry_home: {AF_HOME}",
        "",
        "indices:",
        f"  gex: {GEX_INDEX}",
    ]
    if adt_r1:
        lines.append(f"  adt: {ADT_INDEX}")
    lines += [
        "",
        "fastq:",
        "  gex:",
        f"    r1: {join_paths(gex_r1)}",
        f"    r2: {join_paths(gex_r2)}",
    ]
    if adt_r1 and adt_r2:
        lines += [
            "  adt:",
            f"    r1: {join_paths(adt_r1)}",
            f"    r2: {join_paths(adt_r2)}",
        ]
    if adt_r1:
        lines += ["", f"feature_ref: {FEATURE_REF}"]
    lines += [
        "",
        "chemistry:",
        f"  gex: {chem_gex}",
    ]
    if adt_r1:
        lines.append(f"  adt: {chem_adt}")
    lines += [
        "",
        "quant:",
        "  threads: 64",
        "  min_reads: 10",
        "  resolution: cr-like",
        "  min_gex_umi: 100",
        "",
    ]
    ocm = OCM.get(sample)
    if ocm:
        lines.append("ocm:")
        lines.append("  enabled: true")
        lines.append(f"  min_gex_umi: {ocm['min_gex_umi']}")
        lines.append("  overhang_start: 7")
        lines.append("  overhang_len: 2")
        if ocm.get("cellranger_per_sample_outs"):
            lines.append(f"  cellranger_per_sample_outs: {ocm['cellranger_per_sample_outs']}")
        lines.append("  sample_map:")
        for row in ocm["sample_map"]:
            lines.append(f"    - overhang: {row['overhang']}")
            lines.append(f"      ocm_id: {row['ocm_id']}")
            lines.append(f"      sample_id: {row['sample_id']}")
            lines.append(f"      description: {row['description']}")
    else:
        lines.append("ocm:")
        lines.append("  enabled: false")
    lines.append("")
    OUT_CFG.mkdir(parents=True, exist_ok=True)
    path = OUT_CFG / f"{sample}.yaml"
    path.write_text("\n".join(lines))
    return path


def main() -> None:
    skipped = []
    written = []
    for lib in sorted(LIBS.iterdir()):
        if not lib.is_dir():
            continue
        sample = lib.name
        gex_dir = lib / "GEX" / "fastq"
        if not gex_dir.is_dir():
            skipped.append((sample, "no GEX (ADT-only or other)"))
            continue
        gex_r1, gex_r2 = paired_fastqs(gex_dir)

        adt_lib = ADT_PAIR.get(sample, sample)
        adt_dir = LIBS / adt_lib / "ADT" / "fastq"
        adt_r1 = adt_r2 = None
        if usable_adt(adt_dir):
            adt_r1, adt_r2 = paired_fastqs(adt_dir)
        elif (lib / "ADT" / "fastq").is_dir():
            skipped.append((sample, f"ADT present but unusable/empty under {adt_dir}"))

        path = write_config(sample, gex_r1, gex_r2, adt_r1, adt_r2)
        has_adt = adt_r1 is not None
        chem = "10xv4" if r1_len(gex_r1[0]) <= 30 else "10xv3"
        written.append((sample, chem, has_adt, str(path)))

    print("WRITTEN")
    for row in written:
        print(f"  {row[0]:8s} chem={row[1]} adt={row[2]} -> {row[3]}")
    print("SKIPPED / NOTES")
    for s, why in skipped:
        print(f"  {s}: {why}")


if __name__ == "__main__":
    main()
