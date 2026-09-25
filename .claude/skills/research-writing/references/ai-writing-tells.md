# Machine-writing tells: what editors notice, how to measure it, how to remove it

Reference for `research-writing` (final polish) and `research-submission` (pre-upload check). Companion
tools shipped with this skill: `scripts/ai_style_scan.py` (measure) and `scripts/ai_style_rewrite.py`
(Codex-driven removal behind a structural guard).

**Why this matters.** A desk-triage editor spends minutes on the first pages. Prose that carries the
punctuation and vocabulary habits of LLM output is read as "generated", and generated prose is read as
unreviewed. It is a cheap, silent reason to decline without review, and it stacks on top of every other
first-page signal. The tells below are measurable, so remove them mechanically before anyone reads the draft.

## 1. The tells, with human-prose reference bands

Densities are per 1,000 prose words (tables, code, math, figure lines and the reference list excluded;
citation groups masked). A project's defined labels that collide with the vocabulary list go in an allow
file (`--allow-file`, one phrase per line) rather than into the scanner. Bands are what human-written finance / ML papers typically show; treat them as
targets, not laws.

| Tell | Human band | What LLM drafts do | Fix |
|---|---|---|---|
| **Em dash** (`—`, `--`) as an all-purpose joint | 1–3 /1k, rarely two in a sentence | 12–20 /1k, most paragraphs, often spaced (`word — word`) | Recast per joint: comma pair for a light aside, parentheses for a true parenthetical, colon for an expansion, full stop for an independent clause, "that is / because / which / while" where that is the relation. Keep ≤3 /1k. Then pick one convention: closed `word—word` (Chicago/US) or spaced en dash `word – word` (Elsevier/British house style). Never the spaced em dash. |
| **Semicolon chains** | 2–5 /1k | 10–16 /1k | Split independent halves into sentences. Keep only between list items that contain commas and inside citation groups. |
| **Arrows in running prose** (`→ ⇒ ↔ ⟵`) | 0 | "0.37 → 0.67", "A → B", stage chains `a→b→c` | Write the relation: "from 0.37 to 0.67", "A to B", "structured versus autonomous"; stage chains hyphen-joined (`gather-analyze-decide-execute-reflect`). Legends that define table symbols stay. |
| **Ellipsis character** (`…`) in prose or numeric ranges | 0 | "−0.07…0.08" | "−0.07 to 0.08"; keep only inside quoted machine output. |
| **Symbols in prose**: ✓ ✗ ✦ • emoji | 0 | check-mark lists, starred asides | Words; a symbol that names a table footnote (✦ † ‡) stays. |
| **Invisible / odd Unicode**: U+2011 non-breaking hyphen, U+00A0, zero-width joiners | 0 | pasted from chat UIs | Replace with plain hyphen/space. |
| **Signature vocabulary** | 0 | delve, tapestry, testament, realm, landscape, pivotal, crucial(ly), underscore(s), showcase, leverage (= use), seamless, holistic, multifaceted, nuanced, robust (as praise), foster, bolster, elucidate, meticulous, intricate, actionable, "it is worth noting", "in today's", "sheds light", "paves the way", "bridges the gap", "at the intersection of", "stands as / serves as a", "in summary / in conclusion / taken together" | Plain word with the same meaning. Keep technical senses: leverage (finance), elevated (VIX), robustness (statistics), a label the paper defines. |
| **"not only … but also"**, **"not X but Y"**, **"It is not X; it is Y"** | ≤0.5 /1k, ≤3 /1k | dense | State the positive claim; keep the contrast only where the negation is the point. |
| **Stock sentence openers**: Moreover, Furthermore, Additionally, Notably, Importantly, Crucially, Interestingly, Ultimately, "Together, these" | ≤4 /1k | every second paragraph | Delete or replace with the concrete link ("Because …", "The same run also …"). |
| **"This suggests / This means / This highlights"** summarizing openers | ≤3 /1k | paragraph-final punchlines | Attach the subject: "The gap suggests …". |
| **Triads** of single words ("fast, cheap, and reliable") | ≤4 /1k | rhythmic triples everywhere | Two items, or the list that is actually true. |
| **Question-then-answer** in body text ("Does it hold? It does: …") | ≤1 /1k outside stated RQs | frequent | Declarative sentence. Formal RQ lists are fine. |
| **Bold run-in labels** (`**Label.** text`) | style choice (≤4 /1k reads as paragraph headings) | every paragraph | Keep only where the labels form a real sequence (RQs, findings, hyperparameters). |
| **Anti-disjoint structure** | — | independently written sections stitched together; repeated summaries (§7 recap = §8.1 = §9) | Write in one pass; one summary location (`research-writing`, anti-disjoint rule). |
| **Uniform sentence length / no first-person judgement** | — | every sentence 20–30 words; no "we chose … because" | Vary length; say what was decided and why. |

Keep the list current: editors' guides (e.g. Wikipedia's *Signs of AI writing*, journal copy-desk notes)
evolve, and so do model habits. Update the `BAN_WORDS` / `WATCH_WORDS` lists in the scanner when a new
tell becomes recognizable.

### 1a. Check the manuscript's dialect before believing the counts

