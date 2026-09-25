r"""Translate a draft into Chinese with a codex (GPT) pass behind a structural guard (2026-09-19).

Purpose: produce a Chinese edition whose STRUCTURE and SEMANTICS correspond one-to-one with the
English source, so the owner can review it and a later back-translation diffs cleanly against the
original. The translation itself is done by another model family (`codex exec`, gpt-5.x), never by
the calling agent: a same-model round trip cannot expose the source's own blind spots.

What is frozen (must come back byte-identical) vs translated:
  frozen     : headings (so `{#sec:...}` anchors and section order survive), table rows, fenced
               code, display math, figure/image lines, raw LaTeX lines
  translated : prose paragraphs, list items, block quotes, table/figure caption paragraphs
  kept as-is inside prose: numbers, inline math, [@citation] keys, \ref{}/§N cross-references, and
               the English technical vocabulary (the terms listed with --terms-file, and any other term of art)

Stages
  run    : chunk each file at "## " (and "### " when a section exceeds MAX_WORDS), stage
           <work>/in/<id>.md, launch `codex exec` per chunk (PARALLEL at a time), collect
           <work>/out/<id>.md
  merge  : run the guard on every reply, assemble the accepted ones into <out-prefix>-partN.md,
           and list every rejected chunk (a rejected chunk keeps the ENGLISH original, so the
           edition is always complete and never silently half-translated)
  check  : re-run the guard on an already-merged edition

Inputs : --files       the English part files (markdown master, not the generated .tex/.pdf)
         --terms-file  the paper's terms of art kept in English, one per line (# comments allowed)
Outputs: <work>/index.json, <work>/in|out/, the merged Chinese parts, <work>/report.md

Usage (`codex` on PATH, model from ~/.codex/config.toml; paths are the project's own):
  python translate_draft.py run   --work drafts/zh-v06 --parallel 3 --terms-file docs/style/terms.txt \
      --files drafts/v06-part1.md drafts/v06-part2.md
  python translate_draft.py merge --work drafts/zh-v06 --out-prefix drafts/v06-zh
  python translate_draft.py check --work drafts/zh-v06 --out-prefix drafts/v06-zh
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

CODEX = shutil.which("codex") or "codex"
MAX_WORDS = 1100          # a chunk the guard can still check line by line
CJK_RX = re.compile(r"[一-鿿]")

BRIEF = """You are translating one chunk of an academic finance/machine-learning manuscript from
English into SIMPLIFIED CHINESE, for the author's own review. The author will later translate your
Chinese back into English, so a faithful, structure-preserving rendering matters far more than
elegance.

