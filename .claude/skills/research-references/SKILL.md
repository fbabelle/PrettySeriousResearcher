---
name: research-references
description: Verify that every citation resolves to a real, current-status source whose content supports the claim; cover canonical origins and current work; drop unverifiable support, re-cite corrected work. Use when adding citations or reviewing related work.
---

# Research references — anti-hallucination citation gate

LLMs invent plausible-looking citations: real-sounding titles, real authors, wrong or nonexistent papers. This skill makes that impossible to ship by **forcing every reference through verification before it can be cited**. The rule is simple: *a citation that cannot be resolved to a real source whose content supports the claim does not go in the paper.*

Run this whenever citations are added or a related-work / bibliography section is built or reviewed (Phase 1 prior-art, Phase 4 writing). Use the host agent's current web-search and page-fetch tools for discovery; this skill owns verification and the verdict.

## The per-reference protocol (apply to EVERY citation)

For each proposed reference — and each in-text claim that needs one — work through these in order. Do not skip ahead; an early failure is itself the verdict.

1. **Resolve a real link.** Search for a resolvable identifier — DOI, arXiv ID, ACL Anthology / OpenReview / Semantic Scholar / publisher URL, or SSRN/NBER for finance. **Investigate until you find a link or have genuinely exhausted reasonable searches.** Do not stop at "this sounds like a real paper."
2. **Confirm it exists as cited.** Title, authors, year, and venue must match the citation. A near-match (right authors, wrong year; right title, wrong venue) is a *defect to correct*, not a pass — fix the metadata to the resolved source. **Author-collision check:** when a surfaced work's author list matches one of the project's own authors, confirm with the user whether it is theirs before using it as *independent* evidence — self-citations are fine but must be labelled as such (and anonymized per venue rules).
3. **Verify content.** Fetch the abstract (and the relevant section if the claim is specific). Confirm the source **actually supports the specific claim** it's attached to. Topical overlap is **not** support — "uses transformers" ≠ "shows transformers beat LSTMs on this task." If the source doesn't say what the citation implies, the citation is wrong even if the paper is real.
4. **Verify relevance.** The work must be relevant to *this* paper's specific claim/context, not merely to the broad field. A correct-but-irrelevant citation is padding — drop it.
5. **Check coverage, currency, and status.** Do not exclude a relevant work because of age. Cover the canonical origin when it matters, the closest prior work, and current representative work or a recent synthesis. Check the version of record plus corrections, expressions of concern, retractions, and material superseding results. See [references/recency-and-seminal.md](references/recency-and-seminal.md).

**Treat every entry written from memory or from your own design notes as unverified until its abstract has been opened.** The dangerous failure is not an invented identifier — those are caught the moment anything resolves them — but a *real* identifier under a title that was a working label during drafting: it survives every syntactic check, every "does this look like a real paper" review, and reaches the referee intact. Re-derive title, authors, year and venue *from the fetched page* and overwrite the entry, even when the entry looks right; a bibliography pass that confirms entries rather than rebuilding them will confirm the fabrication. Then re-read every *citation context*: an entry whose subject turns out to be different usually sits inside a sentence that now says something false about the literature (earned 2026-09-14: 20 of 20 checked entries needed correction; one carried an invented title over a real arXiv id and had been cited both as a member of a research lane it does not belong to and as leaving open a question it in fact answers). Delegating this to an agent that actually fetches each abstract is cheap and is the only check that finds it.

