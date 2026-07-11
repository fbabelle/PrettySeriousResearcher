#!/usr/bin/env python3
"""install_skills.py — import the research-paper skill set into an agent system.

SKILL.md is used by several coding agents, but discovery paths and support vary by
tool and version. This installer copies one portable bundle to a target-specific
path; targets not verified against primary documentation print a warning. Cursor's
older *Rules* format (`.cursor/rules/*.mdc`) is supported as a lossy translation.

Before copying anything it LINTS the skill set for absolute paths and secret/PII
patterns and refuses on a hit (override with --force) — so a shared bundle can't
leak one machine's paths or one org's secrets.

Usage (from a clone):
  python install_skills.py --target claude --dest /path/to/project
  python install_skills.py --target cursor --dest . --with-scaffold
  python install_skills.py --target cursor-rules --dest .
  python install_skills.py --target bundle --dest .
  python install_skills.py --check-only            # just run the lint

Usage (no clone — via uv; also exposed as the `research-skills` console script):
  uvx --from git+https://github.com/fbabelle/PrettySeriousResearcher \
      research-skills --target claude --dest .

Targets: claude | cursor | windsurf | copilot | codex | gemini | cline | agents
         | cursor-rules (lossy) | bundle
Claude Code and OpenAI Codex locations are verified against primary docs. For
other targets, confirm the printed path (or pass --skills-subdir to override).

Stdlib only. Python 3.10+ (Windows / macOS / Linux).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

# Two layouts: a repo clone keeps skills at .claude/skills and templates at
# docs/tracking; the built wheel (uvx/pipx) ships both under install_skills_data/.
_HERE = Path(__file__).resolve().parent
if (_HERE / ".claude" / "skills").is_dir():
    SRC_SKILLS = _HERE / ".claude" / "skills"
    SRC_TEMPLATES = _HERE / "docs" / "tracking"
else:
    SRC_SKILLS = _HERE / "install_skills_data" / "skills"
    SRC_TEMPLATES = _HERE / "install_skills_data" / "tracking"

# SKILL.md-native targets: project subdir + user-global dir. `verified` flags the
# locations confirmed against primary docs; others print a confirm note.
TARGETS = {
    "claude":   {"subdir": ".claude/skills",   "glob": "~/.claude/skills",   "verified": True},
    "cursor":   {"subdir": ".cursor/skills",   "glob": "~/.cursor/skills",   "verified": False},
    "windsurf": {"subdir": ".windsurf/skills", "glob": "~/.windsurf/skills", "verified": False},
    "copilot":  {"subdir": ".github/skills",   "glob": "~/.copilot/skills",  "verified": False},
    "codex":    {"subdir": ".agents/skills",   "glob": "~/.agents/skills",   "verified": True},
    "gemini":   {"subdir": ".gemini/skills",   "glob": "~/.gemini/skills",   "verified": False},
    "cline":    {"subdir": ".cline/skills",    "glob": "~/.cline/skills",    "verified": False},
    "agents":   {"subdir": ".agents/skills",   "glob": "~/.agents/skills",   "verified": False},
}
SPECIAL = ("cursor-rules", "bundle")
COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")

# ---- lint --------------------------------------------------------------- #
# Generic placeholders that are NOT identifying — allowed in absolute paths.
_GENERIC_SEG = {"*", "x", "user", "username", "you", "<user>", "<username>",
                "<you>", "<name>", "<home>"}
_PATH_RE = re.compile(r"/(?:home|Users)/([A-Za-z0-9._*<>-]+)")
_WINPATH_RE = re.compile(r"[A-Za-z]:\\Users\\([A-Za-z0-9._<>-]+)")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_PLACEHOLDER_DOMAINS = {"example.com", "example.org", "co.com", "foo.com",
                        "test.com", "domain.com", "email.com", "company.com"}
# Extend _ORG_WORDS with your own org-internal identifiers (codenames, hostnames)
# so the lint blocks them from ever shipping in a shared skill bundle.
_ORG_WORDS: list[str] = []
_SECRET_RES = [
    *[("org-name", re.compile(rf"\b{re.escape(w)}\b", re.I)) for w in _ORG_WORDS],
    ("atlassian", re.compile(r"\batlassian\b", re.I)),
    ("jira-token", re.compile(r"ATATT[A-Za-z0-9]")),
    ("bearer-token", re.compile(r"\bBearer\s+[A-Za-z0-9._-]{8,}")),
    ("slack-token", re.compile(r"xox[bpoas]-[A-Za-z0-9-]{6,}")),
    ("anthropic-key", re.compile(r"sk-ant-[A-Za-z0-9-]{6,}")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{12,}")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("ssh-path", re.compile(r"\.ssh/")),
    ("gpg-ref", re.compile(r"\.gpg\b")),
    ("account-id", re.compile(r"\baccountId\b")),
]


def lint(root: Path) -> list[tuple]:
    """Return findings [(file, lineno, kind, text)] for abs paths / secrets."""
    findings = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(root.parent if root.parent != root else root)
        for i, line in enumerate(text.splitlines(), 1):
            for seg in _PATH_RE.findall(line):
                if seg not in _GENERIC_SEG:
                    findings.append((rel, i, "abs-path", line.strip()[:120]))
                    break
            for seg in _WINPATH_RE.findall(line):
                if seg not in _GENERIC_SEG:
                    findings.append((rel, i, "abs-path(win)", line.strip()[:120]))
                    break
            for dom in _EMAIL_RE.findall(line):
                if dom.lower() not in _PLACEHOLDER_DOMAINS:
                    findings.append((rel, i, "email", line.strip()[:120]))
                    break
            for kind, rx in _SECRET_RES:
                if rx.search(line):
                    findings.append((rel, i, kind, line.strip()[:120]))
                    break
    return findings


# ---- frontmatter -------------------------------------------------------- #
def read_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {"name": skill_md.parent.name, "description": "", "body": text}
    fm, body = m.group(1), m.group(2)
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    return {
        "name": (name.group(1).strip() if name else skill_md.parent.name),
        "description": (desc.group(1).strip() if desc else ""),
        "body": body.lstrip("\n"),
    }


def skill_dirs() -> list[Path]:
    return sorted(d for d in SRC_SKILLS.iterdir()
                  if d.is_dir() and (d / "SKILL.md").exists())


# ---- copy modes --------------------------------------------------------- #
def copy_native(dest_skills: Path, force: bool) -> list[str]:
    names = []
    for d in skill_dirs():
        target = dest_skills / d.name
        if target.exists():
            if not force:
                print(f"  skip (exists, use --force): {target}")
                continue
            shutil.rmtree(target)
        shutil.copytree(d, target, ignore=COPY_IGNORE)
        names.append(d.name)
    return names


def install_cursor_rules(dest: Path, force: bool) -> list[str]:
    rules = dest / ".cursor" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    names = []
    for d in skill_dirs():
        fm = read_frontmatter(d / "SKILL.md")
        mdc = rules / f"{fm['name']}.mdc"
        if mdc.exists() and not force:
            print(f"  skip (exists, use --force): {mdc}")
            continue
        body = fm["body"]
        assets = [s for s in ("references", "scripts") if (d / s).is_dir()]
        if assets:
            adir = rules / f"{fm['name']}-assets"
            if adir.exists() and force:
                shutil.rmtree(adir)
            adir.mkdir(exist_ok=True)
            for s in assets:
                # adir is fresh (new, or rmtree'd under --force), so adir/s
                # never pre-exists — no dirs_exist_ok needed (Py3.7 compatible).
                shutil.copytree(d / s, adir / s, ignore=COPY_IGNORE)
            body += (f"\n\n> Supporting files (not auto-loaded by Cursor rules): "
                     f"see `.cursor/rules/{fm['name']}-assets/`.\n")
        front = (f"---\ndescription: {fm['description']}\nalwaysApply: false\n---\n\n")
        mdc.write_text(front + body, encoding="utf-8")
        names.append(fm["name"])
    return names


def install_bundle(dest: Path, force: bool) -> list[str]:
    bdir = dest / "research-skills-bundle"
    if bdir.exists() and force:
        shutil.rmtree(bdir)
    (bdir / "skills").mkdir(parents=True, exist_ok=True)
    manifest = {"name": "research-paper-skill-set", "skills": [],
                "target_paths": {t: f"{c['subdir']}/<name>/SKILL.md"
                                 for t, c in TARGETS.items()}}
    names = []
    for d in skill_dirs():
        fm = read_frontmatter(d / "SKILL.md")
        out = bdir / "skills" / d.name
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(d, out, ignore=COPY_IGNORE)
        manifest["skills"].append({"name": fm["name"],
                                   "description": fm["description"]})
        names.append(d.name)
    (bdir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    (bdir / "AGENTS.md").write_text(
        "# Research-paper skill set\n\nThis project uses a research-paper skill "
        "set (see `skills/`). Each `skills/<name>/SKILL.md` is on-demand "
        "guidance; load the relevant one per task/phase. Entry point: the "
        "`research-paper` skill. See `MANIFEST.json` for per-tool install paths.\n",
        "utf-8")
    (bdir / "README.md").write_text(
        "# research-skills-bundle\n\nNeutral bundle of the research-paper skill "
        "set. Copy `skills/<name>/` into your tool's skills directory "
        "(see `MANIFEST.json` for paths), or re-run `install_skills.py "
        "--target <tool>`.\n", "utf-8")
    return names


# ---- scaffold ----------------------------------------------------------- #
def write_if_absent(path: Path, content: str, force: bool, label: str):
    if path.exists() and not force:
        print(f"  scaffold: kept existing {label}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  scaffold: wrote {label}")


CLAUDE_MD_START = "<!-- research-paper-skill-set:start -->"
CLAUDE_MD_END = "<!-- research-paper-skill-set:end -->"
CLAUDE_MD_BLOCK = f"""{CLAUDE_MD_START}
## Research-paper skill set

