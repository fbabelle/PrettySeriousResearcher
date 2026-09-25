"""Emphasis audit of a markdown draft: every bold (**x**) and italic (*x*) span in the prose, with where it sits and
how the same phrase is treated elsewhere. Flags: italic term re-italicised after its first use (over-use), a term
defined with "is/are/means/call" but never italicised at that first use (under-use), bold used on machinery nouns
rather than claims or run-in labels, mixed treatment of one phrase (bold here, italic there).
Usage: python emph_scan.py drafts/<paper>-part1.md drafts/<paper>-part2.md   (the project's own draft files)"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BOLD = re.compile(r"\*\*(.+?)\*\*")
ITAL = re.compile(r"(?<![*\w])\*(?!\*)([^*\n]+?)\*(?!\*)")


def prose_blocks(text: str):
    fence = False
    for block in text.split("\n\n"):
        s = block.strip()
        if s.startswith("```"):
            fence = not fence if s.count("```") == 1 else fence
            continue
        if fence or not s or s.startswith(("|", "![", ":", "\\", "$$", "---", "#")):
            continue
        yield s


def main(paths) -> int:
    if not paths:
        print(__doc__)
        return 2
    bold, ital = [], []
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        for n, b in enumerate(prose_blocks(text)):
            for m in BOLD.finditer(b):
                bold.append((Path(path).name, n, m.group(1), b[:60]))
            for m in ITAL.finditer(b):
                ital.append((Path(path).name, n, m.group(1), b[:60]))
    print(f"bold spans: {len(bold)}; italic spans: {len(ital)}\n")
    print("== BOLD (all) ==")
    for f, n, s, ctx in bold:
        print(f"  {f}#{n}: **{s}**   [{ctx}...]")
    ic = Counter(s.lower().strip() for _, _, s, _ in ital)
    print("\n== ITALIC phrases used more than once (candidate over-use: a term is italicised at first use only) ==")
    for s, c in ic.most_common():
        if c > 1:
            print(f"  {c}x  *{s}*")
    print("\n== ITALIC single-use phrases (check: term at first use, lead-in label, or stress?) ==")
    for s, c in sorted(ic.items()):
        if c == 1:
            print(f"  *{s}*")
    both = {s for s in ic} & {s.lower().strip() for _, _, s, _ in bold}
    if both:
        print("\n== phrases both bold and italic somewhere ==", both)
    # defined-but-not-italicised: "X is called a Y", "we call this Y", "A Y is ..."
    print("\n== defining sentences whose defined term is not italicised (candidate under-use) ==")
    seen = set()
    for path in paths:
        for b in prose_blocks(Path(path).read_text(encoding="utf-8")):
            for sent in re.split(r"(?<=[.?!])\s+", b):
                if re.search(r"\b(is called|are called|we call|is the name|is defined as|means that)\b", sent) and "*" not in sent:
                    key = sent[:90]
                    if key not in seen:
                        seen.add(key); print("  " + sent[:160])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
