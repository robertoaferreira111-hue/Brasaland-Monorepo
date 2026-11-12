"""Test-set metrics for the Brasaland sales forecast.

``CONTEXT-company.md`` names MSE, PSI, Gini, and K2 Score and says what a
high or low value means. It does not give formulas. ``skills/data-analysis``
does not define them either. Each docstring states the formula used here.
Those formulas are assumptions, not a course definition.

A small mean squared error, by itself, can look comforting while the
forecast still ranks weak months as strong ones (Gini), while the test
years sit in a different sales range than the training years (PSI), or
while the forecast is no better than guessing the average test month (K2).
"""

from __future__ import annotations

import numpy as np

# Industry bins often used with the population stability index. Not in the
# Brasaland context file.
PSI_MODERATE = 0.10
PSI_LARGE = 0.25


def mean_squared_error_usd(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Average squared miss, in USD squared.

    This is the size of the dollar misses on the months being scored. A low
    value can still be a poor forecast if every month is missed by a similar
    amount in the same direction, or if the forecast cannot tell a slow
    January from a busy December. Pair it with the percentage translation
    ``mean_absolute_percentage_error`` and with Gini and K2.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return float(np.mean((actual - predicted) ** 2))


def mean_absolute_percentage_error(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Average absolute miss divided by actual sales.

    ``CONTEXT-company.md`` asks for MSE in USD squared and also for an
    average percentage error, which is how Finance reads a dollar miss.
    This is that translation. It is not one of the four named scores.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs(actual - predicted) / actual))


def population_stability_index(reference: np.ndarray, current: np.ndarray, bins: int = 4) -> float:
    """Shift in the shape of sales between two periods.

    Assumption. The context says a high PSI between the training and test
    sets means sales behavior changed and the model may need retraining. It
    does not give a formula. This uses the usual population stability index:
    cut the reference period into quantile bins, see what share of each
    period falls in those bins, then sum
    ``(current share - reference share) * log(current share / reference share)``.
    Empty shares are replaced with a tiny number so the log is defined.

    The reference series is the training years and the current series is the
    test years, because that is the comparison the context names. The number
    is not a training-set accuracy score. Values under 0.10 are commonly read
    as a small shift, 0.10 to 0.25 as moderate, and above 0.25 as large.
    Those cut points are also an assumption.
    """
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    edges = np.quantile(reference, np.linspace(0.0, 1.0, bins + 1))
    edges = np.unique(edges)
    if len(edges) < 3:
        raise ValueError("Reference sales do not form enough bins for PSI")
    edges[0] = -np.inf
    edges[-1] = np.inf
    reference_counts = np.histogram(reference, bins=edges)[0].astype(float)
    current_counts = np.histogram(current, bins=edges)[0].astype(float)
    reference_share = reference_counts / reference_counts.sum()
    current_share = current_counts / current_counts.sum()
    epsilon = 1e-6
    reference_share = np.maximum(reference_share, epsilon)
    current_share = np.maximum(current_share, epsilon)
    reference_share = reference_share / reference_share.sum()
    current_share = current_share / current_share.sum()
    return float(np.sum((current_share - reference_share) * np.log(current_share / reference_share)))


def _gini_sort(actual: np.ndarray, predicted: np.ndarray) -> float:
    paired = np.column_stack([np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)])
    paired = paired[np.lexsort((paired[:, 0], paired[:, 1]))]
    total = paired[:, 0].sum()
    if total == 0.0:
        raise ValueError("Gini is undefined when actual sales sum to zero")
    cumulative = paired[:, 0].cumsum().sum() / total
    count = len(paired)
    return (cumulative - (count + 1) / 2.0) / count


def normalized_gini(actual: np.ndarray, predicted: np.ndarray) -> float:
    """How well the forecast ranks busy months above quiet ones.

    Assumption. The context says a low Gini means the model does not
    distinguish good and bad months. It does not give a formula. This is the
    normalized Gini used for ranked outcomes: sort the months by the
    forecast, measure how the actual sales accumulate, and divide by the
    same measure when the months are sorted by actual sales. About 1 means
    the forecast ranks months the way actual sales do. About 0 means the
    ranking is no better than chance. Below 0 means the ranking is backwards.

    A low mean squared error can coexist with a low Gini when the forecast
    is close in dollars but swaps which months are the strong ones.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    perfect = _gini_sort(actual, actual)
    if perfect == 0.0:
        raise ValueError("Gini is undefined when every actual month is equal")
    return float(_gini_sort(actual, predicted) / perfect)


def k2_score(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Share of month-to-month variation the forecast captures.

    Assumption. The context names K2 Score and does not define it. The
    project screenshot names R2 Score in that same slot, and this project
    keeps the name K2 Score. The number computed here is the coefficient of
    determination on the scored months:
    ``1 - (sum of squared misses) / (sum of squared gaps from the average)``.
    About 1 means the forecast tracks the ups and downs. About 0 means it is
    no better than predicting the average month. Below 0 means it is worse
    than that average.

    Mean squared error alone does not say this. A forecast can have a modest
    squared error and still lose to the simple average of the period.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    residual = np.sum((actual - predicted) ** 2)
    centered = np.sum((actual - actual.mean()) ** 2)
    if centered == 0.0:
        raise ValueError("K2 Score is undefined when every actual month is equal")
    return float(1.0 - residual / centered)
