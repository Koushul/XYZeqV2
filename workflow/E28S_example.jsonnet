local base = import "10x-gemx-gex-adt-ocm.jsonnet";

# Thin overlay for E28S — prefer scripts/run_pipeline.sh + configs/examples/E28S_ocm.yaml
local AF = "/ix1/ylee/kor11/tools/af_tutorial/E28S_simpleaf";
local FASTQ = "/ix1/ylee/shared/ResequencedE15S_E27_E28S/Y.Lee_10x_07_13_2026_fastq";
local CR = "/ix1/ylee/kor11/tools/af_tutorial/E28S_cellranger/E28S_ocm/outs/per_sample_outs";
local ROOT = "/ix1/ylee/kor11/tools/XYZeqV2";

base + {
  meta_info+: {
    threads: 112,
  },
  fast_config+: {
    gene_expression+: {
      existing_index+: {
        index: AF + "/mouse-2024-A_splici/index",
        t2g_map: AF + "/mouse-2024-A_splici/index/t2g_3col.tsv",
      },
      map_reads+: {
        reads1: FASTQ + "/E28S_GEX_S3_R1_001.fastq.gz",
        reads2: FASTQ + "/E28S_GEX_S3_R2_001.fastq.gz",
      },
    },
    ADT+: {
      existing_index+: {
        index: AF + "/adt_feature_index_quant/index",
        t2g_map: AF + "/adt_feature_index_quant/index/t2g_3col.tsv",
      },
      map_reads+: {
        reads1: FASTQ + "/E28S_ADT_S4_R1_001.fastq.gz",
        reads2: FASTQ + "/E28S_ADT_S4_R2_001.fastq.gz",
      },
    },
    ocm+: {
      demux_script: ROOT + "/scripts/demux_ocm_cli.py",
      sample_name: "E28S",
      min_gex_umi: "500",
      feature_ref_csv: AF + "/new_feature_ref_quant.csv",
      cellranger_per_sample_outs: CR,
      compare_script: ROOT + "/scripts/compare_ocm_cli.py",
    },
  },
}
