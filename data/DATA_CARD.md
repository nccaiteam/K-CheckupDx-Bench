# Data Card — K-CheckupDx-Bench

**Version:** 1.0 (data release) · **Compiled:** 2026-08-26
**Scope:** Public-standard track only. Contains **no** institution-specific determination master.

---

## 1. What this is

Evaluation data for **tiered determination** in the Korean National Health Screening Program:
given a test item, unit, sex, and a result value, assign one of the program's tiers
(정상A / 정상B / 질환의심, or item-specific options such as 정상 / 복부비만).

All criteria derive from **published** sources only — the Ministry of Health and Welfare
notification (건강검진 실시기준 별표4) and open specialty-society standards — so the data are
redistributable. Institution-local extensions are deliberately excluded.

## 2. Files

| File | Cases | Ordered pairs | Purpose |
|---|---|---|---|
| `pubset_v1.0.jsonl` | 144 | — | Tier accuracy. 20 items. Boundary cases 77, inclusive-threshold (`=cutoff`) cases 32 |
| `pubset_ladder_v1.3.jsonl` | 528 | **6,321** | Monotonicity (primary metric). 22 value ladders |
| `pubset_ladder_v1.1.jsonl` | 370 | 3,066 | Development version (audit trail, §5): initial ladder set |
| `pubset_ladder_v1.2.jsonl` | 530 | 6,352 | Development version (audit trail, §5): hemoglobin capped, fillers added |
| `pubset_bmi_3cond.jsonl` | 54 | **514** | BMI source-ambiguity experiment (tier 9 + ladder 45) |

### Fields

