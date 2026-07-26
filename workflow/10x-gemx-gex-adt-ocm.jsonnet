local utils = std.extVar("__utils");
local output = if std.type(std.extVar("__output")) == "null" then
  error "Pass --output so __output is set."
else std.extVar("__output");

# GEM-X 3' v4 GEX + ADT with Cell Ranger–compatible OCM demux
# OCM overhang at barcode[7:9]: configure via external demux sample map.
#
# Run:
#   simpleaf workflow run \
#     --template workflow/10x-gemx-gex-adt-ocm.jsonnet \
#     --output /path/to/outdir \
#     --jpaths workflow
#
# Prefer instantiating via a thin sample jsonnet that overlays fast_config,
# or drive quant + demux with scripts/run_pipeline.sh --config.

local meta_info = {
  threads: 16,
  output: output,
};

local template = {
  fast_config: {
    gene_expression: {
      existing_index: {
        index: null,
        t2g_map: null,
      },
      splici: {
        gtf: null,
        fasta: null,
        rlen: 91,
      },
      map_reads: {
        reads1: null,
        reads2: null,
      },
    },
    ADT: {
      existing_index: {
        index: null,
        t2g_map: null,
      },
      feature_barcode_csv: null,
      map_reads: {
        reads1: null,
        reads2: null,
      },
    },
    ocm: {
      demux_script: null,
      sample_name: "sample",
      min_gex_umi: "500",
      feature_ref_csv: null,
      cellranger_per_sample_outs: null,
      compare_script: null,
    },
  },

  advanced_config: {
    gene_expression: {
      simpleaf_index: {
        ref_type: {
          type: "existing_index",
          existing_index: $.fast_config.gene_expression.existing_index,
          splici: $.fast_config.gene_expression.splici,
          direct_ref: { ref_seq: null, t2g_map: null },
        },
        arguments: {
          active: true,
          "--threads": $.meta_info.threads,
          "--overwrite": true,
          "--kmer-length": 31,
          "--minimizer-length": utils.ml(31),
        },
        output: $.meta_info.output + "/gene_expression/simpleaf_index",
      },
      simpleaf_quant: {
        map_type: {
          type: "map_reads",
          map_reads: $.fast_config.gene_expression.map_reads,
          existing_mappings: { map_dir: null, t2g_map: null },
        },
        cell_filt_type: {
          type: "unfiltered_pl",
          unfiltered_pl: true,
          knee: false,
          expect_cells: null,
          forced_cells: null,
          explicit_pl: null,
        },
        arguments: {
          active: true,
          "--min-reads": 10,
          "--resolution": "cr-like",
          "--expected-ori": "fw",
          "--threads": $.meta_info.threads,
          "--chemistry": "10xv4-3p",
        },
        output: $.meta_info.output + "/gene_expression/simpleaf_quant",
      },
    },
    ADT: {
      simpleaf_index: {
        ref_type: {
          type: if $.fast_config.ADT.existing_index.index != null then "existing_index"
            else "direct_ref",
          existing_index: $.fast_config.ADT.existing_index,
          direct_ref: {
            ref_seq: $.meta_info.output + "/ADT/simpleaf_index/.feature_barcode_ref.fa",
            t2g_map: $.meta_info.output + "/ADT/simpleaf_index/.feature_barcode_ref_t2g.tsv",
          },
        },
        arguments: {
          active: true,
          "--threads": $.meta_info.threads,
          "--overwrite": true,
          "--kmer-length": 7,
          "--minimizer-length": utils.ml(7),
        },
        output: $.meta_info.output + "/ADT/simpleaf_index",
      },
      simpleaf_quant: {
        map_type: {
          type: "map_reads",
          map_reads: $.fast_config.ADT.map_reads,
          existing_mappings: { map_dir: null, t2g_map: null },
        },
        cell_filt_type: {
          type: "unfiltered_pl",
          unfiltered_pl: true,
          knee: false,
          expect_cells: null,
          forced_cells: null,
          explicit_pl: null,
        },
        arguments: {
          active: true,
          "--min-reads": 10,
          "--resolution": "cr-like",
          "--expected-ori": "fw",
          "--threads": $.meta_info.threads,
          "--chemistry": "e14s-adt-10xv4",
        },
        output: $.meta_info.output + "/ADT/simpleaf_quant",
      },
    },
  },

  meta_info: {
    template_name: "GEM-X 3' v4 GEX+ADT with OCM demux",
    template_id: "10x-gemx-gex-adt-ocm",
    template_version: "0.1.0",
  } + meta_info,

  workflow: {
    gene_expression: {
      simpleaf_index: utils.simpleaf_index(
        1,
        utils.ref_type($.advanced_config.gene_expression.simpleaf_index.ref_type),
        $.advanced_config.gene_expression.simpleaf_index.arguments,
        $.advanced_config.gene_expression.simpleaf_index.output,
      ),
      simpleaf_quant: utils.simpleaf_quant(
        2,
        utils.map_type(
          $.advanced_config.gene_expression.simpleaf_quant.map_type,
          $.workflow.gene_expression.simpleaf_index,
        ),
        utils.cell_filt_type($.advanced_config.gene_expression.simpleaf_quant.cell_filt_type),
        $.advanced_config.gene_expression.simpleaf_quant.arguments,
        $.advanced_config.gene_expression.simpleaf_quant.output,
      ),
    },
    ADT: {
      simpleaf_index: utils.simpleaf_index(
        6,
        utils.ref_type($.advanced_config.ADT.simpleaf_index.ref_type),
        $.advanced_config.ADT.simpleaf_index.arguments,
        $.advanced_config.ADT.simpleaf_index.output,
      ),
      simpleaf_quant: utils.simpleaf_quant(
        7,
        utils.map_type(
          $.advanced_config.ADT.simpleaf_quant.map_type,
          $.workflow.ADT.simpleaf_index,
        ),
        utils.cell_filt_type($.advanced_config.ADT.simpleaf_quant.cell_filt_type),
        $.advanced_config.ADT.simpleaf_quant.arguments,
        $.advanced_config.ADT.simpleaf_quant.output,
      ),
    },
    external_commands: {
      [if $.fast_config.ADT.feature_barcode_csv != null && $.fast_config.ADT.existing_index.index == null
        then "ADT_feature_barcode_ref"]: utils.feature_barcode_ref(
        3,
        $.fast_config.ADT.feature_barcode_csv,
        2,
        5,
        $.advanced_config.ADT.simpleaf_index.output,
      ),
      ocm_demux: {
        active: true,
        step: 8,
        program_name: "python3",
        arguments: std.prune([
          $.fast_config.ocm.demux_script,
          "--gex-alevin",
          $.advanced_config.gene_expression.simpleaf_quant.output + "/af_quant/alevin",
          "--adt-alevin",
          $.advanced_config.ADT.simpleaf_quant.output + "/af_quant/alevin",
          "--outdir",
          $.meta_info.output + "/ocm",
          "--min-gex-umi",
          $.fast_config.ocm.min_gex_umi,
          "--sample",
          $.fast_config.ocm.sample_name,
          if $.fast_config.ocm.feature_ref_csv != null then "--feature-ref" else null,
          if $.fast_config.ocm.feature_ref_csv != null then $.fast_config.ocm.feature_ref_csv else null,
          if $.fast_config.ocm.cellranger_per_sample_outs != null then "--cellranger-per-sample-outs" else null,
          if $.fast_config.ocm.cellranger_per_sample_outs != null then $.fast_config.ocm.cellranger_per_sample_outs else null,
        ]),
      },
      [if $.fast_config.ocm.compare_script != null && $.fast_config.ocm.cellranger_per_sample_outs != null
        then "ocm_compare"]: {
        active: true,
        step: 9,
        program_name: "python3",
        arguments: [
          $.fast_config.ocm.compare_script,
          "--simpleaf-ocm-outdir",
          $.meta_info.output + "/ocm",
          "--cellranger-per-sample-outs",
          $.fast_config.ocm.cellranger_per_sample_outs,
          "--out-json",
          $.meta_info.output + "/ocm/compare_to_cellranger.json",
        ],
      },
    },
  },
};

template
