#!/usr/bin/env bash
# Finish merge/OCM demux for samples that already have quants.h5ad in outdir.
set -euo pipefail
ROOT="/ix1/ylee/kor11/tools/XYZeqV2"
LOG_DIR="${SUBMIT_LOG_DIR:-/ix1/ylee/shared/organized_experiments/simpleleaf_runs/slurm_logs}"
RUNS="/ix1/ylee/shared/organized_experiments/simpleleaf_runs"
mkdir -p "$LOG_DIR"

samples=("$@")
if [[ ${#samples[@]} -eq 0 ]]; then
  samples=(E1P E2S E6T E14S E16S E27 E28S E29 E30 E31S)
fi

for sample in "${samples[@]}"; do
  cfg="$ROOT/configs/organized/${sample}.yaml"
  gex="$RUNS/$sample/gex_quant/af_quant/alevin/quants.h5ad"
  [[ -f "$cfg" ]] || { echo "missing config $cfg" >&2; continue; }
  [[ -f "$gex" ]] || { echo "skip $sample (no gex quant)" >&2; continue; }

  # OCM samples need demux (--skip-quant); others only need merge.
  if grep -q 'enabled: true' "$cfg"; then
    mode_env=(--export=ALL,SKIP_QUANT=1)
    tag=demux
  else
    mode_env=(--export=ALL,MERGE_ONLY=1)
    tag=merge
  fi

  out=$(sbatch -M htc -p htc -q htc-htc-n \
    -J "sl_${sample}_${tag}" \
    -t 4:00:00 \
    -c 16 \
    --mem=64G \
    "${mode_env[@]}" \
    -o "$LOG_DIR/${sample}_${tag}_%j.out" \
    -e "$LOG_DIR/${sample}_${tag}_%j.err" \
    "$ROOT/scripts/sbatch_pipeline.sh" "$cfg")
  jid=$(echo "$out" | grep -oE '[0-9]+' | head -1)
  echo "$sample  $tag  job_id=$jid  $out"
done
