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
# Optional env overrides: THREADS, OUTDIR, SCRATCH, SKIP_QUANT=1, MERGE_ONLY=1

set -euo pipefail
# Pin install root — BASH_SOURCE is unreliable under Slurm spool copies.
ROOT="/ix1/ylee/kor11/tools/XYZeqV2"
CONFIG="${1:?config yaml required}"
[[ "$CONFIG" = /* ]] || CONFIG="$ROOT/$CONFIG"
EXTRA=()
[[ -n "${THREADS:-}" ]] && EXTRA+=(--threads "$THREADS")
[[ -n "${OUTDIR:-}" ]] && EXTRA+=(--outdir "$OUTDIR")
[[ "${SKIP_QUANT:-0}" == "1" ]] && EXTRA+=(--skip-quant)
[[ "${MERGE_ONLY:-0}" == "1" ]] && EXTRA+=(--merge-only)

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

# Snapshot the driver script so mid-run NFS edits cannot corrupt bash's file offset.
PIPELINE_COPY="$SCRATCH/run_pipeline.sh"
cp -a "$ROOT/scripts/run_pipeline.sh" "$PIPELINE_COPY"
chmod +x "$PIPELINE_COPY"
export SIMPLELEAF_ROOT="$ROOT"

echo "SCRATCH=$SCRATCH host=$(hostname) job=${SLURM_JOB_ID:-none} config=$CONFIG"
echo "pipeline_copy=$PIPELINE_COPY"

exec "$PIPELINE_COPY" --config "$CONFIG" --scratch "$SCRATCH" "${EXTRA[@]}"
