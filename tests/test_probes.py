"""T-05: 6 tests per probe x 5 probes = 30. Every test asserts against the real
rules/climate.v1.json pack loaded through core.engine.load_pack — never a hand-rolled params
dict — so a future edit to the pack (a new regex, a widened year range) is what these tests
actually exercise, not a copy of it.

Each probe gets: present, absent, boundary, negation, unicode/typography, and either a
documented-miss case or (where the probe has no interesting miss of its own) a second
typography/boundary case that still earns its slot honestly.

Negation tests are not bugs: probe_quantity/target_year/etc. answer "is an auditable element
present in the text", not "is the claim true". A probe that flipped to False under negation
would be doing sentiment analysis, which is explicitly out of scope (see core/probes.py's
module docstring). The negation tests pin that boundary so nobody "fixes" it into a truth
probe later without noticing they changed what the Gate promises.

Known misses are pinned per the task brief, not hidden: at least three tests below assert a
verdict of False on text a human would consider checkable, and say why in the docstring. If one
of these ever starts asserting True, that's a real behaviour change and should be reviewed as
one, not slip through silently.
"""
from __future__ import annotations

import unittest

from core.engine import load_pack
from core.probes import (
    probe_accountable_party,
    probe_baseline_year,
    probe_named_standard,
    probe_quantity,
    probe_target_year,
)

NBSP = " "  # non-breaking space, as scraped text sometimes carries
ENDASH = "–"


class ProbeTestCase(unittest.TestCase):
    """Loads the real pack once; subclasses look up their own clause's params/lexicons."""

    @classmethod
    def setUpClass(cls):
        cls.pack = load_pack("rules/climate.v1.json")
        cls.specs = {p["clause_id"]: p for p in cls.pack["probes"]}
        cls.lexicons = cls.pack["lexicons"]

    def run_probe(self, fn, clause_id, text):
        spec = self.specs[clause_id]
        return fn(text, spec["params"], self.lexicons)


class TestQuantityProbe(ProbeTestCase):
    CLAUSE = "C1-QTY"

    def test_quantity_present_with_a_percentage(self):
        r = self.run_probe(probe_quantity, self.CLAUSE, "We will cut emissions by 50% by 2030.")
        self.assertTrue(r.present)
        self.assertEqual(r.matched, "50%")

    def test_quantity_absent_when_no_number_is_given(self):
        r = self.run_probe(probe_quantity, self.CLAUSE, "We will cut emissions by a lot.")
        self.assertFalse(r.present)

    def test_quantity_boundary_decimal_amount_and_zero_percent(self):
        with self.subTest("decimal unit"):
            r = self.run_probe(probe_quantity, self.CLAUSE, "We will cut 12.5 tonnes of CO2 by 2030.")
            self.assertTrue(r.present)
        with self.subTest("zero percent still a quantity"):
            r = self.run_probe(probe_quantity, self.CLAUSE, "We aim for a 0% increase.")
            self.assertTrue(r.present)

    def test_quantity_negation_still_counts_as_present(self):
        # The probe checks whether a number is stated, not whether the claim is honest.
        r = self.run_probe(probe_quantity, self.CLAUSE, "We will not reduce emissions by 50%.")
        self.assertTrue(r.present)

    def test_quantity_matches_across_non_breaking_space_before_unit(self):
        text = f"We will cut emissions by 50{NBSP}% by 2030."
        r = self.run_probe(probe_quantity, self.CLAUSE, text)
        self.assertTrue(r.present)

    def test_quantity_misses_word_numbers_like_halve(self):
        """Documented miss: 'halve'/'net-zero'/'double' etc. are listed in the pack's own
        params["known_miss_words"] precisely because the quantity probe does not resolve
        them to a number. This is the Gate's honest weakness, not a bug to fix here."""
        spec = self.specs[self.CLAUSE]
        self.assertIn("halve", spec["params"]["known_miss_words"])
        r = self.run_probe(probe_quantity, self.CLAUSE, "Our target is to halve emissions by 2030.")
        self.assertFalse(r.present)


