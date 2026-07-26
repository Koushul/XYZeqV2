"""CLI for simpleleaf pipelines."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import DEFAULT_OCM_MAP, _load_sample_map, load_config, validate_config


def _add_common_io(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--config", type=Path, help="Sample YAML/JSON config")
    ap.add_argument("--outdir", type=Path)
    ap.add_argument("--sample", default=None)
    ap.add_argument("--gex-h5ad", type=Path)
    ap.add_argument("--adt-h5ad", type=Path)
    ap.add_argument("--gex-alevin", type=Path)
    ap.add_argument("--adt-alevin", type=Path)
    ap.add_argument("--feature-ref", type=Path)


def cmd_validate(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    mode = args.mode
    errs = validate_config(cfg, mode=mode)
    print(json.dumps({"sample": cfg.sample, "outdir": str(cfg.outdir), "errors": errs}, indent=2))
    return 1 if errs else 0


def cmd_demux(args: argparse.Namespace) -> int:
    from .demux import demux, demux_from_config

    if args.config:
        cfg = load_config(args.config)
        if args.outdir:
            cfg.outdir = args.outdir
        if args.gex_h5ad:
            cfg.gex_h5ad = args.gex_h5ad
        if args.adt_h5ad:
            cfg.adt_h5ad = args.adt_h5ad
        if args.gex_alevin:
            cfg.gex_alevin = args.gex_alevin
        if args.adt_alevin:
            cfg.adt_alevin = args.adt_alevin
        if args.feature_ref:
            cfg.feature_ref = args.feature_ref
        if args.min_gex_umi is not None:
            cfg.ocm_min_gex_umi = args.min_gex_umi
        if args.cellranger_per_sample_outs:
            cfg.cellranger_per_sample_outs = args.cellranger_per_sample_outs
        cfg.ocm_enabled = True
        errs = validate_config(cfg, mode="demux")
        if errs and not (cfg.gex_h5ad or cfg.gex_alevin):
            print("Config errors:", *errs, sep="\n  ", file=sys.stderr)
            return 1
        demux_from_config(cfg, outdir=args.outdir)
        return 0

    if not args.outdir:
        print("--outdir is required without --config", file=sys.stderr)
        return 1
    samples = _load_sample_map(None, args.sample_map_tsv) if args.sample_map_tsv else _load_sample_map(DEFAULT_OCM_MAP, None)
    demux(
        outdir=args.outdir,
        sample=args.sample or "sample",
        gex_h5ad=args.gex_h5ad,
        adt_h5ad=args.adt_h5ad,
        gex_alevin=args.gex_alevin,
        adt_alevin=args.adt_alevin,
        feature_ref=args.feature_ref,
        min_gex_umi=args.min_gex_umi or 500,
        ocm_samples=samples,
        cellranger_per_sample_outs=args.cellranger_per_sample_outs,
    )
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    from .merge import merge_from_config, merge_gex_adt

    if args.config:
        cfg = load_config(args.config)
        if args.outdir:
            cfg.outdir = args.outdir
        if args.gex_h5ad:
            cfg.gex_h5ad = args.gex_h5ad
        if args.adt_h5ad:
            cfg.adt_h5ad = args.adt_h5ad
        merge_from_config(cfg, out_h5ad=args.out_h5ad)
        return 0

    if not args.out_h5ad:
        print("--out-h5ad is required without --config", file=sys.stderr)
        return 1
    merge_gex_adt(
        gex_h5ad=args.gex_h5ad,
        adt_h5ad=args.adt_h5ad,
        gex_alevin=args.gex_alevin,
        adt_alevin=args.adt_alevin,
        feature_ref=args.feature_ref,
        min_gex_umi=args.min_gex_umi or 100,
        sample=args.sample or "sample",
        out_h5ad=args.out_h5ad,
    )
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    from .compare import compare

    sample_ids = None
    if args.config:
        cfg = load_config(args.config)
        ocm_dir = args.simpleaf_ocm_outdir or (cfg.outdir / "ocm")
        cr = args.cellranger_per_sample_outs or cfg.cellranger_per_sample_outs
        out_json = args.out_json or (Path(ocm_dir) / "compare_to_cellranger.json")
        sample_ids = [s.sample_id for s in cfg.ocm_samples]
    else:
        ocm_dir = args.simpleaf_ocm_outdir
        cr = args.cellranger_per_sample_outs
        out_json = args.out_json
    if not ocm_dir or not cr or not out_json:
        print("Need ocm outdir, cellranger outs, and out-json", file=sys.stderr)
        return 1
    compare(Path(ocm_dir), Path(cr), Path(out_json), sample_ids=sample_ids)
    return 0


def cmd_whitelist(args: argparse.Namespace) -> int:
    from .whitelist import partition

    if args.config:
        cfg = load_config(args.config)
        samples = cfg.ocm_samples
        start, length = cfg.ocm_overhang_start, cfg.ocm_overhang_len
    else:
        samples = (
            _load_sample_map(None, args.sample_map_tsv)
            if args.sample_map_tsv
            else _load_sample_map(DEFAULT_OCM_MAP, None)
        )
        start, length = 7, 2
    counts = partition(args.whitelist, args.outdir, samples, start, length)
    print(f"Wrote OCM whitelists to {args.outdir}")
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")
    return 0


def cmd_feature_ref(args: argparse.Namespace) -> int:
    from .feature_ref import make_quant_feature_ref

    make_quant_feature_ref(args.src, args.out, args.report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="simpleleaf",
        description="Reusable simpleaf + OCM workflows for GEM-X / XYZeq CITE-seq",
    )
    ap.add_argument("--version", action="version", version=f"simpleleaf {__version__}")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("validate-config", help="Validate a sample config")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--mode", choices=["demux", "quant", "pipeline", "merge"], default="demux")
    p.set_defaults(func=cmd_validate)

    p = sp.add_parser("demux", help="OCM demultiplex GEX(+ADT) quants")
    _add_common_io(p)
    p.add_argument("--min-gex-umi", type=int, default=None)
    p.add_argument("--cellranger-per-sample-outs", type=Path)
    p.add_argument("--sample-map-tsv", type=Path)
    p.set_defaults(func=cmd_demux)

    p = sp.add_parser("merge", help="Merge GEX+ADT without OCM")
    _add_common_io(p)
    p.add_argument("--out-h5ad", type=Path)
    p.add_argument("--min-gex-umi", type=int, default=None)
    p.set_defaults(func=cmd_merge)

    p = sp.add_parser("compare", help="Compare OCM demux to Cell Ranger")
    p.add_argument("--config", type=Path)
    p.add_argument("--simpleaf-ocm-outdir", type=Path)
    p.add_argument("--cellranger-per-sample-outs", type=Path)
    p.add_argument("--out-json", type=Path)
    p.set_defaults(func=cmd_compare)

    p = sp.add_parser("whitelist", help="Split barcode whitelist by OCM overhang")
    p.add_argument("--config", type=Path)
    p.add_argument("--whitelist", type=Path, required=True)
    p.add_argument("--outdir", type=Path, required=True)
    p.add_argument("--sample-map-tsv", type=Path)
    p.set_defaults(func=cmd_whitelist)

    p = sp.add_parser("feature-ref", help="Drop colliding oli* features for ADT quant")
    p.add_argument("--src", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path)
    p.set_defaults(func=cmd_feature_ref)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return int(args.func(args))
