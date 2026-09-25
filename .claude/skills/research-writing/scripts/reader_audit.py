r"""Adversarial reader audit of a draft, paragraph by paragraph, by a model of another family (codex / GPT) (2026-09-19).

Why: readability is not sentence length. A paragraph is readable when a reader outside the project can say, after one
read, what it wants them to believe, and when the claim, the reasoning, the evidence and the conclusion arrive in that
order. The writer cannot test this on their own text; a blind reader can. This script is the blind reader.

Stages
  audit    split the draft (parts concatenated) into section chunks, number every prose paragraph [P01]..., send each
           chunk to `codex exec` (read-only, ephemeral; the brief travels in stdin) and collect one JSON per chunk:
           per paragraph the point in the reader's words (or UNCLEAR), where the point sits, the paragraph type, the
           missing or misordered steps, whether it is a running account, the hard sentences, undefined terms, a 1-5
           clarity score; per section the core claim and whether it is stated up front. With --context every chunk
           carries the earlier sections as an unscored ALREADY READ block, as a real reader would have them. With
           --reference <key,key> the chunks whose id contains a key (the appendices the body points to, e.g.
           a glossary appendix) travel with every other chunk as an unscored REFERENCE block, as a reader flips to them.
           Ruler v2 (2026-09-22): the brief states the page budget, anchors clarity on point and reasoning rather than
           on detail carried, and adds per-paragraph "link" (follows / jump) and per-section "chain" (holds / detours);
           the summary line reports jumps and chains beside the mean. Scores under v2 are not comparable with v1 runs;
           re-audit the old version under the same flags before comparing (<work>/ruler.txt records the settings).
  ledger   write <work>/ledger.json: for every numbered paragraph its first sentence, which under the paragraph
           contract (one point, stated first) is the writer's intended point.
  report   merge the JSON replies into <work>/report.md (worst paragraphs first) and <work>/report.json.
  drift    write <work>/drift.md: the long paragraphs (>= --min-words, default 95) whose point drifts by the reader's
           own flags (running account, 4+ points, or point not first), longest first, with point and fix hint. The
           repair is deleting the sentences after the point, never packing them (2026-09-22).
  compare  given a ledger (JSON: chunk id -> {"P01": "intended point", ...}) and a finished audit, ask the reader model
           to score each (intended point, reader's point) pair 0 = different, 1 = partly, 2 = same; writes compare.md.

Inputs:  --files: the draft's markdown part files, in reading order (the project's own paths)
         --reader "<who reads>": the reader persona (default READER; name the neighbouring field the paper must reach)
Outputs: <work>/in/*.md (numbered chunks), <work>/out/*.json, ruler.txt, report.md, drift.md, compare.md
Usage:   python reader_audit.py audit   --work drafts/reader-audit-v05 --files drafts/v05-part1.md drafts/v05-part2.md
                                         [--context] [--reference <key,key>] [--reader "..."] [--parallel 5] [--effort high] [--only id,id]
         python reader_audit.py report  --work drafts/reader-audit-v05
         python reader_audit.py drift   --work drafts/reader-audit-v05 [--min-words 95]
         python reader_audit.py ledger  --work drafts/reader-audit-v05
         python reader_audit.py compare --work drafts/reader-audit-v05 --ledger drafts/reader-audit-v05/ledger.json
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

CODEX = shutil.which("codex") or "codex"
MAX_CHUNK = 30000

RULER = "v2 (2026-09-22): page budget stated, clarity anchored on point and chain, link and chain fields, reference block"

# who the blind reader is: someone the paper must reach but who does not work in its sub-field (--reader overrides;
# for example "an ML researcher who is rusty in sequential statistics and has never worked in quantitative finance")
READER = ("a careful reader from a neighbouring field: a researcher who knows the general area but has never worked "
          "in this paper's sub-field")

AUDIT_BRIEF = """You are {READER}. You are NOT the author's friend. You read each numbered paragraph ONCE, in
order, with only what came before it in this text. If you have to guess what a paragraph wants you to believe, the
paragraph has failed, and you say so. Do not repair the text; diagnose it.

The text is one section of a research paper. Prose paragraphs carry a tag like [P07]. Headers, tables, figures, display
equations and raw LaTeX are context only; do not score them.

