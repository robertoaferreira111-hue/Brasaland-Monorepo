# Brasaland sales forecast — evaluation report

Target: `seasonal_index` (unitless; `revenue_usd` / trailing 12-month mean).  
Artifacts: [`learning_curve.png`](learning_curve.png), [`evaluation_metrics.json`](evaluation_metrics.json).  
Scope: 8-year training portion only. The held-out 2 test years were not used.

---

## 1. Fit diagnosis: **overfitting**

**Verdict: overfitting** (variance). The learning curve shows a wide, persistent gap: training error stays low while validation error stays higher, and the two curves do not converge to a close pair.

Evidence from [`learning_curve.png`](learning_curve.png) and `evaluation_metrics.json`:

| Train size | Train MAE | Val MAE | Gap (val − train) |
| --- | ---: | ---: | ---: |
| 12 | 0.005596095331711358 | 0.042903391610196254 | 0.037307296278484896 |
| 24 | 0.006115432162859942 | 0.03733566661323791 | 0.03122023445037797 |
| 36 | 0.008553340648147667 | 0.033482270229175624 | 0.024928929581027957 |
| 48 | 0.00989811919494203 | 0.035815229263540665 | 0.025917110068598635 |
| 60 | 0.012046631326034484 | 0.04227041188606654 | 0.030223780560032056 |

Pattern interpretation (README rubric: wide gap, train low / val high → overfitting):

- Training MAE remains low across sizes (0.0056 at size 12 → 0.0120 at size 60).
- Validation MAE stays in a higher band (about 0.033–0.043) and never closes on training.
- At the largest size (60 months), the gap is still 0.030223780560032056 — positive and large relative to training error.
- This is not underfitting: underfitting would show both curves converging at **high** error. Training error here is low.
- This is not well fitted: well fitted requires both curves converging at **low, close** error. The gap persists.

Temporal CV agrees on the same train-vs-validation split of difficulty:

- Train MAE 0.008441923732739097 ± 0.0023932462513981245
- Val MAE 0.03993405834557312 ± 0.006344058235030763
- Train RMSE 0.010696365542905897 ± 0.002939289620636584
- Val RMSE 0.04616563629511199 ± 0.009178511514125328

Root cause class: **variance** (memorization of the small chronological train windows), not bias from an inflexible model.

---

## 2. Stability across temporal folds

Primary metric **MAE** on validation folds (5× `TimeSeriesSplit`, training years only):

**0.03993405834557312 ± 0.006344058235030763**

Per-fold validation MAE:

| Fold | n_train | Val window | Val MAE | Val RMSE |
| --- | ---: | --- | ---: | ---: |
| 1 | 12 | 2019-01 → 2019-12 | 0.050293918227642946 | 0.06260086991113827 |
| 2 | 24 | 2020-01 → 2020-12 | 0.03950247061272144 | 0.04513424437879728 |
| 3 | 36 | 2021-01 → 2021-12 | 0.031247010663254 | 0.03431953790786067 |
| 4 | 48 | 2022-01 → 2022-12 | 0.03635648033818067 | 0.043085634546012476 |
| 5 | 60 | 2023-01 → 2023-12 | 0.04227041188606654 | 0.04568789473175128 |

Commentary:

- Std of 0.006344058235030763 is about 15.9% of the mean (0.006344058235030763 / 0.03993405834557312), so fold-to-fold movement is noticeable on this small series.
- **Outlier fold: fold 1** — highest val MAE (0.050293918227642946) and RMSE (0.06260086991113827), with the smallest train window (12 months). That matches the learning-curve note that the smallest training sizes are tiny (~12 rows) and produce the largest validation spread (val MAE std 0.011817745776688008 at size 12).
- Best fold is fold 3 (val MAE 0.031247010663254). Performance is usable in mid folds but not uniform; early tiny-train folds pull the mean up and widen the std.

---

## 3. Metric choice: MAE (primary) vs RMSE

Both metrics were computed on train and validation (`evaluation_metrics.json`).

