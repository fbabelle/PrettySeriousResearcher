"""Sync every local install of the research skills to the source repo's upstream revision, keeping each
project's own (not yet upstreamed) skill edits — the safe alternative to reinstalling over an install.

Why: `install_skills.py` copies the source bundle *over* the destination, so a reinstall deletes whatever a
project's `.claude/skills/` holds alone (evolution lessons not yet upstreamed, local scripts). This tool
three-way merges instead and reports what each project still owes upstream.

Per project and per file under `.claude/skills/` at --rev:
  ADD       missing in the project                      -> copied from upstream
  OK        identical (CRLF-insensitive), or the merge changes nothing (upstream change already present)
  REPLACE   identical to an older upstream version       -> replaced by upstream (no local edits)
  MERGE     local edits present                          -> `git merge-file` with base = the upstream version
                                                            of that file (in --rev's history) closest to the project
  CONFLICT  the merge conflicts                          -> left untouched, reported, exit code 1
Files only the project has are kept. Each file's line-ending style is preserved. After the merge, a file whose
content still differs from upstream holds project-local lines: they are reported as "owed upstream" (a PR to
the source repo), never deleted.

Inputs : --rev (default origin/main; `git fetch` first unless --no-fetch), --roots to search for installs
         (default: the parent folder of the source repo), or explicit project paths; --apply to write.
Outputs: a per-project table on stdout; with --apply, files written in the projects. Commit them in projects
         that track `.claude/skills/`.
Usage  : python tools/sync_local_instances.py                    # dry run over every install found
         python tools/sync_local_instances.py --apply
         python tools/sync_local_instances.py --apply C:/Projects/my-paper
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
MARKER = Path("research-paper") / "SKILL.md"   # a skills directory is one that holds this file
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}


def git(src: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(src), *args], capture_output=True, check=True).stdout


def norm(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def line_distance(a: bytes, b: bytes) -> int:
    sm = difflib.SequenceMatcher(None, a.split(b"\n"), b.split(b"\n"), autojunk=False)
    return sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")


def find_installs(roots: list[Path], source: Path, max_depth: int = 6) -> list[Path]:
    """Skills directories (holding research-paper/SKILL.md) under `roots`, excluding the source repo's own."""
    found, own = [], (source / ".claude" / "skills").resolve()
    for root in roots:
        root = root.resolve()
        for dirpath, dirnames, _ in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and depth < max_depth]
            if (Path(dirpath) / MARKER).is_file() and Path(dirpath).resolve() != own:
                found.append(Path(dirpath))
    return sorted(set(found))


def skills_dir_of(path: Path) -> Path:
    """Accept a project root or its skills directory."""
    for cand in (path, path / ".claude" / "skills"):
        if (cand / MARKER).is_file():
            return cand
    raise FileNotFoundError(f"no installed research skills under {path}")


def upstream_versions(source: Path, rev: str, rel: str) -> list[tuple[str, bytes]]:
    seen, out = set(), []
    for commit in git(source, "rev-list", rev, "--", rel).decode().split():
        try:
            blob = norm(git(source, "show", f"{commit}:{rel}"))
        except subprocess.CalledProcessError:
            continue
        if blob not in seen:
            seen.add(blob)
            out.append((commit[:8], blob))
    return out


MARK = 15   # conflict-marker length, long enough not to collide with markdown rules


def words(lines: list[bytes]) -> list[str]:
    """Word tokens only: extending a sentence usually changes the punctuation at the join ("printed." ->
    "printed, and ..."), which must not read as a lost word."""
    return re.findall(r"\w+", b"\n".join(lines).decode("utf-8", errors="replace"))


def contains_in_order(outer: list[str], inner: list[str]) -> bool:
    it = iter(outer)
    return all(tok in it for tok in inner)


def merge3(ours: bytes, base: bytes, theirs: bytes) -> tuple[int, bytes]:
    """Three-way merge. A conflicting hunk whose upstream side is non-empty and whose words all appear, in order,
    in the project's side is resolved to the project's side (the project already carries the upstream change and
    extended it); every other conflict is counted and left marked. Returns (conflicts left, merged bytes)."""
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, data in (("ours", ours), ("base", base), ("theirs", theirs)):
            p = Path(d) / name
            p.write_bytes(data)
            paths.append(str(p))
        r = subprocess.run(["git", "merge-file", "-p", "--diff3", f"--marker-size={MARK}", *paths], capture_output=True)
    if r.returncode < 0:
        raise RuntimeError(r.stderr.decode(errors="replace"))
    if r.returncode == 0:
        return 0, r.stdout
    out, left, section, hunk = [], 0, None, {"o": [], "b": [], "t": []}
    for line in r.stdout.split(b"\n"):
        if line.startswith(b"<" * MARK):
            section, hunk = "o", {"o": [], "b": [], "t": []}
        elif section and line.startswith(b"|" * MARK):
            section = "b"
        elif section and line == b"=" * MARK:
            section = "t"
        elif section and line.startswith(b">" * MARK):
            ours_words, theirs_words = words(hunk["o"]), words(hunk["t"])
            if theirs_words and contains_in_order(ours_words, theirs_words):
                out.extend(hunk["o"])
            else:
                left += 1
                out.extend([b"<" * MARK, *hunk["o"], b"=" * MARK, *hunk["t"], b">" * MARK])
            section = None
        elif section:
            hunk[section].append(line)
        else:
            out.append(line)
    return left, b"\n".join(out)