A tell is a habit, not a character. The same character is a habit in one source dialect and correct
typography in another, so read a sample of the hits before acting on a density (earned 2026-09-18: 46 of
47 reported dash hits were correct typography and the real em-dash count was zero).

| Looks like a tell | Is not one when | Why |
|---|---|---|
| `word--word` | the source is bound for LaTeX | `--` is the **en dash**: ranges (`7--17`, `2016--2018`, `$0.49$--$0.69$`), name pairs (`Newey--West`), two-term compounds (`long--short`). The joint is `---` or `—`, and a spaced ` -- `. |
| `;` in `[@key1; @key2]` | the source is pandoc markdown | Bibliographic, like `(Smith 2021; Lee 2023)`. Mask both forms. |
| `;` at the end of most lines of a block | the block is raw LaTeX | Every tikz `\draw`/`\node` statement ends in `;`. Drop `\begin{…}`/`\end{…}` environments and `\`-leading lines. |
| `;` inside `![Caption](path){#fig:x}` and a `: Table caption` line | — | It is prose, so the **scanner** should count it, but the **rewriter** must not edit the line (it carries the path, the label and the attributes). Freeze the line and measure the rewrite's target on editable lines only. |
| A semicolon list in a table note or a parameter caption | the items are settings, not clauses | `(cap fraction 0.5; null streams at $\mu=0$; alive streams … target 1260)` reads worse with commas: five numeric settings run together. Human authors use semicolons here. |
| `---` on its own line | it is a YAML front-matter fence or a horizontal rule | Never prose. |

Two rules follow. **Before the pass:** teach the scanner the dialect (its `prose_of` masking) rather than
discounting the hits by hand, or every future edition re-reports them; the shipped scanner already knows
LaTeX-bound markdown (en-dash ranges, name pairs and compounds, raw LaTeX environments, lines that open with a
backslash) and pandoc citations and cross-references. **Before sending anything to the
rewriter:** put whatever the model must not edit into the guard's `skeleton()` — raw LaTeX above all. The
one chunk whose guard tripped on structure in that run had a tikz node restyled from `dat` to `gov`, which
would have drawn the execution-layer box in the governance colour. A style pass reaches everything in the
chunk, including the figures.

## 2. Measure

```
python scripts/ai_style_scan.py drafts/<paper>.md drafts/<supplement>.md   # summary table per file
python scripts/ai_style_scan.py drafts/<paper>.md --list em_dash            # every hit with line numbers
python scripts/ai_style_scan.py drafts/<paper>.md --strict                  # exit 1 if any FIX band is exceeded
```

FIX categories (em dash, arrows, ellipsis, symbols, odd Unicode, signature vocabulary, "not only") must
sit inside their band before submission; WATCH categories are thinned when high. Run it on **every edition**
(main, short, supplement, cover letter, highlights), not just the main text: a supplement or a cover letter
written in one sitting is usually the worst offender.

## 3. Remove without changing meaning

Never do this by hand across a whole manuscript, and never with a blanket search-and-replace (`—` → `,`
produces wrong sentences). Use the section-wise Codex pass with the structural guard:

```
python scripts/ai_style_rewrite.py run    --work drafts/destyle --files drafts/<paper>.md drafts/<supplement>.md
python scripts/ai_style_rewrite.py merge  --work drafts/destyle       # guard + word-level diffs
python scripts/ai_style_rewrite.py review --work drafts/destyle       # independent Codex meaning review
python scripts/ai_style_rewrite.py apply  --work drafts/destyle       # only guard-passing chunks
python scripts/ai_style_scan.py drafts/<paper>.md                     # re-measure
```

The guard rejects any chunk whose headings / table rows / figure lines / code / math are not byte-identical,
whose multiset of numerals, citations and cross-references changed, whose word count moved more than 8 %,
or whose em-dash count did not fall to a quarter. What the guard cannot judge is **meaning**: read every
diff (they are small: a joint, a split sentence, a word) and the reviewer's leads, and revert any sentence
whose hedge, causal reading or emphasis moved. The rewriter is a different model family from the drafter,
which removes self-preference, but its output is a proposal, not an edit.

Derived editions (a short version built from patches, an arXiv version generated from the journal
source) must be de-styled at their **sources** (the living draft and the patch files), then rebuilt, so
the lanes never diverge by hand edits. Rebuild every PDF afterwards; page counts move by ±0.5 page.

**Runner gotcha (all `codex exec` tooling).** A multi-paragraph prompt passed as the argv prompt reaches the
model truncated at its first blank line (observed 2026-09-17 with the Windows codex shim: the model replied
"which habits? they weren't included", and an earlier content gate had silently run on its first paragraph
only). Put the full brief inside stdin ahead of the text (`=== INSTRUCTIONS === … === TEXT === …`) and pass a
one-line pointer as the argv prompt; `ai_style_rewrite.py` and `research-mock-review`'s `mock_review_panel.py`
both do this. Check a run's `.log`: the `user` block should show the whole brief.

## 4. When to run it

- Before the first mock review (`research-mock-review`), so referees react to the science, not the style.
- After every Codex/LLM polish pass (polish passes reintroduce em dashes and "notably").
- As part of the `research-submission` Step-1 artifact audit, on the exact files being uploaded.
