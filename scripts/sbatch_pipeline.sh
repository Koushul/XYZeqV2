#!/usr/bin/env bash
#SBATCH -J simpleleaf
#SBATCH -M smp
#SBATCH -p smp
#SBATCH -q smp-smp-n
#SBATCH -t 3-00:00:00
#SBATCH -c 64
#SBATCH --mem=400G
#SBATCH -o simpleleaf_%j.out
#SBATCH -e simpleleaf_%j.err
#
# Usage:
#   sbatch -M smp scripts/sbatch_pipeline.sh configs/organized/E14S.yaml
# Optional env overrides: THREADS, OUTDIR, SCRATCH, SKIP_QUANT=1

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${1:?config yaml required}"
EXTRA=()
[[ -n "${THREADS:-}" ]] && EXTRA+=(--threads "$THREADS")
[[ -n "${OUTDIR:-}" ]] && EXTRA+=(--outdir "$OUTDIR")
[[ -n "${SCRATCH:-}" ]] && EXTRA+=(--scratch "$SCRATCH")
[[ "${SKIP_QUANT:-0}" == "1" ]] && EXTRA+=(--skip-quant)

SAMPLE="$(basename "$CONFIG" .yaml)"
export SCRATCH="${SCRATCH:-/scratch/${USER}/simpleleaf_${SAMPLE}_${SLURM_JOB_ID:-manual}}"
mkdir -p "$SCRATCH"

exec "$ROOT/scripts/run_pipeline.sh" --config "$CONFIG" --scratch "$SCRATCH" "${EXTRA[@]}"
