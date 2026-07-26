#!/usr/bin/env bash
# Submit simpleleaf jobs for all configs/organized/*.yaml on the SMP cluster.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG_DIR="${1:-$ROOT/configs/organized}"
LOG_DIR="${SUBMIT_LOG_DIR:-/ix1/ylee/shared/organized_experiments/simpleleaf_runs/slurm_logs}"
mkdir -p "$LOG_DIR"

shopt -s nullglob
configs=("$CFG_DIR"/*.yaml)
[[ ${#configs[@]} -gt 0 ]] || { echo "No configs in $CFG_DIR" >&2; exit 1; }

echo "Submitting ${#configs[@]} jobs to SMP (-c 64, 400G, qos smp-smp-n)"
for cfg in "${configs[@]}"; do
  sample="$(basename "$cfg" .yaml)"
  jid=$(sbatch -M smp \
    -J "sl_${sample}" \
    -o "$LOG_DIR/${sample}_%j.out" \
    -e "$LOG_DIR/${sample}_%j.err" \
    "$ROOT/scripts/sbatch_pipeline.sh" "$cfg" | awk '{print $NF}')
  echo "$sample  job_id=$jid  config=$cfg"
done