| | MAE | RMSE |
| --- | ---: | ---: |
| Train (CV mean ± std) | 0.008441923732739097 ± 0.0023932462513981245 | 0.010696365542905897 ± 0.002939289620636584 |
| Validation (CV mean ± std) | **0.03993405834557312 ± 0.006344058235030763** | 0.04616563629511199 ± 0.009178511514125328 |

**Primary metric: MAE.**

Justification from the company sources (not from the assignment README’s stockout/RMSE example):

- `CONTEXT-company.md` discusses forecasting “within a reasonable margin,” Gini alongside absolute error, and MSE/percentage error. It does **not** state that overestimation or underestimation is costlier.
- Root `company-BRIEFING.md` discusses waste (“direct hit to margin”) and stockouts (service risk) as **operations KPIs for a weekly cost/waste report**. It does **not** rank sales-forecast over- vs under-estimation, and does not map those ops KPIs onto forecast error direction.
- Phase 2 recorded `ranks_over_vs_under_estimation: false`. When the briefings do not establish asymmetric cost of large misses, MAE is the primary metric because it treats errors of either sign equally. RMSE is reported for completeness; it is not primary on company-stated cost grounds.

---

## 4. Corrective action (proposed, not applied)

Diagnosis is overfitting / variance. Corrective action therefore **reduces complexity / adds regularization**, not “increase `max_depth`” and not a bare “tune hyperparameters.”

Saved hyperparameters in `data/pipelines/sales_forecast/sales_forecast_model.joblib`: `n_estimators=100`, `max_depth=3`, `learning_rate=0.05`, `random_state=42`.

**Proposed change (next experiment only):**

1. Reduce `max_depth` from **3 → 2** (shallower trees; less capacity to memorize tiny chronological windows).
2. Add L2 regularization: set `reg_lambda` from the current default to **5.0** (penalize large leaf weights that drive the train/val MAE gap of ~0.030 at size 60).
3. Keep `n_estimators=100`, `learning_rate=0.05`, and seed `42` fixed so the comparison isolates complexity/regularization.
4. Re-run the same leakage-safe temporal CV and learning curve; success criterion: validation MAE mean ≤ current 0.03993405834557312 **and** the size-60 train/val MAE gap below the current 0.030223780560032056, without collapsing both curves at high error (which would signal under-regularization flipped into underfitting).

“Add more data” is not the first lever here: only ~72 feature-ready training months exist, and the rubric’s overfitting path prioritizes reducing complexity before seeking more data. More history would still help CV variance later, but that is secondary to the gap already visible at size 60.

---

## 5. Limitations

- Neither `CONTEXT-company.md` nor root `company-BRIEFING.md` ranks over- vs under-estimation cost for the sales forecast; primary=MAE rests on that absence of ranking, not on an explicit company preference for MAE.
- Only about 72 feature-ready rows exist in the 8-year train window (96 raw months minus 24 months of causal warmup). Temporal CV therefore uses small folds (validation n=12; early train n=12). That inflates fold-to-fold variance and makes the learning-curve std at small sizes (e.g. 0.011817745776688008 at size 12) a sample-size effect as well as a model effect.
- Larger learning-curve sizes use fewer folds (5 → 1), so the right side of [`learning_curve.png`](learning_curve.png) is less averaged than the left.
- Metrics are on `seasonal_index`, not USD. Dollar error would scale with the trailing mean and is out of scope for this CV report.

---

## Checklist map (What We Will Evaluate)

| Item | Status | Evidence |
| --- | --- | --- |
| Learning curve generated and interpreted | Done | [`learning_curve.png`](learning_curve.png); §1 pattern table |
| Temporal CV, no leakage, mean ± std | Done | `pipelines/evaluate_sales_model.py`; §2; `tests/pipelines/test_temporal_cv.py` |
| ≥2 metrics; primary justified from briefing evidence | Done | §3; `evaluation_metrics.json` → `primary_metric_recommendation` |
| Diagnosis backed by curve + train/val gap | Done | §1 (overfitting) |
| Corrective action specific and tied to variance | Done | §4 (`max_depth` 3→2, `reg_lambda=5.0`) |
| Chronological-order unit test | Done | `tests/pipelines/test_temporal_cv.py` |
