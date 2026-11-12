# Brasaland sales forecast on the test years

Scored months: January 2024 through December 2025. The model was not retrained.

## Scores

- MSE: 837,440,385 USD squared (typical miss about 28,939 USD, average absolute miss 3.1% of that month's sales)
- PSI: 7.540
- Gini: 0.847
- K2 Score: 0.846
- Likely-range coverage: 83.3% of the 24 test months

## What Finance can read

On the two most recent years, the forecast is off by about 28,939 USD in a typical month, which is about 3.1% of that month's sales. K2 Score is 0.846: that is the share of the ups and downs captured versus just guessing the average test month. Gini is 0.847: that is how well the forecast ranks busier months above quieter ones, where 1 is a perfect ranking and 0 is no better than chance. PSI is 7.540. That is above 0.25, the usual line for a large shift. 23 of the 24 test months are above the training years' upper quartile, and 2 are above the highest training month. The dollar level moved up with the growth already described in the context file. The context file says a high PSI is a reason to review retraining, and that flag stands. It is a shift in level, not a claim that the forecast missed the December peaks. The shaded band on the chart covered 83.3% of the actual months. The band is the model's usual miss from the training years, moved onto each forecast. It was not widened or narrowed after seeing 2024 and 2025.

## Definitions used

The context file names these scores and does not give formulas. The formulas below are assumptions.

- MSE is the average squared dollar miss on the test months.
- The percentage next to it is the average absolute miss divided by actual sales.
- PSI compares the distribution of actual monthly sales in the training years with the test years. It is not a training accuracy score.
- Gini is the normalized rank agreement between the forecast and actual sales on the test months.
- K2 Score is the coefficient of determination on the test months. The project screenshot calls this slot R2 Score. The name kept here is K2 Score.
- The shaded band adds the 10th and 90th percentile of the training out-of-fold residual on the seasonal index to the forecast, then converts back to dollars with the previous 12 months of actual sales.

Figure: `data/pipelines/sales_forecast/sales_forecast_test_years.png`
