"""Partition GEM-X v4 cell barcodes into OCM whitelists."""
from __future__ import annotations

import gzip
from collections import Counter
from pathlib import Path

from .config import OcmSample
from .ocm import sample_map_tsv


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt")
    return path.open("r")


def partition(
    whitelist: Path,
    outdir: Path,
    ocm_samples: list[OcmSample],
    overhang_start: int = 7,
    overhang_len: int = 2,
) -> dict[str, int]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    overhang_to_ocm = {s.overhang: s.ocm_id for s in ocm_samples}
    handles = {s.ocm_id: (outdir / f"{s.ocm_id}.txt").open("w") for s in ocm_samples}
    other = (outdir / "OTHER.txt").open("w")
    counts: Counter[str] = Counter()
    with open_text(Path(whitelist)) as fh:
        for line in fh:
            bc = line.strip().split("-")[0]
            if len(bc) != 16:
                continue
            tag = overhang_to_ocm.get(bc[overhang_start : overhang_start + overhang_len], "OTHER")
            counts[tag] += 1
            (handles.get(tag) or other).write(bc + "\n")
    for h in handles.values():
        h.close()
    other.close()
    (outdir / "ocm_sample_map.tsv").write_text(sample_map_tsv(ocm_samples))
    return dict(counts)
