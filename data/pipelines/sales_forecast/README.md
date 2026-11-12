# Brasaland sales forecast

Monthly chain sales forecast for Brasaland. Training uses the first 8 years of `data/raw/brasaland_sales.csv`. Scoring uses the last 2 years. The raw CSV is not modified.

## Algorithm and why

The fitted model is **XGBoost** (`n_estimators=100`, `max_depth=3`, `learning_rate=0.05`, `random_state=42`).

Both XGBoost and Random Forest were compared with the same four-point grid and the same three time-ordered folds inside the training years only. The rule was: take XGBoost if its training-fold mean squared error on the seasonal index is more than 5 percent lower; otherwise take the forest, because Finance can review a tree and the forest already has a variability range from its trees.

On this file, Random Forest scored 0.00267246 and XGBoost scored 0.00165595. XGBoost was about 38 percent lower, so the margin rule selected it. The justification, including dataset size, Finance review, tuning time, the variability range, and the tree-extrapolation limit, is in the docstring of `scripts/train_sales_forecast.py`.

The target is the seasonal index (this month's revenue divided by the mean of the previous 12 months). A dollar forecast is that index times the trailing mean. That keeps the rising level described in `CONTEXT-company.md` without asking a tree to invent a revenue leaf above the training years.

## What the four metrics measure

Definitions are in `data/pipelines/sales_forecast_metrics.py`. `CONTEXT-company.md` names the scores and does not give formulas, so those formulas are assumptions.

| Metric | What it measures |
| --- | --- |
| **MSE** | Average squared miss in USD squared on the test months. A percentage translation of the absolute miss is reported next to it. |
| **PSI** | How much the shape of monthly sales changed between the training years and the test years. A high value flags a structural shift and a possible need to retrain. |
| **Gini** | How well the forecast ranks busier months above quieter ones. About 1 is a perfect ranking; about 0 is no better than chance. |
| **K2 Score** | Share of month-to-month variation captured on the test months (coefficient of determination). About 1 tracks the ups and downs; about 0 is no better than the average test month. |

A low MSE alone is not enough. The forecast can be close in dollars while ranking weak months as strong ones (Gini), while the test years sit in a different sales level than the training years (PSI), or while it is no better than guessing the average month (K2 Score).

Test-set results live in `sales_forecast_test_metrics.json` and `sales_forecast_test_metrics.md`.

## How to run with `uv`

From the repository root:

```bash
uv sync --project data/pipelines/sales_forecast
uv run --project data/pipelines/sales_forecast pytest tests/pipelines/test_sales_forecast_split.py
uv run --project data/pipelines/sales_forecast python scripts/train_sales_forecast.py
uv run --project data/pipelines/sales_forecast python scripts/report_sales_forecast.py
```

On some macOS setups, XGBoost needs the OpenMP runtime (`libomp.dylib`) on the dynamic loader path.

## Where the figure lives

`data/pipelines/sales_forecast/sales_forecast_test_years.png`

It shows actual sales for 2024 and 2025, the forecast, and a shaded likely range built from the training out-of-fold residual quantiles on the seasonal index.
