# Venue landscape — rankings, the AI / finance map, fees & disclosure

Reference for `research-venue-selection`. Principle-focused on purpose: **specific deadlines, fees, and acceptance rates change every cycle** and go stale fast, so this file gives the *ranking systems*, the *venue map*, and *where to look* — the live numbers come from the host's web-search/page-fetch tools against the official current-cycle CFP. Stamp `as_of` on anything you record.

## Ranking systems (cite the source + year)

**CS / AI**
- **CORE** rankings (A*/A/B/C) — conferences; the common CS-conference standard. <https://portal.core.edu.au/conf-ranks/>
- **CCF** ranking (A/B/C) — China Computer Federation; widely used, sometimes differs from CORE.
- **Google Scholar Metrics** h5-index — empirical influence per venue (Scholar → Metrics → subcategory).
- **Acceptance rate** — report it; a low rate at an A* venue sets expectations for revision rounds and resubmission risk.

**Finance / economics**
- **ABS / AJG** Academic Journal Guide (4*/4/3/2/1) — the dominant business-school ranking. <https://charteredabs.org/academic-journal-guide/>
- **FT50** — the Financial Times research list (tenure/prestige signal at business schools).
- **The "top-3" finance convention**: *Journal of Finance* (JF), *Journal of Financial Economics* (JFE), *Review of Financial Studies* (RFS). Top-5 econ (AER, ECMA, JPE, QJE, REStud) for econ-leaning work.
- **Impact factor / CiteScore** — secondary; field-relative, gameable, use with the above not instead.

Rank is a constraint, not the goal: a strong-fit A venue beats a weak-fit A* one (desk-reject risk). State the rank *and* its source/year in the plan.

## The venue map (where each contribution type goes)

- **AI/ML method** → NeurIPS, ICML, ICLR (top); AAAI, AISTATS, UAI, KDD; ACL/EMNLP (NLP), CVPR/ICCV/ECCV (vision). Mostly **double-blind**, hard deadlines, ~8-page limits, code/checklist expectations.
- **Benchmark / survey / datasets** → NeurIPS Datasets & Benchmarks track, *TMLR* (rolling, no page limit), survey venues (ACM Computing Surveys, *Foundations & Trends*).
- **Empirical / theoretical finance** → JF, JFE, RFS (top-3); *Review of Asset Pricing Studies*, *Journal of Financial & Quantitative Analysis* (JFQA), *Management Science* (finance dept.). **Rolling** submission, **long** reviews (often 6–18+ months), single-blind or double-blind varies, sometimes **submission fees**.
- **AI × finance bridge** → *two distinct tracks*, name both: (a) ML venues with a finance application framing (NeurIPS, ICML, ICAIF — the ACM Intl. Conf. on AI in Finance), and (b) finance journals with an ML method (JFE/RFS increasingly publish ML; *Journal of Financial Data Science*). They want different things — ML venues reward the method/novelty, finance journals reward economic significance + overfitting controls. Pick the track that matches the paper's *primary* contribution; the other is a fallback with a reframe.
- **Workshops / preprints** → arXiv (the main draft goes here regardless), NeurIPS/ICML workshops (early feedback, non-archival, low cost) — useful waypoints when the main venue's deadline is far.

## Conference vs journal (shapes the timeline)

- **Conferences**: fixed annual deadlines (miss it → wait a year), fast-ish decisions (~2–4 months), strict page limits, often double-blind, camera-ready + (sometimes) registration tied to publication.
- **Journals**: rolling submission, **long** and **variable** review (months to >1 year), revise-and-resubmit cycles, page limits looser. Better when the finishing date doesn't line up with a conference cycle.

Match to the **estimated finishing date**: if a top conference deadline is reachable with margin, target it; if not, either aim the next cycle, a rolling journal, or a workshop waypoint — and log the decision.

## Fees & cost (feed into tracking)

Treat every fee as a *verify-the-current-number* item; ballparks only:
- **ML conferences**: no submission fee, but **registration** (often required to publish) ~$X00–$1k+, plus travel.
- **Finance journals**: **submission fees** are common (e.g. JF/JFE/RFS historically ~$100–$250) and sometimes desk-reject-and-keep.
- **Open access / APC**: gold-OA article processing charges can be **$1k–$4k+**; many venues offer waivers.
Record the chosen venue's fee in `cost.json.actuals` as `category: "publication"` (see `research-tracking`) — a separate fixed line, outside the experiments cap.

## Disclosure & preprint cautions

- **Double-blind**: most ML venues. Anonymize the submission (no author names, no self-revealing links/acknowledgements); check the venue's preprint policy — many allow an arXiv post but some restrict citing/advertising it near the deadline (de-anonymization risk).
- **Dual-submission**: simultaneous submission to two archival venues is forbidden almost everywhere — the priority chain is *sequential*, not parallel.
- **Ethics / artifact / reproducibility**: NeurIPS-style checklists, artifact-evaluation tracks, data/ethics statements — these are prerequisites, not afterthoughts; budget time for them.

Cross-checks: the **IP mask-the-recipe-never-the-evidence** rule for what's posted publicly lives in `research-writing` (short-version-guide); recency/verification discipline mirrors `research-references`.
