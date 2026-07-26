#!/usr/bin/env bash
# Submit simpleleaf jobs for all configs/organized/*.yaml on the HTC cluster.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG_DIR="${1:-$ROOT/configs/organized}"
LOG_DIR="${SUBMIT_LOG_DIR:-/ix1/ylee/shared/organized_experiments/simpleleaf_runs/slurm_logs}"
mkdir -p "$LOG_DIR"

shopt -s nullglob
configs=("$CFG_DIR"/*.yaml)
[[ ${#configs[@]} -gt 0 ]] || { echo "No configs in $CFG_DIR" >&2; exit 1; }

echo "Submitting ${#configs[@]} jobs to HTC (-c 64, 400G, qos htc-htc-n)"
for cfg in "${configs[@]}"; do
  sample="$(basename "$cfg" .yaml)"
  out=$(sbatch -M htc -p htc -q htc-htc-n \
    -J "sl_${sample}" \
    -t 3-00:00:00 \
    -c 64 \
    --mem=400G \
    -o "$LOG_DIR/${sample}_%j.out" \
    -e "$LOG_DIR/${sample}_%j.err" \
    "$ROOT/scripts/sbatch_pipeline.sh" "$cfg")
  # "Submitted batch job 123 on cluster htc" -> 123
  jid=$(echo "$out" | grep -oE '[0-9]+' | head -1)
  echo "$sample  job_id=$jid  $out"
done
