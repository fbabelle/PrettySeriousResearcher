"""Repository-wide contracts for the portable research-paper skill bundle."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class SkillContracts(unittest.TestCase):
    def test_skill_frontmatter_and_size(self):
        skill_files = sorted(SKILLS.glob("*/SKILL.md"))
        self.assertEqual(len(skill_files), 16)
        for path in skill_files:
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            self.assertGreaterEqual(len(lines), 4, path)
            self.assertEqual(lines[0], "---", path)
            self.assertEqual(lines[3], "---", path)
            self.assertEqual(lines[1], f"name: {path.parent.name}", path)
            self.assertTrue(lines[2].startswith("description: "), path)
            self.assertLessEqual(len(lines[2]) - len("description: "), 500, path)
            self.assertLessEqual(len(lines), 500, path)
            self.assertTrue(text.endswith("\n"), path)

    def test_local_markdown_links_resolve(self):
        failures = []
        for path in ROOT.rglob("*.md"):
            if ".git" in path.parts or ".pytest_cache" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for raw in LINK_RE.findall(text):
                target = raw.strip().split("#", 1)[0]
                if not target or "://" in target or target.startswith(("mailto:", "#")):
                    continue
                target = target.strip("<>")
                if not (path.parent / target).resolve().exists():
                    failures.append(f"{path.relative_to(ROOT)} -> {raw}")
        self.assertEqual(failures, [])

    def test_no_false_bundled_skill_or_stale_guidance(self):
        checked = [ROOT / "README.md", ROOT / "architecture.md", ROOT / "install_skills.py"]
        checked.extend(SKILLS.rglob("*.md"))
        corpus = "\n".join(p.read_text(encoding="utf-8") for p in checked)
        forbidden = [
            "deep-research",
            "claude-api",
            ".codex/skills",
            "\\pdfoutput=1",
            "AI ≤5y",
            "finance ≤10y",
            "SEMINAL-EXCEPTION",
            "scanner greps the source",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, corpus)

    def test_experimental_rigor_contract_is_wired(self):
        skill = (SKILLS / "research-experiments" / "SKILL.md").read_text(encoding="utf-8")
        ref = SKILLS / "research-experiments" / "references" / "experimental-rigor.md"
        self.assertIn("(references/experimental-rigor.md)", skill)
        text = ref.read_text(encoding="utf-8").lower()
        for term in [
            "estimand",
            "unit of analysis",
            "sample size",
            "multiple-testing",
            "dependence",
            "exact model snapshot",
            "llm-as-judge",
            "consent",
            "irb",
        ]:
            self.assertIn(term, text)

    def test_verified_codex_path_and_current_rate_card(self):
        installer = (ROOT / "install_skills.py").read_text(encoding="utf-8")
        self.assertRegex(
            installer,
            r'"codex":\s+\{"subdir": "\.agents/skills",\s+"glob": "~/.agents/skills",\s+"verified": True\}',
        )
        cost = (ROOT / "docs" / "tracking" / "cost.json").read_text(encoding="utf-8")
        self.assertIn('"as_of": "2026-07-11"', cost)
        self.assertRegex(
            cost,
            r'"claude-sonnet-5":\s*\{\s*"in": 2\.0,\s*"out": 10\.0,',
        )


if __name__ == "__main__":
    unittest.main()
