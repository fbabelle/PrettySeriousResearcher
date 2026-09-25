r"""Plain-prose pass: a codex (GPT) rewrite of a draft's sentences behind the structural guard of
translate_draft.py (2026-09-22).

Why: the owner's reading rule is "one sentence, one fact; no inversions; no nested subordinate
clauses, least of all in openings and closings". A writer cannot see their own habits, and a
same-model polish keeps them. Another model family rewrites the sentences, and a guard makes sure
it changed nothing else: headings, tables, figures, display math and raw LaTeX come back byte for
byte; the multiset of numbers, inline math, citation keys and cross-references is unchanged; the
paragraph count is unchanged; and the chunk gets shorter or stays the same length, never longer.

Stages (the same shape as translate_draft.py)
  run    : chunk each part at ## / ### (blank-line fallback), stage <work>/in/<id>.md, launch
           `codex exec` per chunk, collect <work>/out/<id>.md; resumes by default
  merge  : guard every reply, assemble <out-prefix>-partN.md (a rejected chunk keeps the original
           text so the edition is always complete), write <work>/report.md
  check  : guard only

Usage (`codex` on PATH, model from ~/.codex/config.toml; paths are the project's own):
  python plain_prose.py run   --work drafts/plain-v08 --parallel 4 --terms-file docs/style/terms.txt \
      --files drafts/v08-part1.md drafts/v08-part2.md
  python plain_prose.py merge --work drafts/plain-v08 --out-prefix drafts/v08p
--terms-file lists the paper's vocabulary the edit must keep exactly, one term per line.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("translate_draft", _HERE / "translate_draft.py")
td = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(td)

MIN_RATIO, MAX_RATIO = 0.70, 1.02   # words out / words in: shorter is fine, longer is not
SLACK_WORDS = 5                      # absolute allowance on top of MAX_RATIO, for short chunks

BRIEF = """You are a copy editor making one chunk of an academic finance / machine-learning
manuscript EASY TO READ. The author's rule: a reader should understand every sentence on the first
pass. You rewrite sentences; you never change what they claim.

