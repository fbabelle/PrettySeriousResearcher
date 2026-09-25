"""Scan markdown manuscripts for the punctuation, vocabulary and sentence patterns that editors read as
"written by an LLM", and report each one's density against a human-prose reference band.

Why: a desk-triage editor decides on the first pages in minutes, and a desk reject returns no feedback.
A spaced em dash every 50 words, arrows in running prose, "delve"/"tapestry"/"underscores", paragraphs
opening with "Moreover,", and "not X but Y" contrasts are all cheap for that editor to notice. This scanner
measures them so a de-styling pass can be targeted and then verified.

What is scanned: prose only. Table rows, fenced code, display math, image lines, HTML comments and the
References section are dropped; inline math ($...$) and inline code (`...`) are masked before matching.

Categories (see CATEGORIES): each has a severity —
  FIX   : should be zero or under a hard per-1k-words threshold in a submitted manuscript;
  WATCH : common in human academic prose too; reported as a density so a pass can thin it out.

Usage (paths are the project's own; nothing is assumed about its layout):
  python ai_style_scan.py drafts/<paper>.md drafts/<supplement>.md   # summary table per file
  python ai_style_scan.py FILE --list em_dash          # print every hit with line numbers
  python ai_style_scan.py FILE --json                  # machine-readable summary
  python ai_style_scan.py FILE --strict                # exit 1 if any FIX threshold is exceeded
  python ai_style_scan.py FILE --allow-file terms.txt  # also mask the project's defined labels (one per line)
Library use: from ai_style_scan import scan_text, prose_of  (scan_text returns {category: [hits]}).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ── vocabulary ────────────────────────────────────────────────────────────────────────────────
# Words/phrases that almost never appear in a human-written finance/ML paper but are frequent in LLM
# output. Matched case-insensitively as whole words; each entry is a regex fragment.
BAN_WORDS = [
    r"delv(?:e|es|ed|ing)", r"tapestry", r"testament to", r"in the realm of", r"realm", r"paradigm shift",
    r"game[- ]changer", r"cutting[- ]edge", r"groundbreaking", r"revolutioni[sz](?:e|es|ed|ing)",
    r"unlock(?:s|ed|ing)?", r"unleash(?:es|ed|ing)?", r"harness(?:es|ed|ing) the", r"embark(?:s|ed|ing)?",
    r"journey", r"seamless(?:ly)?", r"holistic(?:ally)?", r"multifaceted", r"myriad", r"plethora",
    r"elucidat(?:e|es|ed|ing)", r"meticulous(?:ly)?", r"intricate(?:ly)?", r"vibrant", r"foster(?:s|ed|ing)?",
    r"bolster(?:s|ed|ing)?", r"garner(?:s|ed|ing)?", r"underscor(?:e|es|ed|ing)", r"showcas(?:e|es|ed|ing)",
    r"pivotal", r"ever[- ]evolving", r"it is worth noting", r"it should be noted", r"it is important to note",
    r"in today'?s", r"in the era of", r"deep dive", r"at its core", r"sheds? light", r"pav(?:e|es|ed|ing) the way",
    r"bridg(?:e|es|ed|ing) the gap", r"double[- ]edged sword", r"at the intersection of", r"stands as",
    r"serves as a", r"nuanced", r"navigat(?:e|es|ed|ing) the", r"through the lens of", r"beacon",
    r"crucial(?:ly)?", r"actionable", r"synergy", r"empower(?:s|ed|ing)?", r"elevat(?:e|es|ed|ing)",
    r"streamlin(?:e|es|ed|ing)", r"leverag(?:e|es|ed|ing)", r"in summary", r"in conclusion", r"in essence",
    r"taken together", r"a rich (?:set|source|body)", r"landscape",
]
# Frequent in LLM prose but also in human academic writing: report the density, thin out if high.
WATCH_WORDS = [
    r"robust(?:ly)?", r"notably", r"importantly", r"interestingly", r"critically", r"moreover", r"furthermore",
    r"additionally", r"comprehensive(?:ly)?", r"highlight(?:s|ed|ing)?", r"key (?:insight|finding|result|point)s?",
    r"insights?", r"novel", r"rigorous(?:ly)?", r"granular", r"facilitat(?:e|es|ed|ing)", r"utili[sz](?:e|es|ed|ing)",
    r"enhanc(?:e|es|ed|ing)", r"ensur(?:e|es|ed|ing)", r"note that", r"ultimately", r"overall,", r"remarkabl[ey]",
    r"striking(?:ly)?", r"compelling", r"profound(?:ly)?", r"transformative", r"arguably", r"fundamentally",
    r"essentially", r"in particular", r"specifically,", r"consequently", r"conversely", r"hence",
]
# Technical senses of listed words, masked before matching (finance and statistics terms). A project's own
# defined labels that collide with the lists go in an allow file (--allow-file), not here.
ALLOW_PHRASES = ["leverage ratio", "is elevated", "elevated VIX", "robustness", "Robustness"]
# In a LaTeX-bound source "--" is an EN dash, which is correct typography for a range (7--17, 2016--2018),
# a pair of names (Newey--West) and a two-term compound (long--short). Only "---", "—" and a spaced " -- "
# are the all-purpose joint the em-dash category is about, so these three forms are neutralized first.
EN_DASH_COMPOUNDS = ["long--short", "short--long", "risk--return", "mean--variance", "bid--ask", "cross--section"]
CONNECTIVE_OPENERS = (r"Moreover|Furthermore|Additionally|Notably|Importantly|Crucially|Critically|Interestingly|"
                      r"Ultimately|Overall|Consequently|Specifically|Conversely|In particular|Taken together|"
                      r"In sum|In summary|In essence|In short|Together, these|Put differently|Put simply")

SENT_START = r"(?:^|(?<=[.!?:])\s+|(?<=\*\*)\s*)"   # start of line, after sentence end, or after a bold label


@dataclass(frozen=True)
class Cat:
    key: str
    severity: str      # FIX | WATCH
    label: str
    pattern: str       # regex on masked prose
    per_1k_max: float  # threshold (FIX: hard; WATCH: advisory); 0 = any hit counts
    flags: int = 0


CATEGORIES: list[Cat] = [
    Cat("em_dash", "FIX", "em dash (—, --- or --) used as a joint", r" ?(?:—|---|(?<=\w)--(?=\w)|(?<=\s)--(?=\s)) ?", 3.0),
    Cat("spaced_en_dash", "WATCH", "spaced en dash used as a dash (Elsevier house style)", r" – ", 3.0),
    Cat("arrow_prose", "FIX", "arrow character in running prose", r"[→⇒⟵⟶←↔⇐⇔➔➜]", 0.0),
    Cat("ellipsis_char", "FIX", "ellipsis character (…) in prose", r"…", 0.0),
    Cat("symbol_prose", "FIX", "check marks / stars / bullets / emoji in prose", r"[✓✔✗✘✦★☆•▪◦]|[\U0001F300-\U0001FAFF☀-⛿]", 0.0),
    Cat("odd_unicode", "FIX", "invisible / non-breaking characters", r"[‑ ​‌‍﻿]", 0.0),
    Cat("ban_words", "FIX", "LLM-signature vocabulary", r"\b(?:" + "|".join(BAN_WORDS) + r")\b", 0.0, re.I),
    Cat("not_only", "FIX", "'not only … but also'", r"\bnot (?:only|just|merely)\b[^.;]{0,80}?\bbut(?: also)?\b", 0.5, re.I),
    Cat("connective_opener", "WATCH", "sentence opening with a stock connective", SENT_START + r"(?:" + CONNECTIVE_OPENERS + r")\b,?", 4.0),
    Cat("contrast_negation", "WATCH", "'not X but/rather Y' contrast", r"\b(?:not|no|never)\b[^.;:!?]{2,60}?\b(?:but|rather)\b", 3.0, re.I),
    Cat("watch_words", "WATCH", "vocabulary common in LLM prose (also in human prose)", r"\b(?:" + "|".join(WATCH_WORDS) + r")\b", 8.0, re.I),
    Cat("this_verb_opener", "WATCH", "sentence opening 'This suggests/means/…'", SENT_START + r"This (?:suggests|means|implies|indicates|highlights|underscores|shows|matters|is (?:not|the|what|why|where))\b", 3.0),
    Cat("triad", "WATCH", "three-item parallel list of single words", r"\b\w+, \w+,? and \w+\b", 4.0),
    Cat("semicolon", "WATCH", "semicolons", r";", 5.0),
    Cat("rhetorical_q", "WATCH", "question in body text (Q-then-answer pattern)", r"[^\n?]{12,}\?(?=\*\*|\s|$)", 1.0),
    Cat("bold_runin", "WATCH", "paragraph opening with a bold run-in label", r"(?m)^\*\*[^*\n]{2,80}\*\*[:.]?\s", 4.0),
]
BY_KEY = {c.key: c for c in CATEGORIES}


RAW_ENV = r"(tikzpicture|center|figure|table|tabular|adjustbox|algorithm|algorithmic|minipage|equation|align)"


def prose_of(text: str, allow: list[str] | None = None) -> list[tuple[int, str]]:
    """(line_no, masked_line) for prose lines only. Tables, code, display math, images, comments, raw
    LaTeX blocks and command lines, the References section and ATX headings are dropped; inline
    math/code, citation groups, cross-references, en dashes and allowed phrases masked with spaces."""
    allow = ALLOW_PHRASES if allow is None else allow
    out, in_code, in_refs, in_math, env_depth = [], False, False, False, 0
    for i, ln in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if s.startswith("$$"):
            if s == "$$" or not s.endswith("$$") or len(s) == 2:
                in_math = not in_math
            continue
        # raw LaTeX passed through pandoc: a tikzpicture's \draw lines end in ";" and its node text is
        # markup, not prose. Depth-counted because these environments nest (center > tikzpicture).
        if re.match(r"\\begin\{" + RAW_ENV, s):
            env_depth += 1
            continue
        if re.match(r"\\end\{" + RAW_ENV, s):
            env_depth = max(0, env_depth - 1)
            continue
        if in_code or in_math or env_depth:
            continue
        if s.startswith("#"):
            in_refs = bool(re.match(r"#+\s*References\b", s))
            continue
        # a line of exactly "---" is a YAML front-matter fence or a horizontal rule, never prose
        if in_refs or not s or s == "---" or s.startswith("|") or s.startswith("![](") or s.startswith("<!--") or s.startswith("\\"):
            continue
        # en dashes first, on the raw line: a range written as $0.49$--$0.69$ loses its digits once the
        # inline math is blanked, and would then read as a spaced joint
        masked = re.sub(r"(?<=\d)--(?=\d)|(?<=\$)--(?=\$)", "  ", ln)                      # 7--17, $0.49$--$0.69$
        masked = re.sub(r"\b([A-Z][A-Za-z'’]+)--(?=[A-Z][A-Za-z'’]+\b)", r"\1  ", masked)  # Newey--West
        for compound in EN_DASH_COMPOUNDS:
            masked = masked.replace(compound, compound.replace("--", "  "))
        masked = re.sub(r"\$[^$\n]+\$", lambda m: " " * len(m.group(0)), masked)
        masked = re.sub(r"`[^`\n]+`", lambda m: " " * len(m.group(0)), masked)
        # (Author Year; Author Year) groups: their semicolons and dashes are bibliographic, not prose
        masked = re.sub(r"\((?:[^()]*?\b(?:19|20)\d{2}[a-z]?)[^()]*\)", lambda m: " " * len(m.group(0)), masked)
        # pandoc's [@key1; @key2] form of the same thing, and \ref{}/\S\ref{} cross-references
        masked = re.sub(r"\[@[^\]]*\]", lambda m: " " * len(m.group(0)), masked)
        masked = re.sub(r"\\(?:S?ref|eqref|cref|Cref|autoref)\{[^}]*\}", lambda m: " " * len(m.group(0)), masked)
        for phrase in allow:
            masked = masked.replace(phrase, " " * len(phrase))
        out.append((i, masked))
    return out


def word_count(prose: list[tuple[int, str]]) -> int:
    return sum(len(re.findall(r"[A-Za-z][A-Za-z'’\-]*", ln)) for _, ln in prose)


def scan_text(text: str, keys: list[str] | None = None,
              allow: list[str] | None = None) -> dict[str, list[tuple[int, str]]]:
    """{category_key: [(line_no, matched_text), ...]} over the prose of `text`."""
    prose = prose_of(text, allow)
    hits: dict[str, list[tuple[int, str]]] = {}
    for cat in CATEGORIES:
        if keys and cat.key not in keys:
            continue
        rx = re.compile(cat.pattern, cat.flags)
        found = []
        for ln_no, ln in prose:
            for m in rx.finditer(ln):
                found.append((ln_no, m.group(0)))
        hits[cat.key] = found
    return hits


def summarize(text: str, allow: list[str] | None = None) -> dict:
    prose = prose_of(text, allow)
    words = word_count(prose)
    hits = scan_text(text, allow=allow)
    rows = {}
    for cat in CATEGORIES:
        n = len(hits[cat.key])
        per_1k = 1000.0 * n / max(words, 1)
        over = (n > 0) if cat.per_1k_max == 0 else (per_1k > cat.per_1k_max)
        rows[cat.key] = {"severity": cat.severity, "label": cat.label, "count": n,
                         "per_1k": round(per_1k, 2), "max_per_1k": cat.per_1k_max, "over": over}
    return {"words": words, "categories": rows}


def report(path: Path, summ: dict) -> str:
    lines = [f"{path}  ({summ['words']} prose words)",
             f"  {'category':20s} {'sev':5s} {'count':>5s} {'/1k':>6s} {'max':>5s}  flag"]
    for key, r in summ["categories"].items():
        flag = "OVER" if r["over"] else ""
        lines.append(f"  {key:20s} {r['severity']:5s} {r['count']:5d} {r['per_1k']:6.1f} {r['max_per_1k']:5.1f}  {flag}")
    return "\n".join(lines)


def load_allow(path: str | None) -> list[str]:
    """ALLOW_PHRASES plus one phrase per non-empty, non-# line of the project's allow file."""
    extra = []
    if path:
        for ln in Path(path).read_text(encoding="utf-8").splitlines():
            if ln.strip() and not ln.lstrip().startswith("#"):
                extra.append(ln.strip())
    return ALLOW_PHRASES + extra


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--list", dest="list_key", metavar="CATEGORY")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--allow-file")
    args = ap.parse_args(argv)
    if not args.files:
        print(__doc__)
        return 2
    if args.list_key and args.list_key not in BY_KEY:
        print(f"unknown category {args.list_key}; choose from {list(BY_KEY)}")
        return 2
    allow = load_allow(args.allow_file)
    worst = False
    out_json = {}
    for f in args.files:
        text = f.read_text(encoding="utf-8")
        if args.list_key:
            for ln_no, m in scan_text(text, [args.list_key], allow)[args.list_key]:
                print(f"{f}:{ln_no}: {m.strip()}")
            continue
        summ = summarize(text, allow)
        out_json[str(f)] = summ
        if not args.json:
            print(report(f, summ))
            print()
        worst |= any(r["over"] and r["severity"] == "FIX" for r in summ["categories"].values())
    if args.json:
        print(json.dumps(out_json, indent=1, ensure_ascii=False))
    return 1 if (args.strict and worst) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
