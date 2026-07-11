#!/usr/bin/env python3
"""Tests for research-visuals/scripts/audit_visuals.py — run with:
     python -m pytest tests/test_audit_visuals.py

Covers the brittle, fail-loud parsing of Poppler output with captured fixtures
(stdlib unittest only — no PDF needed). An optional integration test runs
against a real PDF if RESEARCH_VISUALS_SAMPLE_PDF is set and Poppler exists.
"""
import os
import sys
import unittest
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, ".claude", "skills", "research-visuals", "scripts")
sys.path.insert(0, SCRIPTS)
import audit_visuals as av  # noqa: E402

# ---- captured fixtures (realistic Poppler output) ------------------------- #
FONTS_CONSISTENT = """\
name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
ABCDEF+TimesNewRomanPSMT             CID TrueType      Identity-H       yes yes yes      7  0
BCDEFG+TimesNewRomanPS-BoldMT        CID TrueType      Identity-H       yes yes yes      8  0
CDEFGH+TimesNewRomanPS-ItalicMT      CID TrueType      Identity-H       yes yes yes      9  0
DEFGHI+Consolas                      CID TrueType      Identity-H       yes yes yes     10  0
"""

FONTS_CHAOTIC = """\
name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
AAAAAA+Arial-BoldMT                  CID TrueType      Identity-H       yes yes yes      4  0
BAAAAA+Georgia                       CID TrueType      Identity-H       yes yes yes      5  0
DAAAAA+TimesNewRomanPS-BoldMT        CID TrueType      Identity-H       yes yes yes      7  0
GAAAAA+Consolas                      CID TrueType      Identity-H       yes yes yes     10  0
NAAAAA+CambriaMath                   CID TrueType      Identity-H       yes yes yes     31  0
JAAAAA+SegoeUISymbol                 CID TrueType      Identity-H       yes yes yes     21  0
RAAAAA+MS-PGothic                    CID TrueType      Identity-H       yes yes yes     72  0
[none]                               Type 3            Custom           yes no  yes     22  0
Helvetica                            Type 1            Standard         no  no  no        9  0
"""

RASTER_GOOD = """\
page   num  type   width height color comp bpc  enc    interp  object ID x-ppi y-ppi size ratio
--------------------------------------------------------------------------------------------
   3     0 image    2763  2142  rgb     3   8  jpeg   no         3  0   428   428  1.2M 1.2%
"""

RASTER_LOWDPI = """\
page   num  type   width height color comp bpc  enc    interp  object ID x-ppi y-ppi size ratio
--------------------------------------------------------------------------------------------
   3     0 image    2763  2142  rgb     3   8  jpeg   no         3  0   428   428  1.2M 1.2%
  18     1 image     999   737  rgb     3   8  jpeg   no        12  0   155   155   80K 2.0%
  26     2 image    1093  1142  rgb     3   8  jpeg   no        14  0   170   170   90K 2.0%
"""


class TestFamilyOf(unittest.TestCase):
    def test_collapses_subset_and_style(self):
        self.assertEqual(av.family_of("AAAAAA+Arial-BoldMT"), "Arial")
        self.assertEqual(av.family_of("TimesNewRomanPS-BoldMT"), "TimesNewRoman")
        self.assertEqual(av.family_of("TimesNewRomanPSMT"), "TimesNewRoman")
        self.assertEqual(av.family_of("DEFGHI+Consolas"), "Consolas")
        self.assertEqual(av.family_of("Georgia-Bold"), "Georgia")
        self.assertEqual(av.family_of("CambriaMath"), "CambriaMath")


class TestParseFonts(unittest.TestCase):
    def test_consistent(self):
        f = av.parse_fonts(FONTS_CONSISTENT)
        self.assertTrue(f["parse_ok"])
        self.assertEqual(f["rows"], 4)
        self.assertEqual(set(f["families"]), {"TimesNewRoman", "Consolas"})
        self.assertEqual(f["n_families"], 2)
        self.assertEqual(f["non_embedded"], [])
        self.assertEqual(f["type3"], [])

    def test_chaotic_flags_everything(self):
        f = av.parse_fonts(FONTS_CHAOTIC)
        self.assertTrue(f["parse_ok"])
        self.assertGreaterEqual(f["n_families"], 7)          # font chaos
        self.assertIn("[none]", f["type3"])                  # Type 3 detected
        self.assertIn("Helvetica", f["non_embedded"])        # non-embedded detected

    def test_garbage_is_fail_loud(self):
        self.assertFalse(av.parse_fonts("")["parse_ok"])
        self.assertFalse(av.parse_fonts("Permission denied\n")["parse_ok"])


class TestParseRaster(unittest.TestCase):
    def test_all_high_dpi(self):
        r = av.parse_raster(RASTER_GOOD, min_dpi=300)
        self.assertTrue(r["parse_ok"])
        self.assertEqual(r["n_images"], 1)
        self.assertEqual(r["low_dpi"], [])
        self.assertEqual(r["min_dpi_seen"], 428)

    def test_low_dpi_flagged(self):
        r = av.parse_raster(RASTER_LOWDPI, min_dpi=300)
        self.assertTrue(r["parse_ok"])
        self.assertEqual(r["n_images"], 3)
        self.assertEqual(len(r["low_dpi"]), 2)               # 155 and 170 dpi
        self.assertEqual(r["min_dpi_seen"], 155)
        self.assertEqual({i["page"] for i in r["low_dpi"]}, {18, 26})

    def test_garbage_is_fail_loud(self):
        self.assertFalse(av.parse_raster("", 300)["parse_ok"])
        self.assertFalse(av.parse_raster("oops\n", 300)["parse_ok"])


@unittest.skipUnless(os.environ.get("RESEARCH_VISUALS_SAMPLE_PDF")
                     and av.have("pdffonts"),
                     "set RESEARCH_VISUALS_SAMPLE_PDF and install poppler to run")
class TestIntegration(unittest.TestCase):
    def test_runs_on_real_pdf(self):
        class A:  # minimal args
            out, render_dpi, max_families, min_dpi, no_render = "qa_previews", 150, 3, 300, True
        rep = av.audit_one(Path(os.environ["RESEARCH_VISUALS_SAMPLE_PDF"]), A())
        self.assertIn("flags", rep)
        self.assertIsInstance(rep["fonts"], dict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
