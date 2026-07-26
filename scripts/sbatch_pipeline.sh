#!/usr/bin/env bash
#SBATCH -J simpleleaf
#SBATCH -t 2:00:00
#SBATCH -c 112
#SBATCH --mem=400G
#SBATCH -o simpleleaf_%j.out
#SBATCH -e simpleleaf_%j.err
#
# Usage:
#   sbatch scripts/sbatch_pipeline.sh configs/examples/E28S_ocm.yaml
# Optional env overrides: THREADS, OUTDIR, SCRATCH, SKIP_QUANT=1

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${1:?config yaml required}"
EXTRA=()
[[ -n "${THREADS:-}" ]] && EXTRA+=(--threads "$THREADS")
[[ -n "${OUTDIR:-}" ]] && EXTRA+=(--outdir "$OUTDIR")
[[ -n "${SCRATCH:-}" ]] && EXTRA+=(--scratch "$SCRATCH")
[[ "${SKIP_QUANT:-0}" == "1" ]] && EXTRA+=(--skip-quant)
exec "$ROOT/scripts/run_pipeline.sh" --config "$CONFIG" "${EXTRA[@]}"