| Field | Present in | Meaning |
|---|---|---|
| `case_id` | all | Stable identifier |
| `item`, `unit`, `sex`, `value` | all | The measurement to be judged (`sex`: `M` / `F` / `공통`) |
| `options` | all | Permitted tier labels for this item |
| `expected` | all | Gold tier (see §4 on verification) |
| `case_type` | all | e.g. `경계값(B 시작=포함)`, `구간 대표`, `사다리` |
| `source` | all | Criteria provenance |
| `ladder_id` | ladder sets | Ladder membership, e.g. `감마GTP#M`, `BMI#upper` (`#M`/`#F` = sex-specific; `#upper`/`#lower` = the two arms of a U-shaped item) |
| `direction` | ladder sets | `high` = larger value is clinically worse; `low` = smaller value is worse |
| `near_boundary` | ladder v1.2+ | Value lies within ±3ε of a tier threshold (ε = that ladder's step) |

## 3. Primary metric and why it is label-independent

The **monotonicity violation rate** is the proportion of ordered value pairs within a ladder for
which the model assigns a *less severe* tier to a *clinically worse* value. Such a pair is a logical
contradiction under **any** threshold table, so the metric does not depend on accepting our gold labels.

**Important caveat.** The metric is label-independent but **not** independent of the `direction`
field: it assumes each ladder is genuinely monotone. Mis-specifying `direction` manufactures
spurious violations. This actually happened twice during development (§5) — both times a model's
clinically correct answer was scored as a violation. Any new ladder must have its monotone range
verified before use.

## 4. Gold-label verification

Every case is independently re-derived by a deterministic rule engine (`src/run_pilot.py
--provider mock`), which encodes the published criteria directly. Agreement is **100%** on all
three files. The rule engine also serves as a control for the primary metric: it produces
**0 monotonicity violations** on every ladder set.

| Set | Rule-engine tier agreement | Rule-engine monotonicity violations |
|---|---|---|
| `pubset_v1.0.jsonl` | 144/144 = 100% | n/a (no ladders) |
| `pubset_ladder_v1.3.jsonl` | 528/528 = 100% | **0 / 6,321** |
| `pubset_bmi_3cond.jsonl` | 54/54 = 100% | **0 / 514** |


**Result files (166 in `results/`).** Final analyses: ladder v1.3 zero-shot 10 runs and rule-grounded 10 runs per model (`*_ladder_v1.3_run1-10.jsonl`); tier v1.0 paired analysis 10 runs per condition per model (`*_v1.0_run1-10.jsonl`); the BMI 3-condition subset 10 runs per condition per model. Development-phase files: the runs on the development ladder versions (v1.1: Claude zero-shot ×3, GPT zero-shot ×1, grounded ×1 per model; v1.2: same configuration; rule-engine controls), the 4-run v1.0 pilot (`*_v1.0_pilot.jsonl`), and the independent 5-run Claude zero-shot replication (`*_v1.0_replication_run1-5.jsonl`). These support the audit trail in §5 and the fragility analyses in the article.

**Access windows.** Runs were collected in two windows: 21–26 August 2026 (pilot, replication, tier runs 1–5, ladder zero-shot, the initial rule-grounded ladder run, BMI subset) and 1 September 2026 (tier runs 6–10, rule-grounded ladder runs 2–10). Both prompting conditions were extended symmetrically across the two windows.

One label bug was found and fixed this way during v1.0 development (`PUB0082`, bone-density
T-score representative-value generation error).

## 5. Version history and confound audit trail

This trail is part of the release: two of the corrections below **reversed a published
between-model conclusion**, which is why we ship the history rather than only the final files.

### `pubset_v1.0.jsonl` (tier set) — unchanged since v1.0
144 cases / 20 items. Dual-verified as in §4.

### Ladder v1.1 → v1.2 — hemoglobin upper tail removed
v1.1 (370 cases / 3,066 pairs) declared `혈색소#M` as `direction: low` and extended it to **17.0**,
and `혈색소#F` to **16.0**. But the criteria table supplied to models states 정상A as
**13.0–16.5 (male) / 12.0–15.5 (female)** and gives **no rule above the upper bound**. Hemoglobin is
in fact U-shaped (both anemia and polycythemia are abnormal), so the monotone assumption was wrong
at the top of the ladder.

Consequence: a model answering `17.0 → 질환의심` — the reading most faithful to the very table it
was given — was scored as committing a violation. In the rule-grounded condition **100%** of both
models' violations traced to these two points; excluding them gave exactly 0.

Fix in v1.2: hemoglobin capped at 16.5 / 15.5.

### Ladder v1.1 → v1.2 — boundary-proximity base rate lowered
Ladders sample densely near thresholds by design, so in v1.1 **66.7%** of all pairs (81.3% of
adjacent pairs) already sat within ±3ε of a threshold. Enrichment was therefore unmeasurable
(observed 0.90–1.11×, i.e. no signal). v1.2 added filler points far from thresholds, lowering the
pair-level base rate to **48.2%** (v1.3: 48.4%) and making enrichment measurable.

### Ladder v1.2 → v1.3 — uric-acid lower point removed
The same structural flaw recurred at the *low* end. `요산(남)#M` was `direction: high` with a
minimum of **3.0**, while the criteria table says only "정상 ≤7.0 / 질환의심 >7.0 (hyperuricemia)"
with no lower bound. One model flagged 3.0 as abnormal (hypouricemia — clinically defensible) and
was scored as violating monotonicity. This single point accounted for **14%** of that model's
non-BMI violations.

Fix in v1.3: values 3.0 and 3.8 removed (528 cases / 6,321 pairs). Residual audit found no further
cases — ladder end-points are involved in only 0–3% of violations, and no other `low`-direction
ladder (HDL, eGFR, bone-density T-score) produced any violation.

### `pubset_bmi_3cond.jsonl` (new in v1.7)
54 BMI-only cases (9 tier + 45 ladder, 514 pairs) built to test whether BMI failures stem from
*criteria-source ambiguity*: BMI is the one item where models most often apply a different but
defensible standard (e.g. Asia-Pacific overweight cutoffs) instead of the notification's.

## 6. Known limitations

1. **BMI operationalization.** The notification places underweight (<18.5) in 질환의심. Models
   commonly read low BMI as non-suspicious, and may apply society cutoffs (23 / 25) rather than
   the notification's (25 / 30). BMI is therefore a confounded item in zero-shot evaluation and is
   reported as a **separate stratum** throughout, never pooled.
2. **Bone-density T-score.** The notification's negative-boundary wording is ambiguous; 정상B is
   operationalized here as −1.1 to −2.4.
3. **PSA / AFP** are excluded: age- and laboratory-specific reference ranges are not settled.
4. `direction` correctness is a precondition for the primary metric (§3).
5. Public-standard track only — no institutional rules, composite conditions, or follow-up codes.

## 7. Provenance and licensing

- Criteria text: 보건복지부 「건강검진 실시기준」 별표4, and open specialty-society standards
  (e.g. Korean Diabetes Association HbA1c thresholds).
- The notification is a 고시 of the Ministry of Health and Welfare. Under **Article 7(2) of the
  Korean Copyright Act**, notifications and public announcements issued by the State are not
  subject to copyright protection, so no 공공누리 (KOGL) grant applies; the notification is cited
  as the source rather than redistributed. This repository distributes only synthetic cases
  derived from those thresholds. See `../LICENSE-DATA.md`.
- Data files in `data/`: CC BY 4.0. Code in `src/`: MIT.
