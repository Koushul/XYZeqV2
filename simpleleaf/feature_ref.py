"""Build quant-compatible feature refs (drop colliding oli* entries)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

SBC_RE = re.compile(r"^sbc(\d+)$")
OLI_RE = re.compile(r"^oli\d+$")


def make_quant_feature_ref(src: Path, out: Path, report: Path | None = None) -> dict:
    df = pd.read_csv(src)
    is_sbc = df["name"].astype(str).str.match(SBC_RE)
    is_oli = df["name"].astype(str).str.match(OLI_RE)
    quant = df[is_sbc | (~is_sbc & ~is_oli)].copy()

    sbcs = quant[quant["name"].astype(str).str.match(SBC_RE)]
    abs_ = quant[~quant["name"].astype(str).str.match(SBC_RE)]

    payload = {
        "source": str(src),
        "output": str(out),
        "n_source": int(len(df)),
        "n_quant": int(len(quant)),
        "n_sbc": int(len(sbcs)),
        "n_antibody": int(len(abs_)),
        "n_excluded_oli": int(is_oli.sum()),
        "seq_lengths": {str(k): int(v) for k, v in quant["sequence"].str.len().value_counts().items()},
    }
    if len(sbcs):
        ids = sbcs["name"].map(lambda x: int(SBC_RE.match(x).group(1)))
        payload["sbc_range"] = [int(ids.min()), int(ids.max())]
        payload["missing_sbc_1_192"] = sorted(set(range(1, 193)) - set(ids))

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    quant.to_csv(out, index=False)
    if report is not None:
        Path(report).write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return payload
