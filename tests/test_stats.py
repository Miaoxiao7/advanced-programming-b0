"""Tests for the pure statistics helpers."""

import math
import unittest

from b0_stats.stats import StatsError, coerce_values, percentile, summarise


class SummariseTest(unittest.TestCase):
    """Expected values below are computed by hand, not copied from the code."""

    def test_small_set_is_summarised(self):
        result = summarise([1, 2, 3, 4])
        self.assertEqual(result["count"], 4)
        self.assertAlmostEqual(result["mean"], 2.5, places=6)
        self.assertAlmostEqual(result["median"], 2.5, places=6)
        self.assertAlmostEqual(result["std_sample"], math.sqrt(5.0 / 3.0), places=6)
        self.assertEqual(result["min"], 1.0)
        self.assertEqual(result["max"], 4.0)
        self.assertAlmostEqual(result["q1"], 1.75, places=6)
        self.assertAlmostEqual(result["q3"], 3.25, places=6)
        self.assertAlmostEqual(result["iqr"], 1.5, places=6)
        self.assertEqual(result["outliers"], [])

    def test_far_value_is_reported_as_outlier(self):
        result = summarise([1, 2, 3, 4, 5, 100])
        self.assertEqual(result["count"], 6)
        self.assertEqual(result["outliers"], [100.0])
        self.assertEqual(result["outlier_count"], 1)

    def test_two_values_have_expected_mean_and_deviation(self):
        result = summarise([10, 20])
        self.assertAlmostEqual(result["mean"], 15.0, places=6)
        self.assertAlmostEqual(result["median"], 15.0, places=6)
        self.assertAlmostEqual(result["std_sample"], math.sqrt(50.0), places=6)

    def test_result_is_rounded_to_six_decimals(self):
        result = summarise([1, 2, 3])
        self.assertAlmostEqual(result["mean"], 2.0, places=6)
        self.assertEqual(round(result["std_sample"], 6), result["std_sample"])


class ValidationTest(unittest.TestCase):
    """Each rejected input must carry a stable error code."""

    def assert_code(self, expected, raw):
        with self.assertRaises(StatsError) as context:
            summarise(raw)
        self.assertEqual(context.exception.code, expected)

    def test_empty_input(self):
        self.assert_code("empty_input", [])

    def test_not_a_list(self):
        self.assert_code("invalid_type", {"values": 1.0})

    def test_single_sample(self):
        self.assert_code("too_few_samples", [7])

    def test_text_item(self):
        self.assert_code("not_a_number", [1, "2"])

    def test_boolean_item(self):
        self.assert_code("not_a_number", [True, 2])

    def test_not_finite_item(self):
        self.assert_code("not_a_number", [1, float("nan")])
        self.assert_code("not_a_number", [1, float("inf")])

    def test_too_many_samples(self):
        self.assert_code("too_many_samples", [1] * 10001)


class HelperTest(unittest.TestCase):
    def test_percentile_interpolates(self):
        self.assertAlmostEqual(percentile([1, 2, 3, 4], 0.25), 1.75, places=6)
        self.assertAlmostEqual(percentile([1, 2, 3, 4], 0.75), 3.25, places=6)

    def test_percentile_on_exact_index(self):
        self.assertAlmostEqual(percentile([1, 2, 3], 0.5), 2.0, places=6)

    def test_percentile_of_single_value(self):
        self.assertAlmostEqual(percentile([10], 0.75), 10.0, places=6)

    def test_coerce_returns_floats(self):
        self.assertEqual(coerce_values([1, 2]), [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