The paper is written to a fixed page budget. Its appendices carry definitions, conventions, derivations and worked
examples, and the body points to them. If a REFERENCE block follows the text, it holds those appendices; a real reader
can flip to them, so a term defined there or in the ALREADY READ block counts as defined. Judge a paragraph by whether
its point can be found and its reasoning followed at this length, not by whether it carries every detail: a detail the
paragraph points elsewhere for is not missing. A detail it needs for its own reasoning and neither gives nor points to
is missing.

For EVERY tagged paragraph report:
- "id": the tag.
- "point": ONE sentence stating what the paragraph wants the reader to believe or be able to do. If you cannot tell
  after one read, write "UNCLEAR: " followed by the two or three things it might be saying.
- "point_position": "first sentence" | "middle" | "last sentence" | "nowhere".
- "type": "argument" | "data reading" | "definition or mechanism" | "design or procedure" | "transition".
- "link": "follows" if the paragraph builds on the previous paragraph or on the section's stated question, "jump" if
  it starts a new topic with no bridge from what came before, "first" for the first paragraph of the section.
- "missing_steps": for an argument the expected order is claim, reasoning, evidence, conclusion; for a data reading it
  is what the data look like, what follows from that, which claim it supports or refutes, conclusion; for a mechanism it
  is why it is needed, what it does, how. List the steps that are absent or out of order. Empty list if none.
- "running_account": true if the paragraph strings facts, caveats or numbers one after another without subordinating
  them to one point. "n_points": how many separate points it actually carries.
- "hard_sentences": for each sentence that has more than one turn (but / although / while / however / yet / whereas /
  though), or more than two levels of nested clauses or parentheses, or more than about 40 words, or a list of numbers
  the reader cannot hold: {"starts": first eight words, "why": short reason}. At most five per paragraph.
- "undefined": terms or symbols used here that the text so far, the ALREADY READ block and the REFERENCE block have
  not defined for a reader like you.
- "clarity": integer 1-5. 5 = I can repeat the point and its reasoning to a colleague. 4 = point and reasoning clear;
  one detail I would look up. 3 = I got the point but had to reread or guess one step. 2 = I got a point, but not the
  one the paragraph seems to make, or I cannot follow the reasoning. 1 = I do not know what this was for.