class TestTargetYearProbe(ProbeTestCase):
    CLAUSE = "C2-TGTYR"

    def test_target_year_present_with_context_word(self):
        r = self.run_probe(probe_target_year, self.CLAUSE, "We aim to reach net zero by 2030.")
        self.assertTrue(r.present)
        self.assertEqual(r.matched, "2030")

    def test_target_year_absent_without_any_year(self):
        r = self.run_probe(probe_target_year, self.CLAUSE, "We aim to reach net zero soon.")
        self.assertFalse(r.present)

    def test_target_year_boundary_min_year_inclusive_year_before_it_excluded(self):
        with self.subTest("2020 is the configured min_year, included"):
            r = self.run_probe(probe_target_year, self.CLAUSE, "Our target for full transition is 2020.")
            self.assertTrue(r.present)
        with self.subTest("2019 is one below min_year, excluded"):
            r = self.run_probe(probe_target_year, self.CLAUSE, "Our target for full transition is 2019.")
            self.assertFalse(r.present)

    def test_target_year_negation_still_counts_as_present(self):
        r = self.run_probe(probe_target_year, self.CLAUSE, "We will not commit to a target by 2030.")
        self.assertTrue(r.present)

    def test_target_year_matches_a_year_inside_an_en_dash_range(self):
        text = f"Our target covers 2020{ENDASH}2030 emissions reductions."
        r = self.run_probe(probe_target_year, self.CLAUSE, text)
        self.assertTrue(r.present)

    def test_target_year_misses_a_year_spelled_out_in_words(self):
        """Documented miss: the year regex matches digits only. "the year twenty thirty"
        names a real target year to a human reader; the probe cannot see it."""
        r = self.run_probe(
            probe_target_year, self.CLAUSE, "We aim to achieve our goal by the year twenty thirty."
        )
        self.assertFalse(r.present)


class TestBaselineYearProbe(ProbeTestCase):
    CLAUSE = "C3-BASEYR"

    def test_baseline_year_present_with_context_phrase(self):
        r = self.run_probe(
            probe_baseline_year, self.CLAUSE, "We will cut emissions 50% compared to a 2019 baseline."
        )
        self.assertTrue(r.present)
        self.assertEqual(r.matched, "2019")

    def test_baseline_year_absent_when_no_baseline_is_named(self):
        r = self.run_probe(probe_baseline_year, self.CLAUSE, "We will cut emissions by 50% by 2030.")
        self.assertFalse(r.present)

    def test_baseline_year_boundary_min_year_inclusive_year_after_max_excluded(self):
        with self.subTest("1990 is the configured min_year, included"):
            r = self.run_probe(
                probe_baseline_year, self.CLAUSE, "Emissions are measured against a 1990 baseline."
            )
            self.assertTrue(r.present)
        with self.subTest("2025 is one above max_year (2024), excluded"):
            r = self.run_probe(
                probe_baseline_year, self.CLAUSE, "Emissions are measured against a 2025 baseline."
            )
            self.assertFalse(r.present)

    def test_baseline_year_negation_still_counts_as_present(self):
        r = self.run_probe(
            probe_baseline_year,
            self.CLAUSE,
            "This is not compared to a 2019 baseline in any way.",
        )
        self.assertTrue(r.present)

    def test_baseline_year_matches_across_non_breaking_space_before_year(self):
        text = f"Emissions are measured against a{NBSP}2019 baseline."
        r = self.run_probe(probe_baseline_year, self.CLAUSE, text)
        self.assertTrue(r.present)

    def test_baseline_year_misses_a_decade_phrase_without_a_specific_year(self):
        """Documented miss: "2010s levels" gestures at a baseline decade but names no single
        base year — GHG Protocol ch.5 requires a specific base year, so this is a correct
        miss, but a human skimming the sentence might not realise nothing was verified."""
        r = self.run_probe(
            probe_baseline_year, self.CLAUSE, "Emissions are measured against 2010s levels."
        )
        self.assertFalse(r.present)