HARD RULES (a reply that breaks any of them is discarded):
1. Reply with the translated chunk ONLY. No preamble, no explanation, no code fence around it.
2. Copy these lines back BYTE-IDENTICAL, in the same order and the same positions: every heading
   line (starting with #), every table row (starting with |), every image/figure line (starting
   with ![), every display-math line ($$), every fenced code line, and every line starting with a
   backslash. Do not translate them. Do not renumber them.
3. Keep the SAME NUMBER OF PARAGRAPHS in the same order. One English paragraph becomes exactly one
   Chinese paragraph. Never merge, split, reorder, add or drop a paragraph. Keep list items as list
   items, one for one, with their original markers.
4. Copy every number, inline math span ($...$), citation key ([@key]), cross-reference
   (\\ref{...}, section signs, "Table 3", "Figure 2", "Appendix B") and label ({#tbl:x}) exactly as
   they appear. Never convert units, never re-format a decimal, never renumber anything.
5. KEEP THE TECHNICAL VOCABULARY IN ENGLISH, inline, unchanged: {TERMS}any established term of
   art, model name, dataset name or statistic name. Translate the prose AROUND them. Do not invent Chinese
   coinages for them and do not add a Chinese gloss in brackets.
6. Preserve emphasis markup exactly where it sits (**bold**, *italic*, `code`).
6b. A line that begins with a COLON AND A SPACE (": ") is a table caption, and that ": " is
   structural markup, not punctuation. Keep the leading ": " and the trailing label ({#tbl:x})
   byte-identical and translate only the words between them. A caption that loses its ": " detaches
   the table from its number and breaks every cross-reference to it.
7. Translate meaning, not word order: write natural academic Chinese, but do not soften, strengthen,
   summarise or omit any claim, hedge or caveat. Every qualifier in the English must survive.

Reply now with the translated chunk and nothing else."""


def load_terms(path: str | None) -> list[str]:
    """The project's terms of art, one per non-empty, non-# line; none when no file is given."""
    if not path:
        return []
    return [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def with_terms(brief: str, terms: list[str]) -> str:
    """Fill the brief's {TERMS} slot: the listed terms, then the generic clause that follows the slot."""
    return brief.replace("{TERMS}", ", ".join(terms) + ", and " if terms else "")


def files_after(argv: list[str], flag: str = "--files") -> list[str]:
    """The values after `flag` up to the next option (an option's value is never taken for a file)."""
    if flag not in argv:
        return []
    out = []
    for a in argv[argv.index(flag) + 1:]:
        if a.startswith("--"):
            break
        out.append(a)
    return out


def slug(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", h.lstrip("# ").lower()).strip("-")[:40]


def _split_on_blocks(body: str):
    """Last-resort split of an oversized run of text at blank lines. A section with no level-3
    headings (a long appendix of tables and commentary) otherwise arrives as one 4k-word chunk,
    which the model silently abridges and the guard can no longer check line by line."""
    blocks = re.split(r"(\n\s*\n)", body)
    cur, count = [], 0
    for i in range(0, len(blocks), 2):
        block = blocks[i]
        sep = blocks[i + 1] if i + 1 < len(blocks) else ""
        w = len(block.split())
        if cur and count + w > MAX_WORDS:
            yield "".join(cur)
            cur, count = [], 0
        cur.append(block + sep)
        count += w
    if "".join(cur).strip():
        yield "".join(cur)


def chunks_of(tag: str, text: str):
    """Yield (chunk_id, body). Chunked at level-1/2 headings; a section past MAX_WORDS is split
    further at its level-3 headings, and any piece still oversized is split at blank lines."""
    text = text.replace("\r\n", "\n")
    heads = [(m.start(), m.group(0)) for m in re.finditer(r"^#{1,2} .*$", text, flags=re.M)]
    if not heads or heads[0][0] > 0:
        heads.insert(0, (0, "## (front matter)"))
    heads.append((len(text), "END"))
    n = 0

    def emit(label: str, piece: str):
        nonlocal n
        if not piece.strip():
            return
        if len(piece.split()) <= MAX_WORDS:
            n += 1
            yield f"{tag}_{n:02d}_{label}", piece
            return
        for k, sub in enumerate(_split_on_blocks(piece), start=1):
            n += 1
            yield f"{tag}_{n:02d}_{label}_p{k}", sub

    for (s, h), (e, _) in zip(heads, heads[1:]):
        body = text[s:e]
        if not body.strip():
            continue
        if len(body.split()) > MAX_WORDS:
            subs = [(m.start(), m.group(0)) for m in re.finditer(r"^### .*$", body, flags=re.M)]
            subs.append((len(body), "END"))
            yield from emit(f"{slug(h)}_intro", body[: subs[0][0]])
            for (ss, sh), (se, _) in zip(subs, subs[1:]):
                yield from emit(slug(sh), body[ss:se])
        else:
            yield from emit(slug(h), body)


def skeleton(s: str) -> list[str]:
    """Lines that must come back byte-identical: headings, table rows, images, display math, fenced
    code (fences and contents) and raw LaTeX command lines."""
    keep, in_code = [], False
    for ln in s.replace("\r\n", "\n").split("\n"):
        if ln.startswith("```"):
            in_code = not in_code
            keep.append(ln)
        elif in_code or ln.startswith(("#", "|", "![", "$$", "\\")):
            keep.append(ln)
    return keep


RANGE_DASH_RX = re.compile(r"(?<=\d)\s*(?:--|[-–—−])\s*(?=\d)")


def tokens(s: str) -> Counter:
    """Everything a translation may never change: numbers, math, citation keys, cross-references.

    Two dashes here are not minus signs, and a Chinese rendering that drops them must not read as
    having lost a number: a dash BETWEEN DIGITS opens an en-dash range ("2016--2026", "7--17"),
    which is blanked before the scan, and a dash AFTER A WORD joins a compound ("mid-2026",
    "post-2008"), so a sign only counts when nothing word-like precedes it."""
    return Counter(
        re.findall(r"(?:(?<!\w)[+\-−])?\d+(?:[.,]\d+)*%?(?!\w|\.\d)", RANGE_DASH_RX.sub(" ", s))
        + re.findall(r"\$\$.*?\$\$|\$[^$\n]+\$", s, flags=re.S)
        + re.findall(r"\[@[^\]]+\]|\\(?:S?ref|eqref|cref|Cref|autoref)\{[^}]*\}|\{#[^}\s]+", s)
        + re.findall(r"§\d+(?:\.\d+)*|Table [A-Z]?\d+|Figure [A-Z]?\d+|Appendix [A-Z]|\bRQ\d", s)
    )


def paragraphs(s: str) -> list[str]:
    return [b for b in re.split(r"\n\s*\n", s.replace("\r\n", "\n").strip()) if b.strip()]


def normalize(reply: str) -> str:
    reply = reply.replace("\r\n", "\n").strip("\n")
    m = re.fullmatch(r"```(?:markdown|md)?\n(.*)\n```", reply, flags=re.S)
    return (m.group(1) if m else reply) + "\n\n"


def translatable(body: str) -> bool:
    """A chunk with no prose (a pure table block, a lone heading) is passed through untouched."""
    frozen = set(skeleton(body))
    prose = [ln for ln in body.replace("\r\n", "\n").split("\n") if ln.strip() and ln not in frozen]
    return sum(len(ln.split()) for ln in prose) >= 15


PLAIN_INT_RX = re.compile(r"^\d{1,4}$")


def guard(old: str, new: str) -> tuple[list[str], list[str]]:
    """Return (reasons to reject, warnings to report). An empty reject list means accept.

    Losing a protected token, or changing any math span, citation key or cross-reference, can
    falsify a claim, so those are hard rejections. A reply that merely GAINS a bare integer
    cannot: English academic prose spells small quantities as words ("twenty groups of five
    seeds") and Chinese writes them as digits, which is a faithful rendering and the single
    largest source of false rejections. Those are reported, not rejected."""
    bad: list[str] = []
    warn: list[str] = []
    if skeleton(old) != skeleton(new):
        o, n = skeleton(old), skeleton(new)
        bad.append(f"skeleton changed ({len(o)} frozen lines in, {len(n)} out)")
    to, tn = tokens(old), tokens(new)
    if to != tn:
        lost = list((to - tn).elements())
        added = list((tn - to).elements())
        soft = [a for a in added if PLAIN_INT_RX.match(a)]
        hard_added = [a for a in added if a not in soft]
        if lost or hard_added:
            bad.append(f"protected tokens changed (lost {lost[:6]}; added {hard_added[:6]})")
        if soft:
            warn.append(f"gained bare integers {sorted(set(soft))[:8]} "
                        f"(English number-words rendered as digits — verify by eye)")
    po, pn = paragraphs(old), paragraphs(new)
    if len(po) != len(pn):
        bad.append(f"paragraph count {len(po)} -> {len(pn)}")
    # pandoc reads a line opening with ": " as the caption of the table above it. The marker is
    # structural, so a translation that drops it detaches the table from its number: the table
    # stays a longtable, the float rewrite no longer matches it, and the build dies on \endhead.
    co = len([l for l in old.replace("\r\n", "\n").split("\n") if l.startswith(": ")])
    cn = len([l for l in new.replace("\r\n", "\n").split("\n") if l.startswith(": ")])
    if co != cn:
        bad.append(f"table-caption markers ': ' {co} -> {cn}")
    if not CJK_RX.search(new):
        bad.append("reply contains no Chinese")
    else:
        frozen = set(skeleton(new))
        prose = "\n".join(ln for ln in new.split("\n") if ln not in frozen)
        latin = len(re.findall(r"[A-Za-z]{4,}", prose))
        cjk = len(CJK_RX.findall(prose))
        if cjk and latin > cjk:          # technical terms stay English, but not whole sentences
            bad.append(f"looks untranslated (latin words {latin} vs cjk chars {cjk})")
    return bad, warn


def launch(ids: list[str], in_dir: Path, out_dir: Path, parallel: int, effort: str, brief: str | None = None):
    brief = with_terms(BRIEF, []) if brief is None else brief
    out_dir.mkdir(parents=True, exist_ok=True)
    pending, running = list(ids), {}
    t0 = time.time()
    while pending or running:
        while pending and len(running) < parallel:
            cid = pending.pop(0)
            # The full brief travels in stdin: a multi-paragraph argv prompt reaches the model
            # truncated at its first blank line on the Windows codex shim.
            staged = in_dir / f"{cid}.stdin.md"
            staged.write_text(
                "=== INSTRUCTIONS ===\n" + brief
                + "\n\n=== TEXT (translate this; reply as the instructions say) ===\n"
                + (in_dir / f"{cid}.md").read_text(encoding="utf-8"),
                encoding="utf-8")
            cmd = [CODEX, "exec", "--ephemeral", "-s", "read-only",
                   "-c", f'model_reasoning_effort="{effort}"',
                   "-o", str(out_dir / f"{cid}.md"),
                   "Follow the INSTRUCTIONS block at the top of the stdin text exactly, applied to "
                   "the TEXT block that follows it. Reply only with the translated chunk."]
            running[cid] = subprocess.Popen(
                cmd, stdin=open(staged, encoding="utf-8"),
                stdout=open(out_dir / f"{cid}.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT)
            print(f"[{time.time() - t0:5.0f}s] start {cid}", flush=True)
        for cid, p in list(running.items()):
            if p.poll() is not None:
                f = out_dir / f"{cid}.md"
                ok = f.exists() and f.stat().st_size > 0
                print(f"[{time.time() - t0:5.0f}s] done  {cid} exit={p.returncode} "
                      f"{'OK' if ok else 'NO OUTPUT'}", flush=True)
                del running[cid]
        time.sleep(5)
    print(f"all chunks done in {time.time() - t0:.0f}s", flush=True)


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("run", "merge", "check"):
        print(__doc__)
        return 2
    stage = argv[0]
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    work = Path(opt("--work", "drafts/zh"))
    out_prefix = opt("--out-prefix", "drafts/zh")
    parallel, effort = int(opt("--parallel", 3)), opt("--effort", "high")
    only = opt("--only")
    IN, OUT = work / "in", work / "out"
    index_path = work / "index.json"

    if stage == "run":
        files = files_after(argv)
        assert files, "--files required"
        IN.mkdir(parents=True, exist_ok=True)
        index: dict[str, dict] = {}
        for f in files:
            tag = Path(f).stem.replace("-", "_")
            text = Path(f).read_text(encoding="utf-8")
            for cid, body in chunks_of(tag, text):
                index[cid] = {"file": f, "words": len(body.split()),
                              "send": translatable(body)}
                (IN / f"{cid}.md").write_text(body, encoding="utf-8")
        index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
        send = [c for c, m in index.items() if m["send"]]
        if only:
            send = [c for c in send if c in only.split(",")]
        skipped = len(index) - len([c for c, m in index.items() if m["send"]])
        if "--force" not in argv:
            # resume: a chunk that already came back is never paid for twice
            done = [c for c in send if (OUT / f"{c}.md").exists()
                    and (OUT / f"{c}.md").stat().st_size > 0]
            send = [c for c in send if c not in done]
            if done:
                print(f"resuming: {len(done)} chunk(s) already translated, skipping them")
        print(f"{len(index)} chunks staged, {len(send)} to translate, {skipped} pass-through "
              f"(no prose), {sum(index[c]['words'] for c in send)} words")
        launch(send, IN, OUT, parallel, effort, with_terms(BRIEF, load_terms(opt("--terms-file"))))
        return 0

    index = json.loads(index_path.read_text(encoding="utf-8"))
    by_file: dict[str, list[str]] = {}
    for cid, meta in index.items():
        by_file.setdefault(meta["file"], []).append(cid)

    report, warned, accepted, rejected, passthrough = [], [], 0, 0, 0
    for src, cids in by_file.items():
        parts = []
        for cid in cids:
            old = (IN / f"{cid}.md").read_text(encoding="utf-8")
            reply_path = OUT / f"{cid}.md"
            if not index[cid]["send"]:
                parts.append(old); passthrough += 1; continue
            if not reply_path.exists() or not reply_path.read_text(encoding="utf-8").strip():
                parts.append(old); rejected += 1
                report.append(f"- `{cid}` — NO REPLY, English kept"); continue
            new = normalize(reply_path.read_text(encoding="utf-8"))
            reasons, warnings = guard(old, new)
            if reasons:
                parts.append(old); rejected += 1
                report.append(f"- `{cid}` — REJECTED, English kept: " + "; ".join(reasons))
            else:
                parts.append(new); accepted += 1
                warned += [f"- `{cid}` — accepted with a warning: {w}" for w in warnings]
        dest = Path(f"{out_prefix}-{Path(src).stem.split('-')[-1]}.md")
        if stage == "merge":
            dest.write_text("".join(parts), encoding="utf-8")
            print(f"wrote {dest} ({len(''.join(parts).split())} words)")

    head = (f"# Translation report\n\naccepted {accepted}, rejected {rejected}, "
            f"pass-through {passthrough}, warnings {len(warned)}\n\n")
    body = "\n".join(report) + (
        "\n\n## Warnings (accepted; check by eye)\n" + "\n".join(warned) if warned else "")
    (work / "report.md").write_text(head + body + "\n", encoding="utf-8")
    print(head.strip())
    for line in report + warned:
        print(" ", line)
    return 0 if rejected == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