- "fix_hint": one sentence on the single change that would help most at this length (for example: "open with the claim
  that the referee, not the controller, sets the count; move the three caveats to one closing sentence").

Then for the section as a whole report "section": {"core_claim": at most two sentences, or "UNCLEAR: ...";
"stated_up_front": true/false; "chain": "holds" if the paragraphs form one chain from question to mechanism or
reasoning to evidence to conclusion, "detours" if the reader is taken off that chain and back; "detours": the
paragraphs that leave the chain; "order_problems": paragraphs that arrive before the reader has what they need;
"redundant": paragraphs that repeat another; "overall": two sentences an editor should hear}.

Reply with ONE JSON object and nothing else: {"chunk": "<the chunk id given on the first line of the text>",
"paragraphs": [...], "section": {...}}. No markdown fence, no commentary."""

COMPARE_BRIEF = """You are given pairs for one section of a paper: the writer's INTENDED point for a paragraph and what a blind
READER said the paragraph's point was. Score each pair: 2 = the reader got the intended point; 1 = partly (the reader
got a side point or a weaker version); 0 = different or the reader found it unclear. Reply with ONE JSON object and
nothing else: {"chunk": "...", "pairs": [{"id": "P01", "score": 2, "gap": "what the reader missed, or empty"}]}."""

SKIP_START = ("#", "|", "![", "```", ":::", "\\", "$$", "---", "<!--", "Table:", ": ")


def is_prose(block: str) -> bool:
    """A block that is a prose paragraph (scored), as opposed to a header, table, figure, fence, equation or raw LaTeX."""
    s = block.strip()
    if not s or s.startswith(SKIP_START):
        return False
    if s.startswith("- ") or re.match(r"^\d+\. ", s):
        return True
    return len(s) > 60


def blocks_of(text: str) -> list[str]:
    """Blank-line separated blocks, keeping fenced regions (``` and :::) whole so their inner blank lines do not split."""
    out, cur, fence = [], [], None
    for line in text.splitlines():
        st = line.strip()
        if fence is None and (st.startswith("```") or st.startswith(":::")):
            fence = st[:3]
        elif fence is not None and st.startswith(fence) and len(cur) > 0 and st.rstrip("`:") == "":
            cur.append(line); out.append("\n".join(cur)); cur, fence = [], None
            continue
        if st == "" and fence is None:
            if cur:
                out.append("\n".join(cur)); cur = []
        else:
            cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def split_sections(text: str, level: str) -> list[tuple[str, str]]:
    """(header line, body including the header) for every header of the given level ('# ' or '## ')."""
    idx = [m.start() for m in re.finditer(rf"^{re.escape(level)}", text, re.M)]
    if not idx:
        return []
    idx.append(len(text))
    return [(text[a:b].splitlines()[0], text[a:b]) for a, b in zip(idx, idx[1:])]


def slug(header: str) -> str:
    m = re.search(r"\{#([^}\s]+)", header)
    base = m.group(1) if m else re.sub(r"[^a-z0-9]+", "-", header.lower()).strip("-")
    return base.replace(":", "-")[:40]


def chunks_of(text: str) -> list[tuple[str, str]]:
    """Section chunks (id, text): top-level sections, split at '## ' when longer than MAX_CHUNK; YAML and references dropped."""
    out = []
    if text.startswith("---"):
        head, text = text[3:].split("\n---", 1)
        m = re.search(r"^abstract: \|\n((?:  .*\n?)+)", head, re.M)
        if m:
            out.append(("00-abstract", "# Abstract\n\n" + " ".join(l.strip() for l in m.group(1).splitlines())))
    for n, (head, body) in enumerate(split_sections(text, "# "), 1):
        if "References" in head:
            continue
        if len(body) <= MAX_CHUNK:
            out.append((f"{n:02d}-{slug(head)}", body)); continue
        subs = split_sections(body, "## ")
        pre = body[: body.find(subs[0][1])] if subs else body
        if pre.strip() and len(pre.strip().splitlines()) > 1:
            out.append((f"{n:02d}-{slug(head)}-0-opening", pre))
        for k, (h2, b2) in enumerate(subs, 1):
            out.append((f"{n:02d}-{slug(head)}-{k}-{slug(h2)}"[:70], head + "\n\n" + b2))
    return out


def number_paragraphs(chunk: str) -> tuple[str, int]:
    """Prefix every prose block with [Pnn]; returns the tagged text and the paragraph count."""
    out, n = [], 0
    for b in blocks_of(chunk):
        if is_prose(b):
            n += 1
            out.append(f"[P{n:02d}] {b}")
        else:
            out.append(b)
    return "\n\n".join(out), n


def first_sentence(par: str) -> str:
    """The paragraph's first sentence (its stated point under the one-point-per-paragraph contract); math and
    abbreviations such as 'i.i.d.' or 'e.g.' do not end it."""
    s = re.sub(r"^\[P\d+\]\s*", "", par.strip()).split("\n")[0]
    s = re.sub(r"^(?:[-*]|\d+\.)\s+", "", s)
    for m in re.finditer(r"[.?!](?=\s+[A-Z*\\(]|\s*$)", s):
        head = s[: m.end()]
        if head.count("$") % 2 == 0 and not re.search(r"\b(?:e\.g|i\.e|i\.i\.d|cf|vs)\.$", head):
            return head
    return s


def stage_ledger(work: Path) -> None:
    """ledger.json from the numbered chunks: chunk id -> {Pnn: first sentence}."""
    led = {}
    for f in sorted((work / "in").glob("*.md")):
        if f.name.endswith((".stdin.md", ".ctx.md")):
            continue
        pars = {}
        for b in blocks_of(f.read_text(encoding="utf-8")):
            m = re.match(r"^\[(P\d+)\]", b)
            if m:
                pars[m.group(1)] = first_sentence(b)
        led[f.stem] = pars
    (work / "ledger.json").write_text(json.dumps(led, indent=1, ensure_ascii=True), encoding="utf-8")
    print(f"ledger: {sum(len(v) for v in led.values())} paragraphs in {len(led)} chunks")


def parse_reply(raw: str) -> dict:
    """The first balanced JSON object in a model reply (tolerates a fence or a stray sentence around it)."""
    a = raw.find("{")
    if a < 0:
        raise ValueError("no JSON object")
    depth, in_str, esc = 0, False, False
    for i, c in enumerate(raw[a:], a):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(raw[a:i + 1])
    raise ValueError("unbalanced JSON")


def launch(ids: list[str], brief: str, in_dir: Path, out_dir: Path, parallel: int, effort: str, label: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pending, running, t0 = list(ids), {}, time.time()
    while pending or running:
        while pending and len(running) < parallel:
            cid = pending.pop(0)
            staged = in_dir / f"{cid}.stdin.md"
            ctx = in_dir / f"{cid}.ctx.md"
            already = ("\n\n=== ALREADY READ (earlier sections of the same paper; context only, do not score; a term "
                       "defined here counts as defined) ===\n" + ctx.read_text(encoding="utf-8")) if ctx.exists() else ""
            ref = in_dir / f"{cid}.ref.md"
            reference = ("\n\n=== REFERENCE (appendices the body points to; a real reader can flip to them; context only, "
                         "do not score; a term defined here counts as defined) ===\n" + ref.read_text(encoding="utf-8")) if ref.exists() else ""
            staged.write_text("=== INSTRUCTIONS ===\n" + brief + already + "\n\n=== TEXT (chunk id: " + cid + ") ===\n"
                              + (in_dir / f"{cid}.md").read_text(encoding="utf-8") + reference, encoding="utf-8")
            cmd = [CODEX, "exec", "--ephemeral", "-s", "read-only", "-c", f'model_reasoning_effort="{effort}"',
                   "-o", str(out_dir / f"{cid}.json"),
                   "Follow the INSTRUCTIONS block at the top of the stdin text exactly, applied to the TEXT block that follows it. Reply only with the JSON object the instructions ask for."]
            running[cid] = subprocess.Popen(cmd, stdin=open(staged, encoding="utf-8"),
                                            stdout=open(out_dir / f"{cid}.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT)
            print(f"[{time.time() - t0:5.0f}s] {label} start {cid}", flush=True)
        for cid, p in list(running.items()):
            if p.poll() is not None:
                f = out_dir / f"{cid}.json"
                ok = f.exists() and f.stat().st_size > 0
                print(f"[{time.time() - t0:5.0f}s] {label} done  {cid} exit={p.returncode} {'OK' if ok else 'NO OUTPUT'}", flush=True)
                del running[cid]
        time.sleep(5)
    print(f"{label}: all done in {time.time() - t0:.0f}s")


def reference_text(chunks: list[tuple[str, str]], reference: str | None) -> str:
    """The bodies of the chunks whose id contains one of the comma-separated reference keys (the appendices a real
    reader can flip to), joined; empty when no key matches or none was given."""
    if not reference:
        return ""
    keys = [k.strip() for k in reference.split(",") if k.strip()]
    return "\n\n".join(body for cid, body in chunks if any(k in cid for k in keys))


def stage_audit(files: list[str], work: Path, parallel: int, effort: str, only: str | None, context: bool,
                reference: str | None = None, reader: str = READER) -> None:
    assert files, "--files required: the draft's part files, in reading order"
    text = "\n\n".join(Path(f).read_text(encoding="utf-8") for f in files)
    in_dir = work / "in"; in_dir.mkdir(parents=True, exist_ok=True)
    chunks = chunks_of(text)
    ref = reference_text(chunks, reference)
    ids, seen = [], []
    for cid, body in chunks:
        tagged, n = number_paragraphs(body)
        if context and seen and not cid.startswith("00-"):
            # the sections a real reader has already read travel along, untagged and unscored
            (in_dir / f"{cid}.ctx.md").write_text("\n\n".join(seen), encoding="utf-8")
        if ref and not any(k.strip() in cid for k in reference.split(",")):
            # the appendices the body points to travel along with every other chunk, as a reader would flip to them
            (in_dir / f"{cid}.ref.md").write_text(ref, encoding="utf-8")
        if not cid.startswith("00-"):
            seen.append(body)
        if n == 0:
            continue
        (in_dir / f"{cid}.md").write_text(tagged, encoding="utf-8"); ids.append(cid)
    if only:
        ids = [i for i in ids if any(i.startswith(o) for o in only.split(","))]
    (work / "ruler.txt").write_text(RULER + (f"; reference={reference}" if reference else "") + ("; context" if context else "") + "\n", encoding="utf-8")
    print(f"{len(ids)} chunks: {', '.join(ids)}" + (f"; reference block {len(ref.split())} words" if ref else ""))
    launch(ids, AUDIT_BRIEF.replace("{READER}", reader), in_dir, work / "out", parallel, effort, "audit")


def load_audit(work: Path) -> dict:
    res = {}
    for f in sorted((work / "out").glob("*.json")):
        try:
            res[f.stem] = parse_reply(f.read_text(encoding="utf-8"))
        except (ValueError, json.JSONDecodeError) as e:
            print("UNPARSED", f.name, e)
    return res


def summary_line(res: dict, rows: list[tuple[str, dict]]) -> str:
    """One line of numbers: the mean clarity and its histogram, then the structural signals (running accounts, point
    not first, jumps, sections whose chain holds), so a version comparison reads the structure and not only the mean."""
    clar = [p.get("clarity", 0) for _, p in rows]
    n = max(1, len(rows))
    links = [p.get("link") for _, p in rows]
    chains = [r.get("section", {}).get("chain") for r in res.values()]
    return (f"clarity: mean {sum(clar) / max(1, len(clar)):.2f}; <=2: {sum(c <= 2 for c in clar)}; 3: {sum(c == 3 for c in clar)}; "
            f">=4: {sum(c >= 4 for c in clar)}; running accounts: {sum(bool(p.get('running_account')) for _, p in rows)}; "
            f"point not in the first sentence: {sum(p.get('point_position') != 'first sentence' for _, p in rows)}; "
            f"jumps: {sum(l == 'jump' for l in links)} of {n}; chain holds: {sum(c == 'holds' for c in chains)} of {len(res)} sections")


def stage_report(work: Path) -> None:
    res = load_audit(work)
    rows = [(c, p) for c, r in res.items() for p in r.get("paragraphs", [])]
    (work / "report.json").write_text(json.dumps(res, indent=1, ensure_ascii=True), encoding="utf-8")
    ruler = (work / "ruler.txt").read_text(encoding="utf-8").strip() if (work / "ruler.txt").exists() else "v1"
    L = [f"# Reader audit ({len(res)} chunks, {len(rows)} paragraphs; ruler {ruler})\n"]
    L.append(summary_line(res, rows) + "\n")
    L.append("## Sections\n")
    for c, r in res.items():
        s = r.get("section", {})
        L.append(f"- **{c}** (stated up front: {s.get('stated_up_front')}; chain: {s.get('chain', 'n/a')}): {s.get('core_claim')} -- {s.get('overall')}"
                 + (f" Detours: {s.get('detours')}" if s.get("detours") else "")
                 + (f" Order: {s.get('order_problems')}" if s.get("order_problems") else "")
                 + (f" Redundant: {s.get('redundant')}" if s.get("redundant") else ""))
    L.append("\n## Paragraphs, worst first\n")
    for c, p in sorted(rows, key=lambda cp: (cp[1].get("clarity", 0), -int(cp[1].get("n_points", 1) or 1))):
        L.append(f"### {c} {p.get('id')}  clarity {p.get('clarity')}, {p.get('type')}, point at: {p.get('point_position')}, "
                 f"points carried: {p.get('n_points')}, running account: {p.get('running_account')}")
        L.append(f"- reader's point: {p.get('point')}")
        if p.get("missing_steps"):
            L.append(f"- missing or misordered: {p.get('missing_steps')}")
        for h in p.get("hard_sentences", []) or []:
            L.append(f"- hard sentence: \"{h.get('starts')}...\" ({h.get('why')})")
        if p.get("undefined"):
            L.append(f"- undefined: {p.get('undefined')}")
        L.append(f"- fix: {p.get('fix_hint')}\n")
    (work / "report.md").write_text("\n".join(L), encoding="utf-8")
    print(L[1])


def drift_rows(work: Path, min_words: int = 95) -> list[tuple]:
    """Long paragraphs that the reader says drift: at least min_words and (running account, or four or more points, or
    the point not in the first sentence). Rows: (words, chunk, id, clarity, n_points, position, running, point, fix)."""
    res = load_audit(work)
    rows = []
    for c, r in res.items():
        f = work / "in" / f"{c}.md"
        if not f.exists():
            continue
        words = {}
        for b in blocks_of(f.read_text(encoding="utf-8")):
            m = re.match(r"^\[(P\d+)\]", b)
            if m:
                words[m.group(1)] = len(b.split())
        for p in r.get("paragraphs", []):
            w = words.get(str(p.get("id", "")).strip("[]"), 0)
            drift = bool(p.get("running_account")) or int(p.get("n_points") or 1) >= 4 or p.get("point_position") != "first sentence"
            if w >= min_words and drift:
                rows.append((w, c, p.get("id"), p.get("clarity"), p.get("n_points"), p.get("point_position"),
                             bool(p.get("running_account")), p.get("point", ""), p.get("fix_hint", "")))
    return sorted(rows, reverse=True)


def stage_drift(work: Path, min_words: int) -> None:
    """<work>/drift.md: the long paragraphs whose point drifts, longest first, with the reader's point and fix hint.
    The repair is deletion: cut the sentences after the point, never pack them."""
    rows = drift_rows(work, min_words)
    L = [f"# Long paragraphs that drift ({len(rows)}; at least {min_words} words and a running account, 4+ points or the point not first)\n"]
    for w, c, i, cl, n, pos, ra, pt, fx in rows:
        L.append(f"- **{c} {i}** {w} words, clarity {cl}, points {n}, point at {pos}, running account {ra}\n  - reader's point: {pt}\n  - fix: {fx}")
    (work / "drift.md").write_text("\n".join(L), encoding="utf-8")
    print(L[0])


def stage_compare(work: Path, ledger_path: Path, parallel: int, effort: str) -> None:
    ledger, res = json.loads(ledger_path.read_text(encoding="utf-8")), load_audit(work)
    in_dir = work / "cmp-in"; in_dir.mkdir(exist_ok=True)
    ids = []
    for cid, want in ledger.items():
        got = {p["id"].strip("[]"): p.get("point", "") for p in res.get(cid, {}).get("paragraphs", [])}
        pairs = [f"{pid}\n  INTENDED: {pt}\n  READER: {got.get(pid, 'MISSING')}" for pid, pt in want.items()]
        (in_dir / f"{cid}.md").write_text("\n\n".join(pairs), encoding="utf-8"); ids.append(cid)
    launch(ids, COMPARE_BRIEF, in_dir, work / "cmp-out", parallel, effort, "compare")
    L, tot = ["# Intended point vs reader's point\n"], []
    for f in sorted((work / "cmp-out").glob("*.json")):
        r = parse_reply(f.read_text(encoding="utf-8"))
        for p in r.get("pairs", []):
            tot.append(p.get("score", 0))
            if p.get("score", 0) < 2:
                L.append(f"- **{f.stem} {p.get('id')}** score {p.get('score')}: {p.get('gap')}")
    L.insert(1, f"pairs {len(tot)}; matched (2): {sum(s == 2 for s in tot)}; partly (1): {sum(s == 1 for s in tot)}; missed (0): {sum(s == 0 for s in tot)}\n")
    (work / "compare.md").write_text("\n".join(L), encoding="utf-8")
    print(L[1])


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


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("audit", "report", "ledger", "compare", "drift"):
        print(__doc__); return 2
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    work = Path(opt("--work", "drafts/reader-audit"))
    if argv[0] == "drift":
        stage_drift(work, int(opt("--min-words", 95)))
    elif argv[0] == "audit":
        stage_audit(files_after(argv), work, int(opt("--parallel", 5)), opt("--effort", "high"), opt("--only"),
                    "--context" in argv, opt("--reference"), opt("--reader", READER))
    elif argv[0] == "report":
        stage_report(work)
    elif argv[0] == "ledger":
        stage_ledger(work)
    else:
        stage_compare(work, Path(opt("--ledger")), int(opt("--parallel", 5)), opt("--effort", "medium"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
