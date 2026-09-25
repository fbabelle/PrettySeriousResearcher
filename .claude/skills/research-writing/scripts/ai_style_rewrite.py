"""De-style a manuscript: send each section to Codex with a "remove machine-writing habits, change no
meaning" brief, guard the replies structurally, diff them for a human meaning review, then apply.

Targets (measured by scripts/ai_style_scan.py): em dashes used as an all-purpose joint, semicolon
chains, arrows / ellipsis characters in running prose, stock LLM vocabulary and sentence openers.
Everything factual is frozen: headings, table rows, figure lines, code, math, every numeral, every
citation and cross-reference, every hedge, defined terms, bold/italic marks, paragraph breaks.

Stages (a work directory keeps the state so a run is resumable and reviewable):
  run    : chunk each file at "## " (and "### " when a section exceeds MAX_WORDS), write <work>/in/<id>.md,
           launch `codex exec` per chunk (PARALLEL at a time), capture replies in <work>/out/<id>.md
  merge  : guard every reply (skeleton + token multisets + word-count band + style counts must drop),
           write word-level diffs to <work>/diff/<id>.diff, print a verdict table
  review : send (ORIGINAL, REVISED) pairs to Codex as an independent meaning reviewer; findings in
           <work>/review/<id>.md (leads for the human review, not verdicts)
  apply  : replace each guard-passing chunk in its source file (exact, unique match)

Usage (`codex` on PATH, model from ~/.codex/config.toml; paths are the project's own):
  python ai_style_rewrite.py run    --work drafts/destyle --files drafts/<paper>.md drafts/<supplement>.md
  python ai_style_rewrite.py merge  --work drafts/destyle
  python ai_style_rewrite.py review --work drafts/destyle
  python ai_style_rewrite.py apply  --work drafts/destyle
Options: --parallel N (default 6), --only <id-substring>, --effort high|xhigh (default high), --force (re-run
existing replies), --pass 1|2, --terms-file F (the paper's defined names, one per line, frozen verbatim by the
brief), --skip-if-contains TEXT (repeatable; a chunk holding TEXT is never sent, e.g. a notice asserted on
verbatim downstream). Chunk ids are <file-tag>_<nn>_<heading-slug>; the index is <work>/index.json.
"""
from __future__ import annotations

import difflib
import json
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_style_scan import BAN_WORDS, CONNECTIVE_OPENERS, WATCH_WORDS, scan_text  # noqa: E402

CODEX = shutil.which("codex") or "codex"
MAX_WORDS = 1300
SKIP_HEADINGS = ("## References", "## Abbreviations")
STYLE_KEYS = ("em_dash", "semicolon", "arrow_prose", "ellipsis_char", "ban_words", "not_only", "connective_opener")