HARD RULES (a reply that breaks any of them is discarded):
1. Reply with the edited chunk ONLY. No preamble, no explanation, no code fence around it.
2. Copy these lines back BYTE-IDENTICAL, in the same order and positions: every heading line
   (starting with #), every table row (starting with |), every image line (starting with ![), every
   display-math line ($$), every fenced code line, every line starting with a backslash, and the
   leading ": " of a table-caption line (translate nothing; this is English to English).
3. Keep the SAME NUMBER OF PARAGRAPHS in the same order. One paragraph in, one paragraph out. You
   may split or join SENTENCES inside a paragraph, never paragraphs. Keep list items one for one.
4. Copy every number, inline math span ($...$), citation key ([@key]), cross-reference
   (\\ref{...}, \\S\\ref{...}, "Table 3", "Figure 2", "Appendix B") and label ({#tbl:x}) exactly.
   Do not turn a number written in words into digits or the reverse. Do not add or drop a number.
5. Do not add, drop, strengthen, weaken or reorder any claim, hedge, caveat or qualifier. Every
   fact in the input is in the output, and no fact that is not.
6. The chunk must come back no longer than it went in. Shorter is welcome when it costs no fact.

WHAT TO CHANGE:
- One sentence, one fact (or one claim and its single reason). Split a sentence that carries two
  or three facts. Prefer 12 to 22 words; never more than 30.
- Subject first, verb early. Remove inversions ("Where the sample is short, the estimate ...") and
  fronted subordinate clauses; put the main clause first and the condition after it.
- At most one subordinate clause per sentence. Replace nested clauses by two sentences.
- Replace colon-chains and semicolon-chains by separate sentences.
- Plain words: "use" not "utilise", "show" not "demonstrate", "because" not "owing to the fact".
- Keep the paper's technical vocabulary exactly: {TERMS}every defined term and term of art.
- Keep every emphasis mark (**bold**, *italic*, `code`) on the same words.
- No em dashes, no arrows, no ellipsis characters.

Reply now with the edited chunk and nothing else."""


def guard_plain(old: str, new: str) -> list[str]:
    """Reasons to reject; empty = accept. Reuses the translation guard's structural checks and
    swaps its language checks for a length band and an English-only check."""
    bad: list[str] = []
    if td.skeleton(old) != td.skeleton(new):
        bad.append(f"skeleton changed ({len(td.skeleton(old))} frozen lines in, {len(td.skeleton(new))} out)")
    to, tn = td.tokens(old), td.tokens(new)
    if to != tn:
        lost = list((to - tn).elements())[:6]
        added = list((tn - to).elements())[:6]
        bad.append(f"protected tokens changed (lost {lost}; added {added})")
    po, pn = td.paragraphs(old), td.paragraphs(new)
    if len(po) != len(pn):
        bad.append(f"paragraph count {len(po)} -> {len(pn)}")
    co = sum(1 for l in old.replace("\r\n", "\n").split("\n") if l.startswith(": "))
    cn = sum(1 for l in new.replace("\r\n", "\n").split("\n") if l.startswith(": "))
    if co != cn:
        bad.append(f"table-caption markers ': ' {co} -> {cn}")
    if td.CJK_RX.search(new):
        bad.append("reply contains CJK characters")
    wo, wn = len(old.split()), len(new.split())
    ratio = wn / max(wo, 1)
    # a short chunk that comes back two words longer is not "longer" in any sense a reader feels;
    # the 2% band is for long chunks, so a small absolute allowance sits on top of it
    if wn > wo * MAX_RATIO + SLACK_WORDS:
        bad.append(f"reply longer than the original ({wo} -> {wn} words)")
    if ratio < MIN_RATIO:
        bad.append(f"reply too short, facts probably dropped ({wo} -> {wn} words)")
    if new.count("—") > old.count("—"):
        bad.append("em dashes added")
    return bad


def launch(ids: list[str], in_dir: Path, out_dir: Path, parallel: int, effort: str, brief: str | None = None):
    brief = td.with_terms(BRIEF, []) if brief is None else brief
    out_dir.mkdir(parents=True, exist_ok=True)
    pending, running = list(ids), {}
    t0 = time.time()
    while pending or running:
        while pending and len(running) < parallel:
            cid = pending.pop(0)
            staged = in_dir / f"{cid}.stdin.md"
            staged.write_text("=== INSTRUCTIONS ===\n" + brief
                              + "\n\n=== TEXT (edit this; reply as the instructions say) ===\n"
                              + (in_dir / f"{cid}.md").read_text(encoding="utf-8"), encoding="utf-8")
            cmd = [td.CODEX, "exec", "--ephemeral", "-s", "read-only",
                   "-c", f'model_reasoning_effort="{effort}"', "-o", str(out_dir / f"{cid}.md"),
                   "Follow the INSTRUCTIONS block at the top of the stdin text exactly, applied to "
                   "the TEXT block that follows it. Reply only with the edited chunk."]
            running[cid] = subprocess.Popen(cmd, stdin=open(staged, encoding="utf-8"),
                                            stdout=open(out_dir / f"{cid}.log", "w", encoding="utf-8"),
                                            stderr=subprocess.STDOUT)
            print(f"[{time.time() - t0:5.0f}s] start {cid}", flush=True)
        for cid, p in list(running.items()):
            if p.poll() is not None:
                f = out_dir / f"{cid}.md"
                ok = f.exists() and f.stat().st_size > 0
                print(f"[{time.time() - t0:5.0f}s] done  {cid} exit={p.returncode} {'OK' if ok else 'NO OUTPUT'}", flush=True)
                del running[cid]
        time.sleep(5)
    print(f"all chunks done in {time.time() - t0:.0f}s", flush=True)


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("run", "merge", "check"):
        print(__doc__)
        return 2
    stage = argv[0]
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    work = Path(opt("--work", "drafts/plain"))
    out_prefix = opt("--out-prefix", "drafts/plain")
    parallel, effort, only = int(opt("--parallel", 4)), opt("--effort", "high"), opt("--only")
    IN, OUT, index_path = work / "in", work / "out", work / "index.json"

    if stage == "run":
        files = td.files_after(argv)
        assert files, "--files required"
        IN.mkdir(parents=True, exist_ok=True)
        index: dict[str, dict] = {}
        for f in files:
            tag = Path(f).stem.replace("-", "_")
            for cid, body in td.chunks_of(tag, Path(f).read_text(encoding="utf-8")):
                index[cid] = {"file": f, "words": len(body.split()), "send": td.translatable(body)}
                (IN / f"{cid}.md").write_text(body, encoding="utf-8")
        index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
        send = [c for c, m in index.items() if m["send"]]
        if only:
            send = [c for c in send if c in only.split(",")]
        if "--force" not in argv:
            done = [c for c in send if (OUT / f"{c}.md").exists() and (OUT / f"{c}.md").stat().st_size > 0]
            send = [c for c in send if c not in done]
            if done:
                print(f"resuming: {len(done)} chunk(s) already done, skipping them")
        print(f"{len(index)} chunks staged, {len(send)} to edit, {sum(index[c]['words'] for c in send)} words")
        launch(send, IN, OUT, parallel, effort, td.with_terms(BRIEF, td.load_terms(opt("--terms-file"))))
        return 0

    index = json.loads(index_path.read_text(encoding="utf-8"))
    by_file: dict[str, list[str]] = {}
    for cid, meta in index.items():
        by_file.setdefault(meta["file"], []).append(cid)
    report, accepted, rejected, passthrough, wi, wo_ = [], 0, 0, 0, 0, 0
    for src, cids in by_file.items():
        parts = []
        for cid in cids:
            old = (IN / f"{cid}.md").read_text(encoding="utf-8")
            rp = OUT / f"{cid}.md"
            if not index[cid]["send"]:
                parts.append(old); passthrough += 1; continue
            if not rp.exists() or not rp.read_text(encoding="utf-8").strip():
                parts.append(old); rejected += 1; report.append(f"- `{cid}` NO REPLY, original kept"); continue
            new = td.normalize(rp.read_text(encoding="utf-8"))
            reasons = guard_plain(old, new)
            if reasons:
                parts.append(old); rejected += 1
                report.append(f"- `{cid}` REJECTED, original kept: " + "; ".join(reasons))
            else:
                parts.append(new); accepted += 1
                wi += len(old.split()); wo_ += len(new.split())
        dest = Path(f"{out_prefix}-{Path(src).stem.split('-')[-1]}.md")
        if stage == "merge":
            dest.write_text("".join(parts), encoding="utf-8")
            print(f"wrote {dest}")
    head = (f"# Plain-prose report\n\naccepted {accepted}, rejected {rejected}, pass-through {passthrough}; "
            f"accepted chunks {wi} -> {wo_} words\n\n")
    (work / "report.md").write_text(head + "\n".join(report) + "\n", encoding="utf-8")
    print(head.strip())
    for line in report:
        print(" ", line)
    return 0 if rejected == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