def plan_file(source: Path, rev: str, rel: str, dst: Path) -> tuple[str, bytes | None, str]:
    """(status, content to write or None, note) for one skill file. Content is LF; the caller restores CRLF."""
    new = norm(git(source, "show", f"{rev}:{rel}"))
    if not dst.exists():
        return "ADD", new, ""
    cur = norm(dst.read_bytes())
    if cur == new:
        return "OK", None, ""
    versions = upstream_versions(source, rev, rel)
    if any(cur == v for _, v in versions):
        return "REPLACE", new, ""
    if not versions:
        return "CONFLICT", None, "no upstream history to merge against"
    # base = the closest upstream version; on a tie take the OLDER one (versions run newest first). Too old a
    # base is harmless (changes both sides share merge cleanly); too new a base hides the upstream change and
    # any conflict with it, reporting "already present" for a file that never received it.
    _, _, commit, base = min((line_distance(cur, v), -i, c, v) for i, (c, v) in enumerate(versions))
    conflicts, merged = merge3(cur, base, new)
    if conflicts:
        return "CONFLICT", None, f"base {commit}, {conflicts} conflicting hunk(s)"
    local = sorted(set(merged.split(b"\n")) - set(new.split(b"\n")) - {b""})
    note = f"base {commit}; {len(local)} project-local line(s) owed upstream" if local else f"base {commit}"
    if merged == cur:
        return "OK", None, (note + "; upstream change already present")
    return "MERGE", merged, note


def sync(source: Path, rev: str, skills_dir: Path, apply: bool) -> dict[str, list[tuple[str, str]]]:
    files = [f for f in git(source, "ls-tree", "-r", "--name-only", rev, ".claude/skills").decode().splitlines()
             if "__pycache__" not in f]
    report: dict[str, list[tuple[str, str]]] = {}
    for rel in files:
        dst = skills_dir / Path(rel).relative_to(".claude/skills")
        status, content, note = plan_file(source, rev, rel, dst)
        report.setdefault(status, []).append((rel, note))
        if apply and content is not None:
            crlf = dst.exists() and b"\r\n" in dst.read_bytes()
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(content.replace(b"\n", b"\r\n") if crlf else content)
    upstream_rel = {str(Path(f).relative_to(".claude/skills")) for f in files}
    local_only = sorted(str(p.relative_to(skills_dir)) for p in skills_dir.rglob("*")
                        if p.is_file() and "__pycache__" not in p.parts
                        and str(p.relative_to(skills_dir)) not in upstream_rel)
    report["LOCAL-ONLY FILE"] = [(f, "kept; owed upstream if general") for f in local_only]
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("projects", nargs="*", type=Path, help="project roots or skills dirs (default: search --roots)")
    ap.add_argument("--rev", default="origin/main")
    ap.add_argument("--roots", nargs="*", type=Path, default=[SOURCE.parent])
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    if not args.no_fetch and args.rev.startswith("origin/"):
        git(args.source, "fetch", "--quiet", "origin")
    installs = [skills_dir_of(p) for p in args.projects] if args.projects else find_installs(args.roots, args.source)
    print(f"source {args.source} @ {args.rev} ({git(args.source, 'rev-parse', '--short', args.rev).decode().strip()}); "
          f"{len(installs)} install(s); {'APPLY' if args.apply else 'dry run'}")
    any_conflict = False
    for skills_dir in installs:
        report = sync(args.source, args.rev, skills_dir, args.apply)
        counts = {k: len(v) for k, v in report.items() if v}
        print(f"\n=== {skills_dir}\n  {counts}")
        for status in ("ADD", "REPLACE", "MERGE", "CONFLICT", "OK", "LOCAL-ONLY FILE"):
            for rel, note in report.get(status, []):
                if status != "OK" or "owed upstream" in note:
                    print(f"  {status:15} {rel}  {note}")
        any_conflict |= bool(report.get("CONFLICT"))
    return 1 if any_conflict else 0


if __name__ == "__main__":
    sys.exit(main())
