#!/usr/bin/env python3
"""Tests for research-writing/scripts/ai_style_scan.py (measuring machine-writing tells) and
ai_style_rewrite.py (the rewrite brief, chunk selection and the structural guard). No CLI is launched.

Run: python tests/test_ai_style_tools.py        (stdlib unittest; no third-party deps)
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, ".claude", "skills", "research-writing", "scripts")


def _load(name):
    sys.path.insert(0, SCRIPTS)  # ai_style_rewrite imports ai_style_scan by name
    try:
        spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, f"{name}.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod  # dataclasses resolve their module through sys.modules
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(SCRIPTS)


scan = _load("ai_style_scan")
rewrite = _load("ai_style_rewrite")

STYLED = (
    "# Results\n\n"
    "Our method — unlike the baseline — works well; it delves into the data.\n\n"
    "| a; b | c — d |\n|---|---|\n\n"
    "Prior work (Smith 2021; Lee 2023) disagrees.\n\n"
    "## References\n\nSmith — 2021; a tapestry of results.\n"
)


class Scan(unittest.TestCase):
    def test_counts_prose_tells_only(self):
        hits = scan.scan_text(STYLED)
        self.assertEqual(len(hits["em_dash"]), 2)          # table row and References are not prose
        self.assertEqual(len(hits["semicolon"]), 1)        # the citation-group semicolon is masked
        self.assertEqual([h[1].lower() for h in hits["ban_words"]], ["delves"])

    def test_allow_list_masks_a_defined_label(self):
        text = "We report the leverage ratio and the Pivotal Score.\n"
        self.assertEqual(len(scan.scan_text(text)["ban_words"]), 1)
        allow = scan.ALLOW_PHRASES + ["Pivotal Score"]
        self.assertEqual(len(scan.scan_text(text, allow=allow)["ban_words"]), 0)

    def test_allow_file_skips_blank_and_comment_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "allow.txt"
            p.write_text("# project labels\nPivotal Score\n\n", encoding="utf-8")
            self.assertEqual(scan.load_allow(str(p)), scan.ALLOW_PHRASES + ["Pivotal Score"])

    def test_strict_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            styled, clean = Path(d) / "styled.md", Path(d) / "clean.md"
            styled.write_text(STYLED, encoding="utf-8")
            clean.write_text("We measured the effect on ten datasets and report it below.\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(scan.main([str(styled), "--strict"]), 1)
                self.assertEqual(scan.main([str(clean), "--strict"]), 0)
                self.assertEqual(scan.main([str(styled)]), 0)   # without --strict the report never fails

    def test_list_prints_every_hit_with_its_line(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "p.md"
            f.write_text(STYLED, encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                scan.main([str(f), "--list", "em_dash"])
            self.assertEqual(buf.getvalue().count(":3:"), 2)


class LatexAndPandocDialect(unittest.TestCase):
    def test_en_dash_forms_are_typography_not_tells(self):
        text = "Ranges 7--17 and 2016--2018, Newey--West errors, $0.49$--$0.69$, and a long--short book.\n"
        self.assertEqual(scan.scan_text(text)["em_dash"], [])

    def test_real_joints_still_count(self):
        text = "The gain held---as expected---and the loss -- a small one -- did too; so did the rest.\n"
        self.assertEqual(len(scan.scan_text(text)["em_dash"]), 4)

    def test_raw_latex_and_pandoc_citations_are_not_prose(self):
        text = ("\\begin{center}\n\\begin{tikzpicture}\n\\draw (0,0) -- (1,1);\n\\node at (0,0) {a; b};\n"
                "\\end{tikzpicture}\n\\end{center}\n\n"
                "As shown [@smith2021; @lee2023] and in \\S\\ref{sec:a}, the result holds.\n")
        self.assertEqual(scan.scan_text(text)["semicolon"], [])
        self.assertEqual(scan.scan_text(text)["em_dash"], [])

    def test_front_matter_fences_are_not_dashes_but_the_abstract_is_still_prose(self):
        text = "---\ntitle: T\nabstract: |\n  We delve into the data.\n---\n\nBody text.\n"
        hits = scan.scan_text(text)
        self.assertEqual(hits["em_dash"], [])                                   # the two "---" fences
        self.assertEqual([h[1].lower() for h in hits["ban_words"]], ["delve"])  # the YAML abstract is read


class Rewrite(unittest.TestCase):
    def test_brief_freezes_the_project_terms(self):
        self.assertIn("ScoreGate, and every other defined name", rewrite.brief(1, ["ScoreGate"]))
        self.assertIn(rewrite.DEFAULT_TERMS, rewrite.brief(2, []))
        self.assertNotIn("{TERMS}", rewrite.brief(1, []) + rewrite.brief(2, []))

    def test_skip_if_contains_keeps_a_chunk_out(self):
        body = "## Intro\n\n" + "Our method — unlike the baseline — works. " * 10
        self.assertTrue(rewrite.worth_sending(body))
        self.assertFalse(rewrite.worth_sending(body, ("unlike the baseline",)))

    def test_guard_rejects_a_changed_number(self):
        old = "The gain is 0.37 — larger than before.\n"
        self.assertEqual(rewrite.guard(old, "The gain is 0.37, larger than before.\n"), [])
        self.assertTrue(rewrite.guard(old, "The gain is 0.38, larger than before.\n"))

    def test_level_one_headings_split_and_references_are_skipped(self):
        text = "# Intro\n\nFirst section text.\n\n# Method\n\nSecond section text.\n\n# References\n\nSmith 2021.\n"
        ids = [cid for cid, _ in rewrite.chunks_of("p", text)]
        self.assertEqual(len(ids), 2)
        self.assertFalse(any("references" in i for i in ids))

    def test_front_matter_chunk_is_never_sent(self):
        body = "---\ntitle: X\nabstract: |\n  Our method — unlike the baseline — works.\n---\n\n" + "Our method — unlike the baseline — works. " * 10
        self.assertFalse(rewrite.worth_sending(body))

    def test_caption_and_raw_latex_lines_are_frozen_and_not_counted(self):
        s = "![A caption; with a semicolon](fig.png){#fig:a}\n\\draw (0,0) -- (1,1);\nPlain prose here.\n"
        self.assertIn("\\draw (0,0) -- (1,1);", rewrite.skeleton(s))
        self.assertIn("![A caption; with a semicolon](fig.png){#fig:a}", rewrite.skeleton(s))
        self.assertEqual(rewrite.editable_style_count(s)["semicolon"], 0)

    def test_pandoc_citations_and_labels_are_protected_tokens(self):
        toks = rewrite.tokens("See [@smith2021], \\ref{sec:a} and the table {#tbl:main}.")
        for t in ("[@smith2021]", "\\ref{sec:a}", "{#tbl:main"):
            self.assertIn(t, toks)

    def test_unanchored_edits_are_reverted(self):
        # the second edit sits well beyond GROUP_GAP and ANCHOR_WINDOW from the dash, so it is judged alone
        filler = "We held every setting fixed across the whole period of the study and report all cells. "
        old = "Alpha is small — it fades. " + filler + "The market was calm and the sample was long enough.\n"
        new = "Alpha is small: it fades. " + filler + "The market was quiet and the sample was long enough.\n"
        merged, kept, reverted, _ = rewrite.anchored_merge(old, new)
        self.assertIn("small: it fades", merged)      # next to a dash: kept
        self.assertIn("was calm", merged)             # far from any tell: reverted
        self.assertEqual((kept > 0, reverted), (True, 1))


if __name__ == "__main__":
    unittest.main()
