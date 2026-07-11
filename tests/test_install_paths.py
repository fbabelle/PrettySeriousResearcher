"""Tracking-hint contract for install_skills.py: the post-install tracking
command must point at a file the chosen install mode actually created.

Each test runs a real install mode into a temp dir, then asserts that
tracking_script_path() resolves to an existing track.py for that mode
(native copy, lossy cursor-rules translation, and the nested bundle).

Run: uv run pytest tests/test_install_paths.py
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import install_skills


class TrackingScriptPath(unittest.TestCase):
    def test_native_copy_hint_exists(self):
        with tempfile.TemporaryDirectory() as td:
            dest_skills = Path(td) / ".claude" / "skills"
            dest_skills.mkdir(parents=True)
            install_skills.copy_native(dest_skills, force=False)
            hint = install_skills.tracking_script_path("claude", dest_skills)
            self.assertTrue(hint.is_file(), hint)

    def test_cursor_rules_hint_exists(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td)
            install_skills.install_cursor_rules(dest, force=False)
            where = dest / ".cursor" / "rules"
            hint = install_skills.tracking_script_path("cursor-rules", where)
            self.assertTrue(hint.is_file(), hint)

    def test_bundle_hint_exists(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td)
            install_skills.install_bundle(dest, force=False)
            where = dest / "research-skills-bundle"
            hint = install_skills.tracking_script_path("bundle", where)
            self.assertTrue(hint.is_file(), hint)


if __name__ == "__main__":
    unittest.main()