This project uses the research-paper skill set in `.claude/skills/`. When the user
works on the paper — starting, resuming, asking "where are we", or any topic /
algorithm / experiment / writing task — use the **research-paper** skill as the entry
point. It routes to the phase skills (research-topic-selection, research-algo-design,
research-experiments, research-writing) and the cross-cutting gates (research-tracking,
research-code-review, research-references, research-provenance, research-finance-rigor,
research-visuals, research-venue-selection, research-mock-review, research-submission,
research-reflection, research-repo-hygiene).
Track effort/cost with `python .claude/skills/research-tracking/scripts/track.py`.
{CLAUDE_MD_END}
"""


def ensure_claude_md(dest: Path, force: bool):
    """Create or append a CLAUDE.md entry-point pointer (idempotent). CLAUDE.md is
    always loaded into context, so this makes Claude proactively route paper work
    through the research-paper skill — the recommended complement to a skill's own
    description-based auto-triggering."""
    p = dest / "CLAUDE.md"
    if p.exists():
        cur = p.read_text(encoding="utf-8")
        if CLAUDE_MD_START in cur:
            print("  scaffold: CLAUDE.md pointer already present")
            return
        with p.open("a", encoding="utf-8") as f:
            f.write("\n" + CLAUDE_MD_BLOCK)
        print("  scaffold: appended research-paper pointer to existing CLAUDE.md")
    else:
        p.write_text(CLAUDE_MD_BLOCK, encoding="utf-8")
        print("  scaffold: wrote CLAUDE.md (research-paper entry-point pointer)")


def scaffold(dest: Path, force: bool, target: str, tracking_command: str):
    print("Scaffolding per-project files (run data is reset, never copied):")
    tdir = dest / "docs" / "tracking"
    tdir.mkdir(parents=True, exist_ok=True)
    # state.json + cost.json: copy the source TEMPLATES, normalized to a clean start.
    src_state = SRC_TEMPLATES / "state.json"
    src_cost = SRC_TEMPLATES / "cost.json"
    if src_state.exists():
        st = json.loads(src_state.read_text("utf-8"))
        st["current_phase"] = "topic-selection"
        st["phase_windows"] = [{"phase": "topic-selection", "start": None, "end": None}]
        st["gates"] = {"algo_design_complete": False, "budget_status": "provisional"}
        write_if_absent(tdir / "state.json", json.dumps(st, indent=2), force, "docs/tracking/state.json")
    if src_cost.exists():
        co = json.loads(src_cost.read_text("utf-8"))
        co["status"] = "provisional"
        co["finalized_at"] = None
        co["budget"] = {"total_cap": None, "by_category": {"llm_api": None, "compute": None, "data": None}}
        co["actuals"] = [a for a in co.get("actuals", []) if a.get("_example")]
        write_if_absent(tdir / "cost.json", json.dumps(co, indent=2), force, "docs/tracking/cost.json (rate-card kept, spend reset)")
    # run-data files are intentionally NOT created — track.py regenerates them.
    write_if_absent(dest / "docs" / "changelogs.md",
                    "# Changelog\n\nAppend-only. Dated what+why entries (feature|fix|decision|reflection).\n",
                    force, "docs/changelogs.md")
    write_if_absent(dest / "memory.md",
                    "# User memory (UNTRACKED — not committed)\n\n## Summary of the user\n\n_TBD_\n\n---\n\n## Specific observations\n\n_None yet._\n",
                    force, "memory.md (untracked)")
    write_if_absent(dest / "architecture.md",
                    "# Architecture\n\nDesign, workflow, and project charter. The charter (domain, direction, scope, success criteria) is filled in during Phase 1 by `research-topic-selection`.\n",
                    force, "architecture.md")
    write_if_absent(dest / "README.md",
                    "# <Your paper project>\n\nThis project uses the research-paper skill set. "
                    "Start by invoking the **research-paper** skill. Track experiment cost "
                    f"and, where supported, agent effort with `{tracking_command}`.\n\n"
                    "_This is the per-project quickstart. The skill set's own documentation lives with the skill set, not here._\n",
                    force, "README.md (project quickstart stub)")
    if target == "claude":
        ensure_claude_md(dest, force)
    gi = dest / ".gitignore"
    needed = ["memory.md", "docs/tracking/.session", "drafts/_archive/",
              ".claude/settings.local.json", ".venv/", "__pycache__/", "data/"]
    existing = gi.read_text("utf-8") if gi.exists() else ""
    add = [e for e in needed if e not in existing]
    if add:
        with gi.open("a", encoding="utf-8") as f:
            f.write(("\n# research skill set\n" if existing else "") + "\n".join(add) + "\n")
        print(f"  scaffold: added {len(add)} .gitignore entries")


def tracking_script_path(target: str, where: Path) -> Path:
    """Where research-tracking's track.py actually lands for each install mode.

    Native targets copy the skill dir as-is; `bundle` nests skills under a
    skills/ subdir; `cursor-rules` translates lossily and moves scripts into
    a <name>-assets/ sibling of the .mdc rule files.
    """
    if target == "bundle":
        return where / "skills" / "research-tracking" / "scripts" / "track.py"
    if target == "cursor-rules":
        return where / "research-tracking-assets" / "scripts" / "track.py"
    return where / "research-tracking" / "scripts" / "track.py"


# ---- main --------------------------------------------------------------- #
def main() -> int:
    # Legacy Windows consoles / redirected pipes may not be UTF-8; degrade the
    # few non-ASCII glyphs ('→') instead of crashing with UnicodeEncodeError.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", choices=list(TARGETS) + list(SPECIAL))
    ap.add_argument("--dest", default=os.getcwd(), help="target project root (default: cwd)")
    ap.add_argument("--global", dest="is_global", action="store_true",
                    help="install to the target's user-global skills dir")
    ap.add_argument("--skills-subdir", default=None,
                    help="override the project skills subdir (e.g. .agents/skills)")
    ap.add_argument("--with-scaffold", action="store_true",
                    help="also lay down per-project tracking templates + stubs (run data reset)")
    ap.add_argument("--check-only", action="store_true", help="run the lint and exit")
    ap.add_argument("--force", action="store_true", help="overwrite existing files / bypass lint refusal")
    args = ap.parse_args()

    if not SRC_SKILLS.is_dir():
        print(f"ERROR: skills not found at {SRC_SKILLS}", file=sys.stderr)
        return 2

    # ---- lint (always) ----
    findings = lint(SRC_SKILLS)
    if findings:
        print(f"LINT: {len(findings)} potential issue(s) in the skill set:", file=sys.stderr)
        for rel, ln, kind, txt in findings:
            print(f"  {rel}:{ln}  [{kind}]  {txt}", file=sys.stderr)
    else:
        print("LINT: clean — no absolute paths or secrets in the skill set.")
    if args.check_only:
        return 1 if findings else 0
    if findings and not args.force:
        print("Refusing to install with lint findings. Fix them, or re-run with --force.", file=sys.stderr)
        return 1

    if not args.target:
        print("ERROR: --target is required (or use --check-only).", file=sys.stderr)
        return 2

    dest = Path(args.dest).expanduser().resolve()
    print(f"\nInstalling research-paper skill set → target '{args.target}', dest {dest}")

    skills_dir_created = False  # whether a brand-new skills dir was made (restart trigger)
    if args.target == "bundle":
        names = install_bundle(dest, args.force)
        where = dest / "research-skills-bundle"
    elif args.target == "cursor-rules":
        print("  note: Cursor Rules are lossy — scripts/progressive-disclosure don't translate.")
        names = install_cursor_rules(dest, args.force)
        where = dest / ".cursor" / "rules"
    else:
        cfg = TARGETS[args.target]
        if args.skills_subdir:
            dest_skills = dest / args.skills_subdir
        elif args.is_global:
            dest_skills = Path(cfg["glob"]).expanduser()
        else:
            dest_skills = dest / cfg["subdir"]
        skills_dir_created = not dest_skills.exists()
        dest_skills.mkdir(parents=True, exist_ok=True)
        names = copy_native(dest_skills, args.force)
        where = dest_skills
        if not cfg["verified"]:
            print(f"  note: confirm your '{args.target}' version reads SKILL.md from "
                  f"{cfg['subdir']}/ (override with --skills-subdir if not).")

    tracking_script = tracking_script_path(args.target, where)
    try:
        tracking_display = tracking_script.relative_to(dest).as_posix()
    except ValueError:
        tracking_display = "<installed-skills-dir>/research-tracking/scripts/track.py"
    tracking_command = f"python {tracking_display}"

    if args.with_scaffold:
        scaffold(dest, args.force, args.target, tracking_command)

    print(f"\nInstalled {len(names)} skill(s) → {where}")
    if names:
        print("  " + ", ".join(names))

    print("\nNext steps:")
    if args.target == "claude":
        # Claude Code: a NEW top-level .claude/skills/ is only scanned at startup;
        # project skills also require accepting the workspace-trust prompt.
        if skills_dir_created:
            print("  1. RESTART Claude Code in the target project — a newly-created")
            print("     .claude/skills/ directory is only picked up at session startup")
            print("     (skills added to an already-existing .claude/skills/ load live).")
        else:
            print("  1. Claude Code auto-loads skills added to an existing .claude/skills/ (no restart).")
        print("  2. Accept the workspace-trust prompt — project skills activate only in a trusted folder.")
        print("  3. Run /skills to confirm they're listed (use /doctor if any are missing/!shortened).")
        if not args.with_scaffold:
            print("  4. For PROACTIVE use without being asked, add a CLAUDE.md pointer:")
            print("       python install_skills.py --target claude --dest <proj> --with-scaffold")
            print("     (CLAUDE.md is always in context, so Claude routes paper work to research-paper).")
        else:
            print("  4. The scaffolded CLAUDE.md makes Claude route paper work to research-paper proactively.")
        print('  5. Then just say e.g. "let\'s work on the paper" — research-paper triggers on the match.')
    else:
        print(f"  1. Confirm your '{args.target}' agent reads skills from {where} (restart it if needed).")
        print("  2. Use the 'research-paper' skill as the entry point for paper work.")
    print(f"  Effort/cost anytime: {tracking_command}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