class TestNamedStandardProbe(ProbeTestCase):
    CLAUSE = "C4-STD"

    def test_named_standard_present_ghg_protocol(self):
        r = self.run_probe(probe_named_standard, self.CLAUSE, "We report in line with the GHG Protocol.")
        self.assertTrue(r.present)
        self.assertEqual(r.matched, "GHG Protocol")

    def test_named_standard_absent_generic_best_practice(self):
        r = self.run_probe(probe_named_standard, self.CLAUSE, "We report in line with best practice.")
        self.assertFalse(r.present)

    def test_named_standard_boundary_term_at_the_very_end_of_the_string(self):
        r = self.run_probe(probe_named_standard, self.CLAUSE, "We disclose in line with TCFD")
        self.assertTrue(r.present)

    def test_named_standard_negation_still_counts_as_present(self):
        r = self.run_probe(
            probe_named_standard, self.CLAUSE, "We are not yet aligned with TCFD but plan to be."
        )
        self.assertTrue(r.present)

    def test_named_standard_matches_across_non_breaking_space_inside_the_term(self):
        # Regression: a multi-word lexicon term used to require an exact ASCII space between
        # its words (re.escape() on " " matches only " "). Text scraped from real reports
        # sometimes carries a non-breaking space in a title like this one instead. Fixed in
        # core/probes.py's _term_pattern(); see test_accountable_party_matches_across_nbsp_
        # word_gap below for the same fix on the other lexicon probe.
        text = f"We report per GHG{NBSP}Protocol standards."
        r = self.run_probe(probe_named_standard, self.CLAUSE, text)
        self.assertTrue(r.present)

    def test_named_standard_misses_paraphrased_standard_language(self):
        """Documented miss: naming no standard, scope or framework by name — only vague
        "best-practice" language — is exactly what TCFD's own recommendation exists to rule
        out, and the probe correctly can't verify prose it has no lexicon entry for. This is
        the "paraphrased standards" miss named in the task brief."""
        r = self.run_probe(
            probe_named_standard,
            self.CLAUSE,
            "We follow internationally recognized best-practice reporting frameworks.",
        )
        self.assertFalse(r.present)


class TestAccountablePartyProbe(ProbeTestCase):
    CLAUSE = "C5-ACTOR"

    def test_accountable_party_present_ceo(self):
        r = self.run_probe(probe_accountable_party, self.CLAUSE, "Our CEO is accountable for this target.")
        self.assertTrue(r.present)
        self.assertEqual(r.matched, "CEO")

    def test_accountable_party_absent_generic_the_company(self):
        r = self.run_probe(
            probe_accountable_party, self.CLAUSE, "The company is accountable for this target."
        )
        self.assertFalse(r.present)

    def test_accountable_party_boundary_term_at_the_very_start_of_the_string(self):
        r = self.run_probe(probe_accountable_party, self.CLAUSE, "CEO oversight applies here.")
        self.assertTrue(r.present)

    def test_accountable_party_negation_still_counts_as_present(self):
        r = self.run_probe(
            probe_accountable_party, self.CLAUSE, "This is not overseen by the CFO alone."
        )
        self.assertTrue(r.present)

    def test_accountable_party_matches_across_nbsp_word_gap(self):
        """Named regression test. Found while writing this suite: a real title like "Chief
        Sustainability Officer" scraped with a non-breaking space between two of its words
        failed to match the lexicon entry, because _lexicon_search used to build its regex
        from a plain-space-escaped literal. Fixed in core/probes.py (_term_pattern now joins
        words with \\s+ instead of a literal escaped space). Before the fix this test failed."""
        text = f"Our Chief{NBSP}Sustainability{NBSP}Officer will oversee this."
        r = self.run_probe(probe_accountable_party, self.CLAUSE, text)
        self.assertTrue(r.present)
        self.assertIn("Sustainability", r.matched)

    def test_accountable_party_misses_a_vague_role_without_a_named_title(self):
        """Documented miss: "a senior executive" names no title from the actors lexicon
        (only specific roles like "executive committee" or "chief sustainability officer"
        are listed), so ISSB IFRS S2 §6's governance-accountability bar is correctly not met
        — but this also means any title the lexicon hasn't anticipated will miss."""
        r = self.run_probe(
            probe_accountable_party,
            self.CLAUSE,
            "A senior executive will be accountable for progress.",
        )
        self.assertFalse(r.present)


if __name__ == "__main__":
    unittest.main()