PROMPT = """You are copy-editing ONE section of a finance/AI research paper (markdown, in the <stdin> block). The text is final in meaning and already correct. Your ONLY job is to remove typographic and phrasing habits that make prose read as machine-written, while changing nothing else. Work sentence by sentence; a sentence with none of the habits below is returned EXACTLY as it is.

HABITS TO REMOVE
1. Em dashes ("—", " — ", "--"). The section uses them as an all-purpose joint. Recast each one so that at most one em dash per ~400 words remains and no sentence keeps two. Pick the joint the sentence actually means: a comma (or a pair of commas) for a light aside; parentheses for a true parenthetical; a colon when the second part explains or expands the first; a full stop and a new sentence when the second part is an independent clause; "that is", "namely", "because", "so", "which", "while" when the joint expresses that relation. Never drop the content of the aside; never merge it into a vaguer sentence.
2. Semicolon chains. Where the two halves are independent statements, make two sentences. Keep a semicolon only when it separates list items that themselves contain commas. Semicolons inside a citation group such as (Smith 2021; Lee 2023) are bibliographic and must not be touched.
3. Arrows in running prose (→ ⇒ ⟵ ↔ ⟶): write the relation in words: "from 0.37 to 0.67", "2025-06-16 to 2026-06-12", "A versus B", "a first-stage failure, which ...". A chain of stage names joined by arrows (gather→analyze→decide→execute→reflect) becomes the same names joined by hyphens (gather-analyze-decide-execute-reflect). EXCEPTION: a legend that defines symbols used in a table ("✓ = supported, — = absent") stays verbatim, and a symbol that names a table footnote (✦, †, ‡) stays.
4. The ellipsis character "…": in a numeric range write "from a to b" (or "a to b"); inside quoted machine output (a JSON fragment, a log line) leave it.
5. Stock vocabulary, when it carries no technical meaning: actionable, underscores, showcases (verb), leverages (meaning "uses"), landscape, notably, additionally, striking, hence, "not just X but Y", and sentence openers Moreover / Furthermore / Additionally / Notably / Importantly / Crucially / "Together, these". Replace with a plain equivalent that keeps the exact meaning. Do NOT touch technical senses: "leverage", "elevated" (as in "VIX is elevated") and "robust"/"robustness" are finance and statistics terms, and any term listed under D is a defined name.

HARD CONSTRAINTS (violating any one ruins the work)
A. Byte-identical: every heading line (# ...), every markdown table row (lines starting with |), every figure line (![](...)), every fenced code block, every display formula ($$...$$) and every inline formula ($...$).
B. Every numeral, percentage, sign, seed count, date, parameter and unit exactly as written, and each stays in the sentence that carries it. Every citation "(Author Year)" and every cross-reference (§7.3, Table 5, Figure 9, Appendix D, RQ4, F2, D5, "Supplementary Material (§S-I.2)") exactly, attached to the same statement.
C. Every hedge and scope qualifier ("to our knowledge", "on this benchmark and period", "descriptive", "in this sample", "we argue", ...) stays. Never strengthen, weaken, generalize, add, remove or reorder a claim.
D. Defined names and technical terms stay verbatim ({TERMS}). Bold and italic marks stay where they are (they mark defined terms, finding labels F1..F5 / RQ1..RQ7, and emphasized contrasts); a bold run-in label at the start of a paragraph stays as it is.
E. Keep list structure and paragraph breaks; keep the word count within ±5% of the input; do not compress, elaborate, or "improve" anything outside habits 1-5.

OUTPUT: only the full revised section in markdown, same first heading line, no preamble, no commentary, no code fence around the whole reply, no notes on what changed."""

PROMPT2 = """You are copy-editing ONE section of a finance/AI research paper (markdown, in the <stdin> block). The text is final in meaning and already correct. A first pass has removed most em dashes. Your ONLY job now is the two habits below; every sentence without them is returned EXACTLY as it is.

1. Semicolons. The section still joins independent statements with semicolons far more often than a human author would. Turn each such semicolon into a full stop and a new sentence (capitalize the next word; add "and", "but", "so" or "because" only when the second clause cannot stand alone without it). Keep a semicolon ONLY (a) between list items that themselves contain commas, or (b) inside a citation group such as (Smith 2021; Lee 2023), which is bibliographic and must not be touched. The number of semicolons outside citation groups must fall to at most one per 250 words.
2. Any remaining em dash ("—", " — ", "--"): recast as a comma pair, parentheses, a colon, or a new sentence, whichever the sentence means. None should remain unless removing it would force a rewrite of the sentence.

HARD CONSTRAINTS (violating any one ruins the work)
A. Byte-identical: every heading line (# ...), every markdown table row (lines starting with |), every figure line (![](...)), every fenced code block, every display formula ($$...$$) and every inline formula ($...$).
B. Every numeral, percentage, sign, seed count, date, parameter and unit exactly as written, in the sentence that carries it. Every citation "(Author Year)" and every cross-reference (§7.3, Table 5, Figure 9, Appendix D, RQ4, F2, D5, "Supplementary Material (§S-I.2)") exactly, attached to the same statement.
C. Every hedge and scope qualifier stays. Never strengthen, weaken, generalize, add, remove or reorder a claim. Do not change any word other than the ones needed to split or rejoin the clause.
D. Defined names and technical terms stay verbatim ({TERMS}). Bold and italic marks stay exactly where they are; a bold run-in label at the start of a paragraph stays as it is.
E. Keep list structure and paragraph breaks; keep the word count within ±3% of the input.

OUTPUT: only the full revised section in markdown, same first heading line, no preamble, no commentary, no code fence around the whole reply, no notes on what changed."""
PROMPTS = {1: PROMPT, 2: PROMPT2}

