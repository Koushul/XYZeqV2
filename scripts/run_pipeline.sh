#!/usr/bin/env bash
# Config-driven simpleaf GEX(+ADT) quant + optional OCM demux.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_pipeline.sh --config CONFIG.yaml [options]

Options:
  --config PATH       Sample config (required)
  --skip-quant        Skip simpleaf quant; demux/merge existing inputs
  --demux-only        Alias for --skip-quant (expects ocm.enabled)
  --merge-only        Skip quant; run GEX+ADT merge only
  --threads N         Override quant.threads
  --outdir PATH       Override outdir
  --scratch PATH      Working directory for quant
  -h, --help          Show help
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONNOUSERSITE=1

CONFIG=""
SKIP_QUANT=0
MERGE_ONLY=0
THREADS_OVERRIDE=""
OUTDIR_OVERRIDE=""
SCRATCH_OVERRIDE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --skip-quant|--demux-only) SKIP_QUANT=1; shift ;;
    --merge-only) SKIP_QUANT=1; MERGE_ONLY=1; shift ;;
    --threads) THREADS_OVERRIDE="$2"; shift 2 ;;
    --outdir) OUTDIR_OVERRIDE="$2"; shift 2 ;;
    --scratch) SCRATCH_OVERRIDE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

[[ -n "$CONFIG" && -f "$CONFIG" ]] || { echo "--config required" >&2; exit 1; }

resolve_env() {
  python3 - "$CONFIG" "$ROOT" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[2])
from simpleleaf.config import load_config
cfg = load_config(sys.argv[1])
env = {
  "SAMPLE": cfg.sample,
  "OUTDIR": str(cfg.outdir),
  "THREADS": str(cfg.threads),
  "GEX_INDEX": str(cfg.gex_index or ""),
  "ADT_INDEX": str(cfg.adt_index or ""),
  "GEX_R1": str(cfg.gex_r1 or ""),
  "GEX_R2": str(cfg.gex_r2 or ""),
  "ADT_R1": str(cfg.adt_r1 or ""),
  "ADT_R2": str(cfg.adt_r2 or ""),
  "GEX_CHEM": cfg.gex_chemistry,
  "ADT_CHEM": cfg.adt_chemistry,
  "MIN_READS": str(cfg.min_reads),
  "RESOLUTION": cfg.resolution,
  "OCM_ENABLED": "1" if cfg.ocm_enabled else "0",
  "FEATURE_REF": str(cfg.feature_ref or ""),
  "CR_OUTS": str(cfg.cellranger_per_sample_outs or ""),
  "CONDA_BIN": str(cfg.conda_bin or ""),
  "AF_HOME": str(cfg.alevin_fry_home or ""),
  "SCRATCH_CFG": str(cfg.scratch or ""),
  "GEX_H5AD": str(cfg.gex_h5ad or ""),
  "ADT_H5AD": str(cfg.adt_h5ad or ""),
  "GEX_ALEVIN": str(cfg.gex_alevin or ""),
  "ADT_ALEVIN": str(cfg.adt_alevin or ""),
}
print("\n".join(f"{k}={json.dumps(v)}" for k, v in env.items()))
PY
}

eval "$(resolve_env)"

OUTDIR="${OUTDIR_OVERRIDE:-$OUTDIR}"
THREADS="${THREADS_OVERRIDE:-$THREADS}"
SCRATCH="${SCRATCH_OVERRIDE:-${SCRATCH_CFG:-${SCRATCH:-$OUTDIR/scratch}}}"
mkdir -p "$OUTDIR" "$SCRATCH" "$OUTDIR/logs"

if [[ -n "$CONDA_BIN" ]]; then
  export PATH="$CONDA_BIN:$PATH"
  CONDA_ROOT="$(dirname "$CONDA_BIN")"
  if [[ -d "$CONDA_ROOT/lib" ]]; then
    export LD_LIBRARY_PATH="$CONDA_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  fi
