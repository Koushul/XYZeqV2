---
name: simpleleaf
description: >-
  Run reusable simpleaf (alevin-fry/piscem) GEX+ADT quantification and Cell
  Ranger-compatible OCM demultiplexing for GEM-X / XYZeq CITE-seq datasets.
  Use when the user mentions simpleleaf, simpleaf, OCM demux, GEM-X v4,
  overhang barcodes, XYZeq, or setting up a new sample config for GEX+ADT.
---

# simpleleaf + OCM

Config-driven wrapper around **simpleaf** quantification and **OCM** demultiplexing
(GEM-X / Chromium 3′ v4 multiplex via the 2 bp overhang at barcode positions 7–8).

## When to use

- New GEM-X GEX(+ADT) sample needs quant + optional OCM split
- Reuse existing `quants.h5ad` / alevin MTX for demux-only
- Compare simpleaf OCM cells to Cell Ranger `per_sample_outs`

## Quick start for a new dataset

1. Copy `configs/template.yaml` → `configs/<SAMPLE>.yaml`
2. Fill `sample`, `outdir`, `paths`, `indices`, `fastq`, `feature_ref`, `chemistry`
3. If OCM: set `ocm.enabled: true` and edit `ocm.sample_map` (overhang → sample_id)
4. Validate: `python -m simpleleaf validate-config --config configs/<SAMPLE>.yaml --mode pipeline`
5. Run:
   - Full: `scripts/run_pipeline.sh --config configs/<SAMPLE>.yaml`
   - Demux only: `scripts/run_pipeline.sh --config configs/<SAMPLE>.yaml --skip-quant`
   - Merge only (no OCM): `scripts/run_pipeline.sh --config configs/<SAMPLE>.yaml --merge-only`

## OCM facts agents must not reinvent

| Overhang (bc[7:9]) | Default ocm_id |
|--------------------|----------------|
| GT | OB1 |
| CA | OB2 |
| TC | OB3 |
| AG | OB4 |

- GEX chemistry: `10xv4-3p`
- ADT chemistry (this lab): `e14s-adt-10xv4` = `1{b[16]u[12]x:}2{r[15]x:}` + v4 whitelist
- Prefer existing piscem indices over rebuilding splici
- For feature refs that include both `sbc*` and colliding `oli*` (leading-A duplicates), run `python -m simpleleaf feature-ref --src full.csv --out quant.csv` before ADT index/quant
- Independent cell filter default for OCM: GEX UMI ≥ 500 (recovers CR filtered cells on E28S)

## CLI reference

```bash
python -m simpleleaf demux --config CONFIG.yaml --outdir OUT/ocm
python -m simpleleaf merge --config CONFIG.yaml --out-h5ad OUT/sample_gex_adt.h5ad
python -m simpleleaf compare --config CONFIG.yaml \
  --simpleaf-ocm-outdir OUT/ocm \
  --cellranger-per-sample-outs /path/per_sample_outs \
  --out-json OUT/ocm/compare_to_cellranger.json
python -m simpleleaf whitelist --whitelist 3M.txt.gz --outdir OUT/whitelists
```

## Environment

- Put simpleaf on `PATH` via `paths.conda_bin`
- Set `paths.alevin_fry_home` (needs registered chemistries, including `e14s-adt-10xv4`)
- Export `LD_LIBRARY_PATH=$conda/lib` if numba/llvmlite fails against system libstdc++
- `export PYTHONNOUSERSITE=1` to avoid mixed user site-packages

## Example data (af_tutorial)

- Config: `configs/examples/E28S_ocm.yaml` (OCM) and `configs/examples/E14S_cite.yaml` (no OCM)
- Provenance scripts lived under `/ix1/ylee/kor11/tools/af_tutorial/E28S_simpleaf/ocm/`
- Smoke test demux-only against existing E28S quants; expect `demux_summary.json` cell counts to match the tutorial run

## Outputs

OCM mode (`outdir/ocm/`):

- `per_sample_outs/<sample_id>/sample_filtered_gex_adt.h5ad`
- `per_sample_outs/<sample_id>/sample_filtered_feature_bc_matrix/`
- `<sample>_gex_adt_ocm.h5ad`
- `demux_summary.json`
- optional `*_cr_match.h5ad` + `compare_to_cellranger.json`

Merge mode: `<sample>_gex_adt.h5ad` with ADT in `.obsm["ADT"]`

## Agent checklist

- [ ] Do not hardcode sample paths in new scripts; edit YAML instead
- [ ] Keep overhang map in config (do not assume E28S edge/core names)
- [ ] Prefer `--skip-quant` when quants already exist
- [ ] After demux with Cell Ranger outs, run `compare` and confirm `all_cr_filtered_recovered_in_sf_raw`
- [ ] Commit configs for new samples; do not commit large h5ad/fastq outputs
