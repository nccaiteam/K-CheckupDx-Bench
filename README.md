# K-CheckupDx-Bench

A benchmark for **tiered determination** in the Korean National Health Screening Program
(국가건강검진), built entirely from published criteria and shipped with a deterministic rule engine
that re-derives every gold label.

Given a test item, unit, sex, and result value, a system must assign the program's tier —
정상A (normal A) / 정상B (borderline) / 질환의심 (suspected disease), or item-specific labels such as
정상 / 복부비만 (abdominal obesity).

> **Scope.** Public-standard track only. This repository contains no institution-specific
> determination master.

---

## Why another benchmark

Existing Korean medical LLM benchmarks are built from licensing examinations and measure knowledge
recall. This task is different: thresholds are explicit, boundary semantics (whether a cutoff is
inclusive) are clinically consequential, and a one-directional error — calling a suspected-disease
result normal — translates into missed follow-up at population scale.

Two design choices follow from that:

**1. A label-independent primary metric.** The **monotonicity violation rate** is the proportion of
ordered value pairs in which a model gives a *less severe* tier to a *clinically worse* value. Such
a pair is self-contradictory under any threshold table, so the metric survives disagreement about
which criteria table is correct — the single largest source of dispute in this domain.

**2. A shipped audit trail.** During development, two benchmark design artifacts each reversed a
between-model conclusion. Both corrections, and the reasoning, are documented in
[`data/DATA_CARD.md`](data/DATA_CARD.md §5). We ship this history because "benchmark fragility" is
one of our findings, not an embarrassment to hide.

## Contents

```
data/     pubset_v1.0.jsonl        144 tier cases, 20 items (boundary 77, inclusive-threshold 32)
          pubset_ladder_v1.1.jsonl 370 cases / 3,066 pairs (development version, audit trail)
          pubset_ladder_v1.2.jsonl 530 cases / 6,352 pairs (development version, audit trail)
          pubset_ladder_v1.3.jsonl 528 cases / 6,321 ordered pairs, 22 value ladders
          pubset_bmi_3cond.jsonl    54 cases /   514 pairs (BMI source-ambiguity experiment)
          DATA_CARD.md             schema, verification, version history + confound audit
src/      run_pilot.py             runner (anthropic / openai / mock rule engine)
          score_pilot.py           tier accuracy, boundary gap, safety-critical errors
          score_monotonicity.py    monotonicity violations, BMI stratum, enrichment, run agreement
          score_bootstrap.py       cluster (by-ladder) bootstrap for between-model differences
          score_mcnemar.py         exact McNemar for the grounding effect (majority-vote based)
          prompts.md               prompt definitions and design rationale
results/  result files from all reported runs, including development-phase runs (v1.1, v1.2), the v1.0 pilot, and the replication runs
figures/  pipeline and results figures
```

## Conditions

Three system-prompt conditions, selected with `--mode`:

| Mode | What the model is given |
|---|---|
| `zeroshot` | The task and the permitted options only |
| `named` | Told *which* criteria to apply (별표4) but **not** the table itself |
| `grounded` | The verbatim criteria table |

The `named` condition separates *criteria recall* from *numeric comparison*: if naming the source
alone restores accuracy, the failure was choosing the wrong standard, not comparing numbers.

## Reproducing

```bash
pip install -r src/requirements.txt
export ANTHROPIC_API_KEY=...   # for --provider anthropic
export OPENAI_API_KEY=...      # for --provider openai
```

**Always start with the rule-engine self-check** (no API key needed). It must return 100% tier
accuracy and 0 monotonicity violations; anything else means a broken environment, not a finding:

```bash
python src/run_pilot.py --provider mock --model rule-engine --mode zeroshot \
    --input data/pubset_ladder_v1.3.jsonl
python src/score_monotonicity.py results_rule-engine_zeroshot_ladder_v1.3.jsonl
```

Then evaluate a model. **Use at least 10 runs** — see *Reporting policy* below:

```bash
python src/run_pilot.py --provider anthropic --model <model> --mode zeroshot \
    --input data/pubset_ladder_v1.3.jsonl --runs 10
python src/score_monotonicity.py results_<model>_zeroshot_ladder_v1.3_run{1..10}.jsonl
```

Runs resume by `case_id`: re-running an interrupted condition continues where it stopped. To redo a
condition from scratch, delete its result file first.

`score_monotonicity.py` refuses to compute run agreement across mixed conditions — pass only runs of
the same model and mode.

## Reporting policy

These are not style preferences; each one exists because violating it produced a wrong answer
during development.

1. **Never report a single run.** Report mean ± SD across runs, plus a 95% CI for the mean. Decoding
   cannot be made deterministic for current frontier models, and one model's 3-run mean differed
   from its 10-run mean by enough to flip a significance test.
2. **Use ≥10 runs.** Run-to-run SD does *not* shrink as you add runs — only the standard error of
   the mean does. Judge stability with **SEM > mean/4**, not SD-based rules, which are unsatisfiable
   for rare-event rates.
3. **Match run counts when comparing reproducibility.** Flip rate increases monotonically with the
   number of runs, so a 10-run model looks worse than a 3-run model for free.
4. **Report BMI as its own stratum.** Pooling it hides opposing failure modes: in our runs one model
   was significantly worse on BMI and the other significantly worse on everything else, and the
   aggregate metric showed *no difference at all* (p=0.99).
5. **Cluster your bootstrap by ladder.** The 6,321 pairs derive from 528 cases in 22 ladders and are
   not independent.
6. **Audit for confounds before trusting a between-model difference.** See `DATA_CARD.md` §5.

## Citation

⟦TBC: repository DOI (Zenodo) and the accompanying article, once available.⟧

```bibtex
@misc{kcheckupdx_bench,
  title  = {K-CheckupDx-Bench: a benchmark for tiered determination in the
            Korean National Health Screening Program},
  year   = {2026},
  url    = {https://github.com/<OWNER>/K-CheckupDx-Bench},
  note   = {Version 1.0}
}
```

## Licensing

- **Code** (`src/`): MIT — see [`LICENSE`](LICENSE)
- **Data** (`data/`): CC BY 4.0, with source attribution to the Ministry of Health and Welfare
  notification — see [`LICENSE-DATA.md`](LICENSE-DATA.md)

## Disclaimer

Research and evaluation use only. Not a medical device, not clinical decision support, and not a
substitute for professional judgment. Tier labels here are benchmark ground truth derived from
published criteria; they are not medical advice for any individual.