fi
if [[ -n "$AF_HOME" ]]; then
  export ALEVIN_FRY_HOME="$AF_HOME"
fi
ulimit -n 2048 || true

MODE="pipeline"
[[ "$SKIP_QUANT" -eq 1 ]] && MODE="demux"
[[ "$MERGE_ONLY" -eq 1 ]] && MODE="merge"
python3 -m simpleleaf validate-config --config "$CONFIG" --mode "$MODE" || true

if [[ "$SKIP_QUANT" -eq 0 ]]; then
  command -v simpleaf >/dev/null || { echo "simpleaf not on PATH" >&2; exit 1; }
  simpleaf set-paths

  THREADS_TOTAL="$THREADS"
  THREADS_GEX=$(( THREADS_TOTAL * 3 / 4 ))
  THREADS_ADT=$(( THREADS_TOTAL - THREADS_GEX ))
  [[ "$THREADS_ADT" -lt 8 ]] && THREADS_ADT=8 && THREADS_GEX=$(( THREADS_TOTAL - THREADS_ADT ))

  mkdir -p "$SCRATCH/stage/gex_index" "$SCRATCH/stage/fastq"
  rm -rf "$SCRATCH/stage/gex_index"
  mkdir -p "$SCRATCH/stage/gex_index"
  cp -a "$GEX_INDEX"/. "$SCRATCH/stage/gex_index/"

  # Stage FASTQs as scratch symlinks. Always symlink each file so paths with
  # commas (e.g. "Lee, Youjin") are not misparsed as multi-FASTQ lists by piscem.
  stage_reads() {
    local src="$1" name="$2"
    local -a parts=()
    local -a staged=()
    local i=0 p link
    IFS=',' read -r -a parts <<< "$src"
    # If a single path contains commas (directory name), parts length >1 but
    # intermediate pieces won't exist as files — detect and treat as one path.
    if [[ ${#parts[@]} -gt 1 ]]; then
      local all_exist=1
      for p in "${parts[@]}"; do
        [[ -e "$p" ]] || { all_exist=0; break; }
      done
      if [[ "$all_exist" -eq 0 ]]; then
        parts=("$src")
      fi
    fi
    for p in "${parts[@]}"; do
      link="$SCRATCH/stage/fastq/${name}_${i}.fastq.gz"
      ln -sfn "$p" "$link"
      staged+=("$link")
      i=$((i + 1))
    done
    local IFS=','
    echo "${staged[*]}"
  }
  GEX_R1_ARG="$(stage_reads "$GEX_R1" gex_R1)"
  GEX_R2_ARG="$(stage_reads "$GEX_R2" gex_R2)"

  run_gex() {
    rm -rf "$SCRATCH/gex_quant"
    simpleaf quant \
      --reads1 "$GEX_R1_ARG" \
      --reads2 "$GEX_R2_ARG" \
      --threads "$THREADS_GEX" \
      --index "$SCRATCH/stage/gex_index" \
      --chemistry "$GEX_CHEM" \
      --resolution "$RESOLUTION" \
      --unfiltered-pl \
      --min-reads "$MIN_READS" \
      --anndata-out \
      --output "$SCRATCH/gex_quant" \
      >"$OUTDIR/logs/quant_gex.log" 2>&1
  }

  if [[ -n "$ADT_R1" && -n "$ADT_INDEX" ]]; then
    rm -rf "$SCRATCH/stage/adt_index"
    mkdir -p "$SCRATCH/stage/adt_index"
    cp -a "$ADT_INDEX"/. "$SCRATCH/stage/adt_index/"
    ADT_R1_ARG="$(stage_reads "$ADT_R1" adt_R1)"
    ADT_R2_ARG="$(stage_reads "$ADT_R2" adt_R2)"

    run_adt() {
      rm -rf "$SCRATCH/adt_quant"
      simpleaf quant \
        --reads1 "$ADT_R1_ARG" \
        --reads2 "$ADT_R2_ARG" \
        --threads "$THREADS_ADT" \
        --index "$SCRATCH/stage/adt_index" \
        --chemistry "$ADT_CHEM" \
        --resolution "$RESOLUTION" \
        --unfiltered-pl \
        --anndata-out \
        --output "$SCRATCH/adt_quant" \
        >"$OUTDIR/logs/quant_adt.log" 2>&1
    }

    run_gex & PID_GEX=$!
    run_adt & PID_ADT=$!
    RC_GEX=0
    RC_ADT=0
    wait $PID_GEX || RC_GEX=$?
    wait $PID_ADT || RC_ADT=$?
    if [[ "$RC_GEX" -ne 0 || "$RC_ADT" -ne 0 ]]; then
      echo "quant failed gex_rc=$RC_GEX adt_rc=$RC_ADT" >&2
      tail -50 "$OUTDIR/logs/quant_gex.log" >&2 || true
      tail -50 "$OUTDIR/logs/quant_adt.log" >&2 || true
      exit 1
    fi
    rm -rf "$OUTDIR/gex_quant" "$OUTDIR/adt_quant"
    cp -a "$SCRATCH/gex_quant" "$OUTDIR/gex_quant"
    cp -a "$SCRATCH/adt_quant" "$OUTDIR/adt_quant"
    GEX_H5AD="$OUTDIR/gex_quant/af_quant/alevin/quants.h5ad"
    ADT_H5AD="$OUTDIR/adt_quant/af_quant/alevin/quants.h5ad"
  else
    run_gex
    rm -rf "$OUTDIR/gex_quant"
    cp -a "$SCRATCH/gex_quant" "$OUTDIR/gex_quant"
    GEX_H5AD="$OUTDIR/gex_quant/af_quant/alevin/quants.h5ad"
    ADT_H5AD=""
  fi
fi

if [[ "$MERGE_ONLY" -eq 1 || "$OCM_ENABLED" != "1" ]]; then
  OUT_H5AD="$OUTDIR/${SAMPLE}_gex_adt.h5ad"
  MERGE_ARGS=(--config "$CONFIG" --outdir "$OUTDIR" --out-h5ad "$OUT_H5AD")
  [[ -n "${GEX_H5AD:-}" ]] && MERGE_ARGS+=(--gex-h5ad "$GEX_H5AD")
  [[ -n "${ADT_H5AD:-}" ]] && MERGE_ARGS+=(--adt-h5ad "$ADT_H5AD")
  [[ -n "${FEATURE_REF:-}" ]] && MERGE_ARGS+=(--feature-ref "$FEATURE_REF")
  python3 -m simpleleaf merge "${MERGE_ARGS[@]}"
else
  OCM_OUT="$OUTDIR/ocm"
  DEMUX_ARGS=(--config "$CONFIG" --outdir "$OCM_OUT")
  [[ -n "${GEX_H5AD:-}" ]] && DEMUX_ARGS+=(--gex-h5ad "$GEX_H5AD")
  [[ -n "${ADT_H5AD:-}" ]] && DEMUX_ARGS+=(--adt-h5ad "$ADT_H5AD")
  [[ -n "${FEATURE_REF:-}" ]] && DEMUX_ARGS+=(--feature-ref "$FEATURE_REF")
  [[ -n "${CR_OUTS:-}" ]] && DEMUX_ARGS+=(--cellranger-per-sample-outs "$CR_OUTS")
  python3 -m simpleleaf demux "${DEMUX_ARGS[@]}"
  if [[ -n "${CR_OUTS:-}" ]]; then
    python3 -m simpleleaf compare \
      --config "$CONFIG" \
      --simpleaf-ocm-outdir "$OCM_OUT" \
      --cellranger-per-sample-outs "$CR_OUTS" \
      --out-json "$OCM_OUT/compare_to_cellranger.json"
  fi
fi

echo "DONE -> $OUTDIR"
