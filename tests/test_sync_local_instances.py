#!/usr/bin/env python3
"""Tests for tools/sync_local_instances.py — discovery of local installs and the three-way sync that
updates them without deleting project-local skill edits. Builds a throwaway source repo with git.

Run: python tests/test_sync_local_instances.py        (stdlib unittest; needs git on PATH)
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, "tools", "sync_local_instances.py")

spec = importlib.util.spec_from_file_location("sync_local_instances", TOOL)
sync_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_mod)

V1 = "line one\nline two\nline three\nline four\nline five\nline six\nline seven\n"
V2 = V1.replace("line two", "line two, revised upstream")


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "core.autocrlf=false",
                    *args], cwd=cwd, check=True, capture_output=True)


@unittest.skipUnless(shutil.which("git"), "git not on PATH")
class Sync(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.source = self.tmp / "source"
        skills = self.source / ".claude" / "skills"
        (skills / "research-paper").mkdir(parents=True)
        (skills / "a").mkdir()
        (skills / "research-paper" / "SKILL.md").write_text("marker\n", encoding="utf-8", newline="\n")
        (skills / "a" / "SKILL.md").write_text(V1, encoding="utf-8", newline="\n")
        _git(self.source, "init", "-q")
        _git(self.source, "add", ".")
        _git(self.source, "commit", "-q", "-m", "v1")
        (skills / "a" / "SKILL.md").write_text(V2, encoding="utf-8", newline="\n")
        (skills / "b").mkdir()
        (skills / "b" / "new.md").write_text("new file\n", encoding="utf-8", newline="\n")
        _git(self.source, "add", ".")
        _git(self.source, "commit", "-q", "-m", "v2")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def project(self, name: str, a_text: str, newline: str = "\n") -> Path:
        skills = self.tmp / name / ".claude" / "skills"
        (skills / "research-paper").mkdir(parents=True)
        (skills / "a").mkdir()
        (skills / "research-paper" / "SKILL.md").write_text("marker\n", encoding="utf-8", newline=newline)
        (skills / "a" / "SKILL.md").write_text(a_text, encoding="utf-8", newline=newline)
        return skills

    def run_sync(self, skills: Path, apply: bool = True) -> dict:
        return sync_mod.sync(self.source, "HEAD", skills, apply)

    def test_pristine_copy_is_replaced_and_new_files_added(self):
        skills = self.project("p1", V1)
        report = self.run_sync(skills)
        self.assertIn(".claude/skills/a/SKILL.md", [r for r, _ in report["REPLACE"]])
        self.assertIn(".claude/skills/b/new.md", [r for r, _ in report["ADD"]])
        self.assertEqual((skills / "a" / "SKILL.md").read_text(encoding="utf-8"), V2)

    def test_local_edit_is_kept_and_reported_as_owed_upstream(self):
        skills = self.project("p2", V1 + "a lesson only this project has\n")
        report = self.run_sync(skills)
        (rel, note), = report["MERGE"]
        self.assertIn("1 project-local line(s) owed upstream", note)
        text = (skills / "a" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("line two, revised upstream", text)
        self.assertIn("a lesson only this project has", text)

    def test_conflict_leaves_the_file_untouched(self):
        local = V1.replace("line two", "line two, revised locally")
        skills = self.project("p3", local)
        report = self.run_sync(skills)
        self.assertEqual([r for r, _ in report["CONFLICT"]], [".claude/skills/a/SKILL.md"])
        self.assertEqual((skills / "a" / "SKILL.md").read_text(encoding="utf-8"), local)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sync_mod.main(["--source", str(self.source), "--rev", "HEAD", "--no-fetch",
                                            "--apply", str(self.tmp / "p3")]), 1)

    def test_project_that_extended_the_upstream_line_is_not_a_conflict(self):
        # the project already has v2's line and appended to it; v1 and v2 tie on distance, so the older base is
        # chosen and the hunk conflicts — the word-level check sees v2's words inside the project's line
        local = V2.replace("line two, revised upstream", "line two, revised upstream, plus a local clause")
        skills = self.project("p6", local)
        report = self.run_sync(skills)
        self.assertNotIn("CONFLICT", report)
        self.assertEqual((skills / "a" / "SKILL.md").read_text(encoding="utf-8"), local)

    def test_crlf_files_stay_crlf(self):
        skills = self.project("p4", V1, newline="\r\n")
        self.run_sync(skills)
        data = (skills / "a" / "SKILL.md").read_bytes()
        self.assertIn(b"line two, revised upstream\r\n", data)
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))

    def test_dry_run_writes_nothing_and_local_only_files_are_kept(self):
        skills = self.project("p5", V1)
        (skills / "a" / "local_tool.py").write_text("print('mine')\n", encoding="utf-8")
        report = self.run_sync(skills, apply=False)
        self.assertEqual((skills / "a" / "SKILL.md").read_text(encoding="utf-8"), V1)
        self.assertFalse((skills / "b").exists())
        self.assertEqual([r for r, _ in report["LOCAL-ONLY FILE"]], [str(Path("a") / "local_tool.py")])

    def test_discovery_finds_installs_but_not_the_source(self):
        p1, p2 = self.project("p1", V1), self.project("nested/p2", V1)
        found = sync_mod.find_installs([self.tmp], self.source)
        self.assertEqual(found, sorted([p1, p2]))
        self.assertEqual(sync_mod.skills_dir_of(self.tmp / "p1"), p1)


if __name__ == "__main__":
    unittest.main()