REVIEW_PROMPT = """You are an independent meaning reviewer. The <stdin> block contains ORIGINAL and REVISED versions of one section of a research paper. REVISED was produced by a copy-edit that was only allowed to change punctuation habits (em dashes, semicolons, arrows, ellipses) and a short list of stock words. List EVERY place where REVISED differs from ORIGINAL in meaning, however slightly: a claim strengthened, weakened, generalized or narrowed; a hedge or scope qualifier dropped or added; a causal or temporal relation changed (e.g. an aside turned into a cause, a contrast turned into a sequence); a number, citation, cross-reference or defined term altered, moved to another sentence or lost; a list item lost; a technical term paraphrased. Quote ORIGINAL and REVISED for each item and say in one line what changed. Ignore pure punctuation and word-order changes that preserve meaning. If there is nothing to report, reply with the single line: NO MEANING CHANGES."""


def slug(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", h.lstrip("# ").lower()).strip("-")[:40]


def chunks_of(tag: str, text: str):
    text = text.replace("\r\n", "\n")
    heads = [(m.start(), m.group(0)) for m in re.finditer(r"^## .*$", text, flags=re.M)]
    if not heads or heads[0][0] > 0:
        heads.insert(0, (0, "## (front matter)"))
    heads.append((len(text), "END"))
    n = 0
    for (s, h), (e, _) in zip(heads, heads[1:]):
        if h.startswith(SKIP_HEADINGS):
            continue
        body = text[s:e]
        if len(body.split()) > MAX_WORDS:
            subs = [(m.start(), m.group(0)) for m in re.finditer(r"^### .*$", body, flags=re.M)]
            subs.append((len(body), "END"))
            pre = body[: subs[0][0]]
            if pre.strip():
                n += 1
                yield f"{tag}_{n:02d}_{slug(h)}_intro", pre
            for (ss, sh), (se, _) in zip(subs, subs[1:]):
                n += 1
                yield f"{tag}_{n:02d}_{slug(sh)}", body[ss:se]
        else:
            n += 1
            yield f"{tag}_{n:02d}_{slug(h)}", body


def style_count(s: str) -> dict[str, int]:
    return {k: len(v) for k, v in scan_text(s, list(STYLE_KEYS)).items()}


DEFAULT_TERMS = "the paper's method, benchmark, metric and label names"


def brief(pass_no: int, terms: list[str]) -> str:
    """The rewrite brief for a pass, with the project's defined names (if any) frozen under constraint D."""
    listed = ", ".join(terms) + ", and every other defined name" if terms else DEFAULT_TERMS
    return PROMPTS[pass_no].replace("{TERMS}", listed)


def worth_sending(body: str, skip_if_contains: tuple[str, ...] = ()) -> bool:
    if any(k in body for k in skip_if_contains):
        return False
    return len(body.split()) >= 30 and sum(style_count(body).values()) > 0


def normalize(reply: str) -> str:
    reply = reply.replace("\r\n", "\n").strip("\n")
    m = re.fullmatch(r"```(?:markdown|md)?\n(.*)\n```", reply, flags=re.S)
    return (m.group(1) if m else reply) + "\n\n"


def skeleton(s: str):
    lines = s.replace("\r\n", "\n").split("\n")
    keep, in_code = [], False
    for ln in lines:
        if ln.startswith("```"):
            in_code = not in_code
            keep.append(ln)
        elif in_code or ln.startswith("#") or ln.startswith("|") or ln.startswith("![](") or ln.startswith("$$"):
            keep.append(ln)
    return keep


def tokens(s: str) -> Counter:
    return Counter(
        re.findall(r"[+\-−]?\d+(?:[.,]\d+)*%?(?!\w|\.\d)", s)
        + re.findall(r"[A-Z][\w'’\-]+(?: et al\.| and [A-Z][\w'’\-]+)? \d{4}[a-z]?(?=[;)\],])", s)
        + re.findall(r"§\d+(?:\.\d+)*|Table [A-Z]?\d+|Figure [A-Z]?\d+|Appendix [A-Z]|§S-[A-Z](?:\.\w+)?|\bRQ\d|\bF\d\b|\bD\d\b", s)
        + re.findall(r"\$\$.*?\$\$|\$[^$\n]+\$", s, flags=re.S)
    )


ANCHOR_RX = re.compile(r"—|(?<=\w)--(?=\w)|;|[→⇒⟵⟶←↔]|…|\b(?:" + "|".join(BAN_WORDS + WATCH_WORDS) + r")\b|"
                       r"\b(?:" + CONNECTIVE_OPENERS + r")\b|\bnot (?:only|just|merely)\b", re.I)
ANCHOR_WINDOW = 8   # tokens (words and whitespace runs) on either side of an edit that may carry the tell
GROUP_GAP = 14      # edits closer than this (in original tokens, ~7 words) are decided together


def anchored_merge(old: str, new: str) -> tuple[str, int, int, list[tuple[str, str]]]:
    """Keep only the edits that sit next to a style tell; put the original text back everywhere else.

    Tokenizes both texts into words and whitespace runs (so paragraph breaks survive), diffs them, and
    for every non-equal opcode checks whether the ORIGINAL tokens within ANCHOR_WINDOW of it contain a
    tell (dash, semicolon, arrow, ellipsis, listed word or opener). Unanchored edits are the model
    "improving" prose it was told to leave alone; they are reverted mechanically and reported.
    Returns (merged_text, kept_edits, reverted_edits, [(old_segment, new_segment) reverted])."""
    ot = re.findall(r"\S+|\s+", old)
    nt = re.findall(r"\S+|\s+", new)
    sm = difflib.SequenceMatcher(None, ot, nt, autojunk=False)
    # group non-equal opcodes separated by at most GROUP_GAP equal tokens: one recast phrase usually
    # diffs as several opcodes, and reverting half of it would splice two wordings into one sentence
    ops = sm.get_opcodes()
    groups, cur = [], []
    for k, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag == "equal":
            continue
        if cur and i1 - ops[cur[-1]][2] > GROUP_GAP:
            groups.append(cur)
            cur = []
        cur.append(k)
    if cur:
        groups.append(cur)
    decision, log = {}, []
    for g in groups:
        i1, i2 = ops[g[0]][1], ops[g[-1]][2]
        j1, j2 = ops[g[0]][3], ops[g[-1]][4]
        window = "".join(ot[max(0, i1 - ANCHOR_WINDOW): i2 + ANCHOR_WINDOW])
        seg_old, seg_new = "".join(ot[i1:i2]), "".join(nt[j1:j2])
        # an edit may not add or drop bold/italic marks (a run-in label demoted to plain text is a loss)
        keep = bool(ANCHOR_RX.search(window)) and seg_old.count("*") == seg_new.count("*")
        for k in g:
            decision[k] = keep
        if not keep:
            log.append((seg_old, seg_new))
    out, kept, reverted = [], 0, 0
    for k, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag == "equal" or decision[k]:
            out.extend(nt[j1:j2])
            kept += tag != "equal"
        else:
            out.extend(ot[i1:i2])
            reverted += 1
    return "".join(out), kept, len(log), log


def guard(old: str, new: str, pass_no: int = 1) -> list[str]:
    problems = []
    if old.count("**") != new.count("**") or old.count("*") != new.count("*"):
        problems.append(f"bold/italic marks changed ({old.count('*')} -> {new.count('*')} asterisks)")
    if skeleton(old) != skeleton(new):
        problems.append("skeleton (heading/table/figure/code/display-math) changed")
    lost = dict((tokens(old) - tokens(new)).items())
    added = dict((tokens(new) - tokens(old)).items())
    if lost or added:
        problems.append(f"tokens lost={dict(list(lost.items())[:6])} added={dict(list(added.items())[:6])}")
    ow, nw = len(old.split()), len(new.split())
    if abs(nw - ow) > max(6, 0.08 * ow):
        problems.append(f"word count {ow} -> {nw} (outside 8%)")
    if len(re.findall(r"(?<=\S)  +(?=\S)", new)) > len(re.findall(r"(?<=\S)  +(?=\S)", old)):
        problems.append("new double spaces")
    so, sn = style_count(old), style_count(new)
    if pass_no == 2 and sn["semicolon"] > max(2, so["semicolon"] // 2):
        problems.append(f"semicolons {so['semicolon']} -> {sn['semicolon']} (pass 2 target ≤ {max(2, so['semicolon'] // 2)})")
    # reverted (unanchored) groups keep their dashes, so pass 1 only requires a fall; the final scan and
    # pass 2 enforce the per-1k target on the applied text
    if sn["em_dash"] > so["em_dash"] or (pass_no == 2 and sn["em_dash"] > max(1, so["em_dash"] // 2)):
        problems.append(f"em dashes {so['em_dash']} -> {sn['em_dash']} did not fall as required")
    for k in ("arrow_prose", "ellipsis_char", "ban_words", "not_only"):
        if sn[k] > so[k]:
            problems.append(f"{k} rose {so[k]} -> {sn[k]}")
    # an em dash recast as a semicolon is still a joint; the total number of joints must not rise
    if sn["semicolon"] + sn["em_dash"] > so["semicolon"] + so["em_dash"]:
        problems.append(f"joints rose: semicolons {so['semicolon']} -> {sn['semicolon']}, em {so['em_dash']} -> {sn['em_dash']}")
    return problems


def launch(work: Path, ids: list[str], prompt: str, in_dir: Path, out_dir: Path, parallel: int, effort: str, label: str):
    out_dir.mkdir(exist_ok=True)
    pending, running = list(ids), {}
    t0 = time.time()
    while pending or running:
        while pending and len(running) < parallel:
            cid = pending.pop(0)
            # GOTCHA: a multi-paragraph prompt passed as the argv prompt reaches the model truncated at its
            # first blank line (observed with the Windows codex shim: the model then asks "which habits?").
            # So the full brief travels inside stdin, ahead of the text, and argv carries a one-line pointer.
            staged = in_dir / f"{cid}.stdin.md"
            staged.write_text("=== INSTRUCTIONS ===\n" + prompt + "\n\n=== TEXT (apply the instructions to this; reply as they say) ===\n"
                              + (in_dir / f"{cid}.md").read_text(encoding="utf-8"), encoding="utf-8")
            cmd = [CODEX, "exec", "--ephemeral", "-s", "read-only", "-c", f'model_reasoning_effort="{effort}"',
                   "-o", str(out_dir / f"{cid}.md"),
                   "Follow the INSTRUCTIONS block at the top of the stdin text exactly, applied to the TEXT block that follows it. Reply only with what the instructions ask for."]
            running[cid] = subprocess.Popen(
                cmd, stdin=open(staged, encoding="utf-8"),
                stdout=open(out_dir / f"{cid}.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT)
            print(f"[{time.time() - t0:5.0f}s] {label} start {cid}", flush=True)
        for cid, p in list(running.items()):
            if p.poll() is not None:
                f = out_dir / f"{cid}.md"
                ok = f.exists() and f.stat().st_size > 0
                print(f"[{time.time() - t0:5.0f}s] {label} done  {cid} exit={p.returncode} {'OK' if ok else 'NO OUTPUT'}", flush=True)
                del running[cid]
        time.sleep(5)
    print(f"{label}: all done in {time.time() - t0:.0f}s")


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("run", "merge", "review", "apply"):
        print(__doc__)
        return 2
    stage = argv[0]
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    work = Path(opt("--work", ".ai_style_rewrite"))
    parallel, effort, only, force = int(opt("--parallel", 6)), opt("--effort", "high"), opt("--only"), "--force" in argv
    pass_no = int(opt("--pass", 1))   # 1 = dashes/arrows/vocabulary, 2 = semicolons + residual dashes (see PROMPTS)
    skips = tuple(argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--skip-if-contains")
    terms_file = opt("--terms-file")
    terms = [ln.strip() for ln in Path(terms_file).read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")] if terms_file else []
    IN, OUT, DIFF, REV = work / "in", work / "out", work / "diff", work / "review"
    index_path = work / "index.json"

    if stage == "run":
        files = []
        if "--files" in argv:
            for f in argv[argv.index("--files") + 1:]:
                if f.startswith("--"):
                    break
                files.append(f)
        assert files, "--files required"
        IN.mkdir(parents=True, exist_ok=True)
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
        for f in files:
            path = Path(f)
            tag = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
            for cid, body in chunks_of(tag, path.read_text(encoding="utf-8")):
                if not worth_sending(body, skips):
                    continue
                (IN / f"{cid}.md").write_text(body, encoding="utf-8")
                index[cid] = {"source": str(path), "words": len(body.split()), "style": style_count(body)}
        index_path.write_text(json.dumps(index, indent=1), encoding="utf-8")
        ids = [c for c in index if (not only or only in c) and (force or not (OUT / f"{c}.md").exists())]
        print(f"{len(index)} chunks indexed, {len(ids)} to run, {sum(index[c]['words'] for c in ids)} words")
        launch(work, ids, brief(pass_no, terms), IN, OUT, parallel, effort, "rewrite")
        return 0

    index = json.loads(index_path.read_text(encoding="utf-8"))
    ids = [c for c in index if not only or only in c]

    if stage == "review":
        rin = work / "review_in"
        rin.mkdir(exist_ok=True)
        todo = []
        for cid in ids:
            o, n = IN / f"{cid}.md", OUT / f"{cid}.md"
            if not n.exists() or (not force and (REV / f"{cid}.md").exists()):
                continue
            (rin / f"{cid}.md").write_text("=== ORIGINAL ===\n" + o.read_text(encoding="utf-8") + "\n=== REVISED ===\n"
                                           + normalize(n.read_text(encoding="utf-8")), encoding="utf-8")
            todo.append(cid)
        launch(work, todo, REVIEW_PROMPT, rin, REV, parallel, effort, "review")
        return 0

    DIFF.mkdir(exist_ok=True)
    passed, failed = {}, []
    for cid in ids:
        out_path = OUT / f"{cid}.md"
        if not out_path.exists() or out_path.stat().st_size == 0:
            failed.append((cid, "no reply"))
            continue
        old = (IN / f"{cid}.md").read_text(encoding="utf-8").replace("\r\n", "\n")
        new, kept, reverted, reverts = anchored_merge(old, normalize(out_path.read_text(encoding="utf-8")))
        problems = guard(old, new, pass_no)
        ow, nw = old.split(), new.split()
        sm = difflib.SequenceMatcher(None, ow, nw, autojunk=False)
        changed = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")
        with (DIFF / f"{cid}.diff").open("w", encoding="utf-8") as f:
            f.write(f"# {cid}  words {len(ow)} -> {len(nw)}  changed~{changed}  guard={'FAIL' if problems else 'ok'}"
                    f"  style {style_count(old)} -> {style_count(new)}\n")
            for p in problems:
                f.write(f"# ! {p}\n")
            f.write(f"# anchored edits kept: {kept}; unanchored edits reverted: {reverted}\n")
            for a, b in reverts:
                f.write(f"# reverted: {a.strip()!r} <- {b.strip()!r}\n")
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag != "equal":
                    f.write(f"\n--- {tag} ---\n- {' '.join(ow[i1:i2])}\n+ {' '.join(nw[j1:j2])}\n")
        if problems:
            failed.append((cid, "; ".join(problems)))
        else:
            passed[cid] = (old, new, len(ow), len(nw), changed)
    print(f"guard passed: {len(passed)}   failed/missing: {len(failed)}")
    for cid, why in failed:
        print(f"  FAIL {cid}: {why}")
    for cid, (old, new, a, b, c) in passed.items():
        so, sn = style_count(old), style_count(new)
        print(f"  ok   {cid}: {a}->{b} w, ~{c} touched; em {so['em_dash']}->{sn['em_dash']}, ; {so['semicolon']}->{sn['semicolon']}")

    if stage == "apply":
        by_src: dict[str, str] = {}
        for cid, (old, new, *_r) in passed.items():
            src = index[cid]["source"]
            text = by_src.get(src) or Path(src).read_text(encoding="utf-8").replace("\r\n", "\n")
            if text.count(old) != 1:
                print(f"  SKIP {cid}: original chunk not unique/absent in {src} (already applied?)")
                continue
            by_src[src] = text.replace(old, new, 1)
        for src, text in by_src.items():
            Path(src).write_text(text, encoding="utf-8")
            print(f"APPLIED -> {src} ({len(text.split())} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
