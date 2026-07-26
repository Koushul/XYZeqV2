# XYZeqV2 — simpleleaf

Reusable **simpleaf** + **OCM** workflows for GEM-X / XYZeq GEX(+ADT) datasets.

Generalizes the sample-specific scripts under `af_tutorial` into a config-driven CLI and pipeline.

## Install / env

```bash
export PATH=/ix1/ylee/kor11/tools/af_tutorial/conda_env/bin:$PATH
export LD_LIBRARY_PATH=/ix1/ylee/kor11/tools/af_tutorial/conda_env/lib:$LD_LIBRARY_PATH
export PYTHONNOUSERSITE=1
export PYTHONPATH=/ix1/ylee/kor11/tools/XYZeqV2:$PYTHONPATH
```

Requires: `simpleaf`, `scanpy`, `pandas`, `scipy`, `numpy` (provided by the af_tutorial conda env).

## New sample

```bash
cp configs/template.yaml configs/MySample.yaml
# edit paths, chemistry, ocm.sample_map
scripts/run_pipeline.sh --config configs/MySample.yaml
```

Demux existing quants only:

```bash
scripts/run_pipeline.sh --config configs/examples/E28S_ocm.yaml --skip-quant
```

## Batch: organized_experiments (SMP)

Generate configs and submit one job per GEX library (64 cores, 400G, `smp-smp-n`):

```bash
python3 scripts/generate_organized_configs.py
scripts/submit_organized_smp.sh
```

Outputs land in `/ix1/ylee/shared/organized_experiments/simpleleaf_runs/<SAMPLE>/`.
GEX uses the mouse-2024-A **splici** index (`spliced` / `unspliced` / `ambiguous` layers in h5ad).
Paired ADT is merged into `.obsm["ADT"]` when FASTQs are present (E30↔E30S, E31S↔E318S).
OCM demux is enabled for E27 and E28S.

## Layout

| Path | Role |
|------|------|
| `simpleleaf/` | Python package (`demux`, `merge`, `compare`, …) |
| `scripts/run_pipeline.sh` | Quant ± OCM / merge driver |
| `scripts/sbatch_pipeline.sh` | Slurm wrapper (SMP cluster) |
| `scripts/generate_organized_configs.py` | Build YAMLs for organized_experiments |
| `scripts/submit_organized_smp.sh` | Submit all organized configs |
| `configs/template.yaml` | Blank sample config |
| `configs/examples/` | E28S (OCM) + E14S (CITE) examples |
| `configs/organized/` | Per-library configs for organized_experiments |
| `workflow/` | simpleaf jsonnet template |
| `.cursor/skills/simpleleaf/SKILL.md` | Agent skill |

## OCM

Cell Ranger OCM (SC3Pv4-*-OCM) splits on barcode positions **7–8**:

`GT→OB1`, `CA→OB2`, `TC→OB3`, `AG→OB4`

Map those IDs to your biological sample names in `ocm.sample_map`.

## License

See `LICENSE`.
