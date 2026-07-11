# Citation coverage, currency, and canonical sources

Reference protocol for `research-references`. Relevance and evidentiary fit control inclusion; age alone does not.

## Build a coverage set

For each load-bearing claim, look for the smallest set that covers the roles that matter:

- **Canonical origin** — the original method, theorem, dataset, or result when attribution matters.
- **Closest prior work** — the most directly comparable method or empirical design.
- **Current evidence** — recent representative work, benchmark leaders, replications, or a current systematic review.
- **Contradictory evidence** — credible failures, null results, corrections, or boundary conditions.
- **Context source** — standards, official statistics, dataset cards, or policy documents when they are the primary authority.

Not every claim needs every role. Record which role each source serves; do not add citations merely to lengthen the bibliography.

## Check currency and publication status

1. Resolve the version of record when one exists; link a preprint as well only when it provides a useful public copy.
2. Check publisher and index records for corrections, expressions of concern, retractions, and newer versions.
3. Verify that datasets, software, standards, laws, leaderboards, and provider specifications are current as of a recorded date.
4. When later work supersedes or disputes an older result, cite both if the change matters and state it explicitly.
5. Prefer systematic reviews or meta-analyses for broad consensus claims, then inspect the primary studies that carry the specific claim.

## Canonical is a role, not an exception

Older work is often the correct source for an origin claim. Label it `CANONICAL` only after verifying that it introduced or standardized the concept; citation count alone is not enough. A canonical source does not establish the present state of the art, so pair it with current evidence whenever the sentence makes a current claim.

## Domain reminders

- **AI/ML:** verify exact model/dataset versions, evaluation protocol, contamination controls, and whether a leaderboard result is directly comparable.
- **Finance/economics:** distinguish theory from evidence; check sample period, market regime, data vintage, corrections, and independent replication.
- **Fast-changing operational facts:** use the official current source and stamp an access or verification date.

## Audit outcome

Use `VERIFIED`, `CANONICAL`, `SUPERSEDED/CORRECTED`, `RETRACTED`, or `UNVERIFIABLE` from the parent skill. Never convert “old” into an automatic rejection and never convert “recent” into evidence of quality.
