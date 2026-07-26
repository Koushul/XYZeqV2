"""OCM overhang helpers for GEM-X / Chromium 3' v4 multiplex."""
from __future__ import annotations

from .config import OcmSample
from .io import strip_gem


def ocm_id_for_barcode(
    bc: str,
    overhang_to_ocm: dict[str, str],
    start: int = 7,
    length: int = 2,
) -> str:
    b = strip_gem(bc)
    if len(b) < start + length:
        return "OTHER"
    return overhang_to_ocm.get(b[start : start + length], "OTHER")


def sample_map_tsv(samples: list[OcmSample]) -> str:
    lines = ["ocm_barcode_id\tsample_id\tdescription\toverhang"]
    for s in samples:
        lines.append(f"{s.ocm_id}\t{s.sample_id}\t{s.description}\t{s.overhang}")
    return "\n".join(lines) + "\n"
