"""T-10: harness/compare.py. 14 tests.

compare.py is pure arithmetic over committed inputs — no network, no model — so it is
tested two ways: unit tests against synthetic confusion data (fast, no repo state needed,
pin the arithmetic itself), and one integration test that runs the real script against the
real committed corpus/gold/baseline files and checks the acceptance properties T-10's board
row names directly: no STUB string survives, the negative-result section is above the fold,
and deleting + regenerating the file is byte-for-byte idempotent (nothing in it may be
derived from wall-clock time).
"""
from __future__ import annotations

import unittest

from harness.compare import (
    OUT,
    confusion,
    coverage,
    exact_match,
    main as compare_main,
    precision_recall_f1,
    self_agreement,
)


class TestConfusionAndPRF1(unittest.TestCase):
    def test_confusion_counts_tp_fp_fn_tn_correctly(self):
        gold = {
            "a": {"x": True},
            "b": {"x": True},
            "c": {"x": False},
            "d": {"x": False},
        }
        preds = {
            "a": {"x": True},  # tp
            "b": {"x": False},  # fn
            "c": {"x": True},  # fp
            "d": {"x": False},  # tn
        }
        c = confusion(gold, preds, ["a", "b", "c", "d"], "x")
        self.assertEqual(c, {"tp": 1, "fp": 1, "fn": 1, "tn": 1})

    def test_confusion_skips_claims_with_no_prediction_none(self):
        gold = {"a": {"x": True}, "b": {"x": True}}
        preds = {"a": {"x": True}, "b": None}
        c = confusion(gold, preds, ["a", "b"], "x")
        self.assertEqual(c, {"tp": 1, "fp": 0, "fn": 0, "tn": 0})

    def test_precision_recall_f1_perfect_scores_are_all_1(self):
        p, r, f1 = precision_recall_f1({"tp": 5, "fp": 0, "fn": 0, "tn": 3})
        self.assertEqual((p, r, f1), (1.0, 1.0, 1.0))

    def test_precision_recall_f1_zero_predicted_positive_is_none_not_a_crash(self):
        # A named regression test: an earlier draft divided tp/(tp+fp) with tp=fp=0 and
        # would have raised ZeroDivisionError the first time a field never fires.
        # accountable_party under the Gate's own construct fires on 0/60 real claims —
        # this is not a hypothetical edge case, it is this corpus's actual data.
        p, r, f1 = precision_recall_f1({"tp": 0, "fp": 0, "fn": 29, "tn": 31})
        self.assertIsNone(p)
        self.assertEqual(r, 0.0)
        self.assertIsNone(f1)


class TestExactMatch(unittest.TestCase):
    def test_exact_match_requires_every_field_to_agree(self):
        gold = {
            "a": {"x": True, "y": False},
            "b": {"x": True, "y": True},
        }
        preds = {
            "a": {"x": True, "y": False},  # full match
            "b": {"x": True, "y": False},  # y disagrees
        }
        matches, total = exact_match(gold, preds, ["a", "b"], ["x", "y"])
        self.assertEqual((matches, total), (1, 2))

    def test_exact_match_excludes_unparseable_claims_from_the_denominator(self):
        gold = {"a": {"x": True}, "b": {"x": True}}
        preds = {"a": {"x": True}, "b": None}
        matches, total = exact_match(gold, preds, ["a", "b"], ["x"])
        self.assertEqual((matches, total), (1, 1))


class TestCoverage(unittest.TestCase):
    def test_coverage_counts_only_non_none_entries_as_parseable(self):
        preds = {"a": {"x": True}, "b": None, "c": {"x": False}}
        self.assertEqual(coverage(preds), (2, 3))


class TestSelfAgreement(unittest.TestCase):
    def test_three_identical_runs_agree_on_every_claim(self):
        run = {"a": {"x": True, "_checkable": True}, "b": {"x": False, "_checkable": False}}
        agg = self_agreement([run, dict(run), dict(run)], ["a", "b"], ["x"])
        self.assertEqual(agg["disagree_checkable"], 0)
        self.assertEqual(agg["disagree_vector"], 0)
        self.assertEqual(agg["agree_checkable"], 2)

    def test_a_flipped_checkable_bit_is_counted_as_one_contradiction(self):
        run1 = {"a": {"x": True, "_checkable": True}}
        run2 = {"a": {"x": True, "_checkable": False}}  # same field verdict, different self-report
        run3 = {"a": {"x": True, "_checkable": True}}
        agg = self_agreement([run1, run2, run3], ["a"], ["x"])
        self.assertEqual(agg["disagree_checkable"], 1)
        # the field-level vector never moved, only the model's own summary bit did —
        # this is exactly the gap the docstring on self_agreement() calls out: the two
        # are separate outputs from the same call and can genuinely disagree.
        self.assertEqual(agg["disagree_vector"], 0)

    def test_unparseable_claims_are_skipped_not_counted_as_disagreement(self):
        run1 = {"a": {"x": True, "_checkable": True}}
        run2 = {"a": None}
        run3 = {"a": {"x": True, "_checkable": True}}
        agg = self_agreement([run1, run2, run3], ["a"], ["x"])
        self.assertEqual(agg["skipped_unparseable"], 1)
        self.assertEqual(agg["agree_checkable"] + agg["disagree_checkable"], 0)


class TestCompareIntegration(unittest.TestCase):
    """Runs the real script against the real, committed corpus/gold/baseline files —
    the acceptance properties named directly on T-10's board row."""

    @classmethod
    def setUpClass(cls):
        compare_main()
        cls.text = OUT.read_text()

    def test_no_stub_string_survives(self):
        self.assertNotIn("STUB", self.text)

    def test_negative_result_is_above_the_fold(self):
        head = "\n".join(self.text.splitlines()[:20])
        self.assertRegex(head.lower(), r"beats|wins|misses")

    def test_regenerating_the_file_is_byte_for_byte_idempotent(self):
        first = self.text
        compare_main()
        second = OUT.read_text()
        self.assertEqual(first, second)

    def test_gate_three_run_hash_does_not_report_diverged(self):
        # Arm A's own "3/3 identical by construction" claim, checked mechanically: if the
        # committed gate.run{1,2,3}.json ever stopped hashing identically, this string
        # would appear in the generated file and this test would catch it before a human
        # reading COMPARISON.md would.
        self.assertNotIn("DIVERGED", self.text)


if __name__ == "__main__":
    unittest.main()
