#!/usr/bin/env bash
#SBATCH -J simpleleaf
#SBATCH -t 3-00:00:00
#SBATCH -c 64
#SBATCH --mem=400G
#SBATCH -o simpleleaf_%j.out
#SBATCH -e simpleleaf_%j.err
#
# Prefer submit_organized_smp.sh / submit_organized_htc.sh which set -M/-p/-q.
# Usage:
#   sbatch -M htc -p htc -q htc-htc-n scripts/sbatch_pipeline.sh configs/organized/E14S.yaml
# Optional env overrides: THREADS, OUTDIR, SCRATCH, SKIP_QUANT=1

set -euo pipefail
# BASH_SOURCE is unreliable under Slurm (script is copied to spool); pin install root.
ROOT="/ix1/ylee/kor11/tools/XYZeqV2"
CONFIG="${1:?config yaml required}"
[[ "$CONFIG" = /* ]] || CONFIG="$ROOT/$CONFIG"
EXTRA=()
[[ -n "${THREADS:-}" ]] && EXTRA+=(--threads "$THREADS")
[[ -n "${OUTDIR:-}" ]] && EXTRA+=(--outdir "$OUTDIR")
[[ "${SKIP_QUANT:-0}" == "1" ]] && EXTRA+=(--skip-quant)

SAMPLE="$(basename "$CONFIG" .yaml)"

if [[ -n "${SCRATCH:-}" ]]; then
  :
elif [[ -n "${SLURM_JOB_ID:-}" ]]; then
  if mkdir -p "/scratch/slurm-${SLURM_JOB_ID}/simpleleaf_${SAMPLE}" 2>/dev/null; then
    SCRATCH="/scratch/slurm-${SLURM_JOB_ID}/simpleleaf_${SAMPLE}"
  elif mkdir -p "/scratch/${USER}/simpleleaf_${SAMPLE}_${SLURM_JOB_ID}" 2>/dev/null; then
    SCRATCH="/scratch/${USER}/simpleleaf_${SAMPLE}_${SLURM_JOB_ID}"
  else
    SCRATCH="/tmp/${USER}/simpleleaf_${SAMPLE}_${SLURM_JOB_ID}"
    mkdir -p "$SCRATCH"
  fi
else
  SCRATCH="/tmp/${USER}/simpleleaf_${SAMPLE}_manual"
  mkdir -p "$SCRATCH"
fi
export SCRATCH
mkdir -p "$SCRATCH"
echo "SCRATCH=$SCRATCH host=$(hostname) job=${SLURM_JOB_ID:-none} config=$CONFIG"

exec "$ROOT/scripts/run_pipeline.sh" --config "$CONFIG" --scratch "$SCRATCH" "${EXTRA[@]}"
