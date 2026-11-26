"""Summary statistics helpers.

The module contains pure functions only, so every number can be recomputed by
hand without starting the HTTP service.
"""

import math
from typing import Dict, List, Sequence

MAX_SAMPLES = 10000
MIN_SAMPLES = 2
DECIMALS = 6


class StatsError(ValueError):
    """Raised when the input cannot produce a meaningful summary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def coerce_values(raw: object) -> List[float]:
    """Validate a decoded JSON value and return it as a list of floats."""
    if not isinstance(raw, list):
        raise StatsError("invalid_type", "values must be a list of numbers")
    if not raw:
        raise StatsError("empty_input", "values must not be empty")
    if len(raw) > MAX_SAMPLES:
        raise StatsError(
            "too_many_samples",
            "values must contain at most {} numbers".format(MAX_SAMPLES),
        )
    values = []
    for index, item in enumerate(raw):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise StatsError("not_a_number", "values[{}] is not a number".format(index))
        number = float(item)
        if not math.isfinite(number):
            raise StatsError("not_a_number", "values[{}] is not finite".format(index))
        values.append(number)
    if len(values) < MIN_SAMPLES:
        raise StatsError(
            "too_few_samples",
            "at least {} numbers are required".format(MIN_SAMPLES),
        )
    return values


def percentile(sorted_values: Sequence[float], fraction: float) -> float:
    """Return a linearly interpolated percentile of an ascending sequence."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * fraction
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))
    if lower_index == upper_index:
        return sorted_values[lower_index]
    weight = position - lower_index
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    return lower_value + (upper_value - lower_value) * weight


def zero_crossing_rate(values: Sequence[float]) -> float:
    """Return the share of adjacent pairs that change sign, in input order.

    Zero is counted as non-negative, so ``[0, 1]`` has no crossing while
    ``[-1, 1]`` has one. The rate is the crossing count divided by ``n - 1``,
    which needs at least two samples; callers validate that beforehand.
    """
    non_negative = [value >= 0 for value in values]
    crossings = 0
    for previous, current in zip(non_negative, non_negative[1:]):
        if previous != current:
            crossings += 1
    return crossings / (len(values) - 1)


def summarise(raw: object) -> Dict[str, object]:
    """Return count, central tendency, dispersion, extremes and IQR fences."""
    values = coerce_values(raw)
    ordered = sorted(values)
    count = len(ordered)
    mean = sum(ordered) / count
    median = percentile(ordered, 0.5)
    variance = sum((value - mean) ** 2 for value in ordered) / (count - 1)
    q1 = percentile(ordered, 0.25)
    q3 = percentile(ordered, 0.75)
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outliers = [
        value for value in ordered if value < lower_fence or value > upper_fence
    ]
    mean_square = sum(value * value for value in values) / count
    return {
        "count": count,
        "mean": round(mean, DECIMALS),
        "median": round(median, DECIMALS),
        "std_sample": round(math.sqrt(variance), DECIMALS),
        "variance_sample": round(variance, DECIMALS),
        "variance_population": round(variance * (count - 1) / count, DECIMALS),
        "rms": round(math.sqrt(mean_square), DECIMALS),
        "min": ordered[0],
        "max": ordered[-1],
        "peak": max(abs(value) for value in values),
        "peak_to_peak": round(ordered[-1] - ordered[0], DECIMALS),
        "q1": round(q1, DECIMALS),
        "q3": round(q3, DECIMALS),
        "iqr": round(iqr, DECIMALS),
        "zero_crossing_rate": round(zero_crossing_rate(values), DECIMALS),
        "outliers": outliers,
        "outlier_count": len(outliers),
    }
