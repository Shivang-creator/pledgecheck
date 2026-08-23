"""T-05: core/engine.py — load_pack validation and evaluate() semantics. 10 tests."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from core.engine import evaluate, load_pack
from core.probes import UnknownProbe, get_probe
from core.scoring import band_for_score


def _write_pack(tmpdir: Path, data: dict, name: str = "pack.json") -> Path:
    path = tmpdir / name
    path.write_text(json.dumps(data))
    return path


def _minimal_valid_pack() -> dict:
    return {
        "pack_id": "test",
        "version": "0.0.1",
        "probes": [
            {
                "clause_id": "T1",
                "probe": "quantity",
                "weight": 1,
                "citation": "a real source",
                "params": {"regexes": [r"\d+%"]},
            }
        ],
        "bands": [
            {"min": 0, "max": 0, "label": "None"},
            {"min": 1, "max": 1, "label": "Full"},
        ],
        "lexicons": {},
    }


class TestLoadPack(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_pack_raises_on_missing_required_key(self):
        data = _minimal_valid_pack()
        del data["bands"]
        path = _write_pack(self.tmpdir, data)
        with self.assertRaises(ValueError):
            load_pack(path)

    def test_load_pack_raises_on_duplicate_clause_id(self):
        data = _minimal_valid_pack()
        data["probes"].append(copy.deepcopy(data["probes"][0]))
        path = _write_pack(self.tmpdir, data)
        with self.assertRaises(ValueError):
            load_pack(path)

    def test_load_pack_raises_on_empty_citation(self):
        data = _minimal_valid_pack()
        data["probes"][0]["citation"] = "   "
        path = _write_pack(self.tmpdir, data)
        with self.assertRaises(ValueError):
            load_pack(path)

    def test_load_pack_raises_on_zero_probes(self):
        data = _minimal_valid_pack()
        data["probes"] = []
        path = _write_pack(self.tmpdir, data)
        with self.assertRaises(ValueError):
            load_pack(path)

    def test_load_pack_accepts_a_valid_pack_and_returns_its_data(self):
        data = _minimal_valid_pack()
        path = _write_pack(self.tmpdir, data)
        pack = load_pack(path)
        self.assertEqual(pack["pack_id"], "test")
        self.assertEqual(len(pack["probes"]), 1)


class TestEvaluate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_pack = load_pack("rules/climate.v1.json")

    def test_score_arithmetic_counts_one_point_per_present_probe(self):
        claim = {
            "text": (
                "We will cut Scope 1 emissions by 50% by 2030, compared to a 2019 baseline, "
                "overseen by our CEO."
            )
        }
        result = evaluate(claim, self.real_pack)
        present_count = sum(1 for v in result["verdicts"] if v["present"])
        self.assertEqual(result["score"], present_count)
        self.assertEqual(result["max_score"], len(self.real_pack["probes"]))

    def test_band_thresholds_from_the_real_pack_cover_every_reachable_score(self):
        for score in range(0, 6):
            band = band_for_score(score, self.real_pack)
            self.assertIn(score, range(band["min"], band["max"] + 1))

    def test_unknown_probe_name_raises(self):
        with self.assertRaises(UnknownProbe):
            get_probe("not_a_real_probe")

    def test_rule_pack_version_is_asserted_in_output(self):
        claim = {"text": "We will do something vague."}
        result = evaluate(claim, self.real_pack)
        self.assertEqual(result["pack_version"], self.real_pack["version"])

    def test_verdict_ordering_always_follows_pack_order(self):
        claim = {"text": "We will cut emissions by 50% by 2030."}
        result = evaluate(claim, self.real_pack)
        actual_order = [v["clause_id"] for v in result["verdicts"]]
        expected_order = [p["clause_id"] for p in self.real_pack["probes"]]
        self.assertEqual(actual_order, expected_order)

    def test_two_identical_inputs_give_identical_output(self):
        claim = {
            "text": "We will cut Scope 1 emissions by 50% by 2030, per the GHG Protocol, overseen by our CEO."
        }
        first = evaluate(dict(claim), self.real_pack)
        second = evaluate(dict(claim), self.real_pack)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