**Verification has two halves, and the second fails when the first is clean.** The *entry* (exists, matches the version of record) and the *citation context* (the cited work actually contains the attributed claim) are separate checks with separate failure modes; a bibliography in which every entry is exact can still carry contexts that are false. The three recurring shapes: a count or finding from your own scan attributed to the papers the scan covered (attribute your own counts to your own scan, in the paper's voice); a lesson attributed to the paper whose method failed rather than to the paper that showed it fails; a paper cited for a discipline it never discusses because it is adjacent to one it does. Verify contexts as a pass of their own, sentence by sentence, not as a by-product of fixing entries (earned 2026-09-15: 26 of 26 entries exact, 3 contexts false). **A fetch tool's summary is not the source:** when a specific attribution (a number, a named counterexample) is not confirmed by the summariser's reply, extract the PDF text and search it before ruling the context false; a "not found" reply for a counterexample with $\mathbb{E}[M]=1.25$ was wrong, and the passage sat in the paper's supplementary appendix (earned 2026-09-22). **A method's name must appear in the version cited for it.** Preprint and journal versions of one line of work can define different methods under different names; a rule cited by name to the journal paper was defined only in the earlier arXiv report (LOND in the 2015 preprint, LORD in the 2018 journal version), so search the cited text for the name before attaching it, and cite the preprint alongside when the name lives only there (earned 2026-09-25).

## Coverage, not an age cutoff

A sound related-work set normally includes both **canonical origins** and **current evidence**. Older work can remain the best source for an original method, theorem, dataset, or economic result; newer work is needed to establish today's comparison set, replications, limitations, and state of the art. Age alone is neither a pass nor a failure. When a newer paper changes or disputes an older claim, cite both and describe the relationship accurately.

**A "no prior work does X" sentence is re-searched whenever the target venue changes community.** Related work assembled for one community is written in that community's vocabulary and misses the other's: retargeting an applied-finance paper to an ML venue turned up an ICML paper doing the closest thing to X under different words (agentic falsification with sequential e-values), which the introduction's "no prior system" sentence contradicted. Before the claim survives a retarget, search the target community's proceedings in its own vocabulary, and position the closest hit rather than dropping the sentence silently (earned 2026-09-25).

## Verdicts (assign one per reference)

| Verdict | Meaning | Action |
|---|---|---|
| **VERIFIED** | Real, resolved, relevant, and the content supports the claim | Cite it; record the resolved identifier and version of record |
| **CANONICAL** | VERIFIED and the appropriate origin or standard source | Cite it alongside current evidence when the claim concerns present practice |
| **SUPERSEDED/CORRECTED** | Real, but a later version or notice materially changes the relevant claim | Cite the current record and explain the change; do not repeat the obsolete claim |
| **RETRACTED** | The work is retracted or its relevant result is invalidated | Do not use it as supporting evidence; mention only when the retraction itself is relevant |
| **UNVERIFIABLE** | No resolvable link after real effort, metadata cannot be matched, or content does not support the claim | **Remove. Never cite as support.** Flag it and find a valid source if the claim remains |

**VERIFIED** and **CANONICAL** entries may support claims; **SUPERSEDED/CORRECTED** or **RETRACTED** items enter only when their status is explicitly material to the discussion. An **UNVERIFIABLE** verdict is not a failure of the paper — it's the gate working; tell the user which proposed citations were dropped and why, and (if the claim still needs support) search for a real source that does support it.

## Output: the citation audit

Produce a table the user can scan, then update the BibTeX with only the passing entries:

```
| Cite key | Claim it supports | Resolved link | Year | Verdict | Note |
|----------|-------------------|---------------|------|---------|------|
```

Maintain the BibTeX with the **resolved** identifiers (DOI/arXiv), not the originally-proposed strings, so every entry is traceable.

## Anti-padding (shared with research-reflection)

Don't inflate the bibliography to look thorough. A lean set of verified, relevant, correctly-supporting citations beats a long list with one fabricated entry — a single hallucinated reference can sink a paper's credibility. It is fine to conclude a claim needs no citation, or that the right citation doesn't exist yet (state the claim as the paper's own contribution instead).

## The running evidence ledger (one literature pass, two consumers)

Don't hit the literature twice. The **same** literature pass that powers the Phase-1 **novelty-gap scan** should **harvest the citations** it surfaces into a running, append-only **claim → source ledger** carried from prior-art through experiments into writing. Each ledger entry is an atomic, source-tagged learning (dense with the numbers/dates/entities that make it load-bearing), so the ledger is both the input to synthesis *and* the backing the bibliography draws from.

- **Cross-source corroboration for load-bearing claims.** A claim the paper leans on should resolve to **more than one independent source**, pre-ranked by source authority × frequency × relevance — the strongest-corroborated sources surface first. This is *added on top of* the content-check, **never a substitute**: a claim agreed on by many low-quality pages still fails the content-check bar (this is why the majority-vote heuristic some search/synthesis tools use is too weak for us).
- **Keep it light.** This is a **single-paper, in-context ledger with one dedup pass** — *not* a heavyweight vector/RAG index or a cross-run knowledge store. The value is one clean literature pass reused, not new infrastructure.

## Cross-references

- **research-writing** — invokes this for the references section and the final bibliography; Phase-4 exit requires a clean citation audit.
- **research-topic-selection** — invokes this when citing prior art / building related work in Phase 1.
- **research-paper** — orchestrator; the Phase-4 exit criteria include this audit.
- **Host web-search/page-fetch tools** — discover and fetch candidate sources; prefer version-of-record and primary sources.
- **research-reflection** — shares the anti-padding / don't-manufacture principle.
