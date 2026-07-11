# Experimental rigor protocol

Use this before authorizing the full matrix and again when reporting results. Adapt the design to the scientific question; do not apply a statistical test by habit.

## Prospective design

- State the estimand, unit of analysis, primary endpoint, secondary endpoints, and directional hypotheses before inspecting final test results.
- Justify sample size by power, precision, or a defensible resource-constrained sensitivity analysis. Report the assumptions and smallest effect of interest.
- Pre-specify inclusion/exclusion rules, stopping rules, data splits, seed/run counts, and the family of comparisons subject to multiplicity control.
- Freeze the test set and grader before tuning. For temporal targets, split by time; otherwise use entity/group-disjoint splits whenever repeated entities could leak.
- Register the plan publicly when the field and stakes warrant it; otherwise commit a timestamped analysis plan in the project.

## Estimation and uncertainty

- Lead with effect sizes and confidence or credible intervals, not p-values alone.
- Match inference to dependence: paired tests for paired evaluations; cluster, block-bootstrap, HAC, hierarchical, or repeated-measures methods when observations are not independent.
- Name the interval/test method and its assumptions. Report the number of independent units, not only rows or prompts.
- Define the multiple-testing family in advance and choose one appropriate control for its goal, such as FWER, FDR, a permutation/max-statistic method, or a domain-specific correction. Do not present methods as interchangeable.
- Report all planned conditions and all attempted tuning trials relevant to selection. Distinguish exploratory from confirmatory analyses.
- Treat negative and null results as results; give intervals or sensitivity bounds rather than interpreting “not significant” as equivalence.

## ML and LLM evaluation

- Record dataset version, license, split construction, preprocessing, contamination/deduplication checks, metric implementation, environment, compute, and every seed.
- For API models, record provider, exact model snapshot/version, access date, system/user prompts, tool definitions, decoding parameters, output limits, retries, and sampling count.
- Evaluate stochastic systems with enough independent repeats to characterize variance; do not treat repeated samples from one item as independent items.
- For LLM-as-judge, calibrate against blinded human labels, report agreement and position/order bias checks, keep judge and candidate identities separated where possible, and include robustness to at least one alternative judge or scoring method.
- For benchmarks at contamination risk, document cutoff assumptions, leakage probes, and any held-out/private evaluation.

## Human-subject evaluation

- Preserve task instructions, recruitment criteria, compensation, consent, exclusions, randomization/blinding, and rater training.
- Record ethics/IRB determination where applicable and protect sensitive data.
- Report rater counts, assignment structure, inter-rater reliability with an appropriate uncertainty estimate, adjudication, and missing-data handling.

## Minimum experiment record

The run manifest must link the timestamped plan, immutable config, code/data versions, environment, raw outputs, usage/cost ledger, exclusion log, and analysis script. The paper’s main text retains the design facts needed to judge the primary result: independent sample size, seed/run count, split, primary metric, effect and interval, and multiplicity rule. Put exhaustive configuration details in the appendix or artifact.
