#!/usr/bin/env python3
"""Unit tests for OCM overhang + config loading (no scanpy required)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simpleleaf.config import load_config
from simpleleaf.ocm import ocm_id_for_barcode
from simpleleaf.yaml_lite import loads


class TestOcm(unittest.TestCase):
    def test_overhang_map(self):
        m = {"GT": "OB1", "CA": "OB2", "TC": "OB3", "AG": "OB4"}
        # barcode with GT at positions 7-8
        bc = "AAAAAAAGTAAAAAAA"
        self.assertEqual(ocm_id_for_barcode(bc, m), "OB1")
        self.assertEqual(ocm_id_for_barcode(bc + "-1", m), "OB1")
        self.assertEqual(ocm_id_for_barcode("AAAAAAACAAAAAAAA", m), "OB2")
        self.assertEqual(ocm_id_for_barcode("AAAAAAATCAAAAAAA", m), "OB3")
        self.assertEqual(ocm_id_for_barcode("AAAAAAAAGAAAAAAA", m), "OB4")
        self.assertEqual(ocm_id_for_barcode("AAAAAAAAAAAAAAA", m), "OTHER")


class TestYamlLite(unittest.TestCase):
    def test_nested(self):
        text = """
sample: E28S
ocm:
  enabled: true
  min_gex_umi: 500
  sample_map:
    - overhang: GT
      ocm_id: OB1
      sample_id: edge_gfp_plus
      description: Edge GFP+ hypoxia A223
    - overhang: CA
      ocm_id: OB2
      sample_id: edge_gfp_minus
      description: Edge GFP- hypoxia A223
"""
        data = loads(text)
        self.assertEqual(data["sample"], "E28S")
        self.assertTrue(data["ocm"]["enabled"])
        self.assertEqual(data["ocm"]["min_gex_umi"], 500)
        self.assertEqual(len(data["ocm"]["sample_map"]), 2)
        self.assertEqual(data["ocm"]["sample_map"][0]["ocm_id"], "OB1")
        self.assertEqual(data["ocm"]["sample_map"][1]["sample_id"], "edge_gfp_minus")


class TestConfig(unittest.TestCase):
    def test_e28s_example(self):
        cfg = load_config(ROOT / "configs/examples/E28S_ocm.yaml")
        self.assertEqual(cfg.sample, "E28S")
        self.assertTrue(cfg.ocm_enabled)
        self.assertEqual(len(cfg.ocm_samples), 4)
        self.assertEqual(cfg.ocm_samples[0].overhang, "GT")
        self.assertEqual(cfg.overhang_to_ocm["AG"], "OB4")


if __name__ == "__main__":
    unittest.main()
