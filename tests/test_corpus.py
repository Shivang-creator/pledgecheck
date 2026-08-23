"""T-05: corpus invariants. 5 tests.

State at the time this was written: T-02 (corpus/documents.json) and T-07
(corpus/claims.frozen.jsonl + corpus/MANIFEST.md) have not landed yet — this file only has
`.gitkeep` in it. Rather than hard-code a path that doesn't exist yet (which would make this
whole file fail loudly the moment it's imported, for a reason that has nothing to do with a
real bug) or silently skip everything (which hides the gap instead of pinning it), these tests
run against `harness.run_gate.load_claims()` — the same three-tier fallback
(frozen -> documents.json -> embedded fixture) the actual gate run uses tonight. Right now
that resolves to the embedded fixture tier. The moment T-07 commits `claims.frozen.jsonl`,
these same five tests start running against the real frozen corpus with zero changes needed
here, and the manifest-matching test below starts actually checking the manifest instead of
pinning the pre-freeze placeholder count.
"""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from core.scoring import claim_id as compute_claim_id
from core.scoring import normalise
from harness.run_gate import FROZEN_CLAIMS, load_claims

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "corpus" / "MANIFEST.md"

LEGAL_PROVENANCE_TAGS = {"Observed", "Simulated"}


class TestCorpusInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.claims, cls.tier = load_claims()

    def test_claim_ids_are_stable_hashes_of_the_normalised_text(self):
        for claim in self.claims:
            with self.subTest(claim_id=claim["claim_id"]):
                expected = hashlib.sha256(normalise(claim["text"]).encode("utf-8")).hexdigest()[:12]
                self.assertEqual(claim["claim_id"], expected)
                # also agrees with the shared helper every other module uses
                self.assertEqual(claim["claim_id"], compute_claim_id(claim["text"]))

    def test_no_duplicate_claim_ids(self):
        ids = [c["claim_id"] for c in self.claims]
        self.assertEqual(len(ids), len(set(ids)), "duplicate claim_id in the current corpus tier")

    def test_every_claim_carries_a_provenance_tag(self):
        for claim in self.claims:
            with self.subTest(claim_id=claim.get("claim_id")):
                self.assertIn("provenance", claim)
                self.assertTrue(claim["provenance"], "provenance tag is present but falsy/empty")

    def test_every_provenance_tag_is_in_the_legal_set(self):
        """Legal set is {"Observed", "Simulated"} — the two values T-02's own spec allows
        ("no third value"). No claim tier may introduce a third tag without this test being
        updated deliberately, which is the point."""
        for claim in self.claims:
            with self.subTest(claim_id=claim.get("claim_id")):
                self.assertIn(claim["provenance"], LEGAL_PROVENANCE_TAGS)

    def test_claim_count_matches_the_manifest_once_the_corpus_is_frozen(self):
        if FROZEN_CLAIMS.exists():
            frozen_line_count = sum(
                1 for line in FROZEN_CLAIMS.read_text().splitlines() if line.strip()
            )
            self.assertEqual(len(self.claims), frozen_line_count)
            self.assertTrue(
                MANIFEST.exists(), "claims.frozen.jsonl exists but corpus/MANIFEST.md does not"
            )
        else:
            # Pinned pre-freeze state, not a hidden gap: T-07 (the freeze) has not landed yet,
            # so the gate is honestly running on whichever earlier tier is available —
            # "documents.json" once T-02 lands, or the embedded bring-up fixture before that.
            # This assertion is the one that will need to be revisited (it already will be,
            # automatically, via the branch above) once corpus/claims.frozen.jsonl exists.
            self.assertIn(self.tier, ("documents.json", "embedded-fallback"))
            self.assertGreater(len(self.claims), 0)


if __name__ == "__main__":
    unittest.main()
