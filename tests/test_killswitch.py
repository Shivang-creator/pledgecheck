"""T-05/T-06: the model kill switch.

Written under T-05, before T-06 wired a real model call into `harness/run_gate.py`. Two
of the original assertions turned out to be *stronger than the actual guarantee* once
wiring landed, and are fixed here rather than left to fail — both changes are flagged in
`.crew/LOG.md` and `.crew/DECISIONS.md`, not silently rewritten:

1. The original `test_scores_identical_with_model_on_and_off` asserted the *entire* claims
   list byte-equal between model-on and model-off. That is stronger than the promise
   T-06's own board row makes ("no score, verdict, band or count may change") — the
   `explanation` field is *supposed* to differ, since its whole job is to report whether
   the model actually ran. Fixed to compare only the scoring fields, and to separately
   assert that the on-run's explanations are real generated text, not the placeholder.
2. The original `test_model_layer_field_becomes_the_disabled_placeholder` asserted "off"
   for every reachable scenario, including "a key is configured and the switch is not
   flipped" — true only because nothing called the model yet. Once wired, that scenario
   must be able to report "on" when the model actually produces output, or `model_layer`
   is a decorative field, which is exactly the kind of claim pc-red-team is briefed to
   attack. Split into two tests, one per real outcome.

No test here makes a real network call. `model.explain.call` (the name `model/explain.py`
imports `model.provider.call` as, in its own module namespace — patch site matters more
than definition site for `unittest.mock`) is patched at that boundary, so these assertions
are about `harness/run_gate.py`'s wiring and `model/explain.py`'s batching/parsing, not
about live provider behaviour or tonight's call budget (PLAN.md §10). The one test that
talks to `model.gemini.call` directly (`test_model_fallback_path_logs_loudly_to_stderr`)
forces the kill switch explicitly via `PLEDGECHECK_NO_MODEL=1` rather than relying on the
ambient shell having no `GEMINI_API_KEY` — deterministic regardless of what `.env.local`
holds.

ADDENDUM (Featherless added as a second provider, after Gemini's free-tier daily quota was
exhausted mid-build): `model/explain.py` now imports `call` from `model.provider` (the new
registry/router) instead of `model.gemini` directly — the patch site named above,
`model.explain.call`, is unchanged by that, since `unittest.mock` patches the attribute in
the *importing* module's namespace regardless of where the name originally came from, so
none of the tests below needed to change for that migration alone.
`test_verdicts_identical_across_gemini_featherless_and_off` is new: it pins the actual
architecture claim end to end — every provider this repo can route through, and the kill
switch, produce byte-identical scores/verdicts — by patching `model.gemini.call` and
`model.featherless.call` directly (the exact two functions `model.provider.PROVIDERS`
holds references to), so it exercises the real registry/selection-order logic in
`model/provider.py`, not just `model/explain.py`'s batching.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import unittest
from pathlib import Path
from unittest import mock

import harness.run_gate as run_gate
import model.gemini as gemini

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "deliverables" / "results.json"

# The part of a claim the kill switch actually promises not to change. Deliberately
# excludes `explanation`, which is allowed -- expected -- to differ with the model on vs
# off; that is what the field exists to report.
SCORING_FIELDS = ("claim_id", "text", "score", "max_score", "verdicts", "pack_version")


def _run_gate_with_env(**env_overrides) -> dict:
    original = dict(os.environ)
    try:
        for key, value in env_overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        run_gate.main([])
        return json.loads(RESULTS.read_text())
    finally:
        os.environ.clear()
        os.environ.update(original)


def _scoring_only(claims: list[dict]) -> list[dict]:
    return [{k: c[k] for k in SCORING_FIELDS} for c in claims]


def _stable_hash(data: dict) -> str:
    data = dict(data)
    data.pop("generated_at", None)
    data.pop("model_layer", None)  # metadata *about* the model, expected to differ
    data.pop("model_provider", None)  # metadata *about which backend*, expected to differ
    data["claims"] = _scoring_only(data["claims"])
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _fake_gemini_response(prompt: str, *, timeout: int = 60) -> str:
    """Stands in for a real Gemini response with no network call: echoes back one
    generated-looking rewrite per claim_id found in the prompt, in the exact JSON shape
    `model/explain.py` expects back. Exercises the real batching/parsing/merge code in
    `model/explain.py` and `harness/run_gate.py` — only the HTTP boundary is faked."""
    ids = re.findall(r'"claim_id": "([0-9a-f]+)"', prompt)
    return json.dumps({cid: "Generated: add the missing element in [brackets]." for cid in ids})


def _fake_provider_response(label: str):
    """Same idea as `_fake_gemini_response`, but tagged with `label` so a test can prove
    which provider's fake actually produced a given claim's explanation, and parameterised
    so the same helper stands in for either provider module."""

    def _responder(prompt: str, *, timeout: int = 60) -> str:
        ids = re.findall(r'"claim_id": "([0-9a-f]+)"', prompt)
        return json.dumps({cid: f"Generated by {label}: add the missing element in [brackets]." for cid in ids})

    return _responder


class TestKillSwitch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._original_results = RESULTS.read_text() if RESULTS.exists() else None

    @classmethod
    def tearDownClass(cls):
        # Tests below intentionally re-run the gate and overwrite deliverables/results.json,
        # same as `./run.sh gate` does. Restore whatever was there before this file ran so the
        # test suite has no side effect on the committed deliverable.
        if cls._original_results is not None:
            RESULTS.write_text(cls._original_results)

    def test_scores_identical_with_model_on_and_off(self):
        with mock.patch("model.explain.call", side_effect=_fake_gemini_response):
            on = _run_gate_with_env(PLEDGECHECK_NO_MODEL=None)
        off = _run_gate_with_env(PLEDGECHECK_NO_MODEL="1")
        self.assertEqual(_scoring_only(on["claims"]), _scoring_only(off["claims"]))
        self.assertEqual(on["corpus"], off["corpus"])
        # and confirm the one field that's *allowed* to diverge actually did, so this test
        # cannot pass by accident (e.g. if the model layer silently never fired at all)
        on_explained = [c["explanation"] for c in on["claims"] if c["score"] < c["max_score"]]
        self.assertTrue(on_explained, "fixture corpus has no failing claim to explain")
        self.assertTrue(all(e != "[model layer disabled]" for e in on_explained))

    def test_model_layer_is_off_when_kill_switched_or_the_model_fails(self):
        with self.subTest(scenario="PLEDGECHECK_NO_MODEL=1"):
            output = _run_gate_with_env(PLEDGECHECK_NO_MODEL="1")
            self.assertEqual(output["model_layer"], "off")

        with self.subTest(scenario="model call attempted but fails (dead API / bad key)"):
            with mock.patch("model.explain.call", return_value=None):
                output = _run_gate_with_env(PLEDGECHECK_NO_MODEL=None)
            self.assertEqual(output["model_layer"], "off")
            failing = [c for c in output["claims"] if c["score"] < c["max_score"]]
            self.assertTrue(failing)
            self.assertTrue(all(c["explanation"] == "[model layer disabled]" for c in failing))

    def test_model_layer_turns_on_when_the_model_actually_produces_output(self):
        """Named regression test: T-05's original version of this file asserted "off" was
        the *only* reachable value for model_layer, written before T-06 wired a real call.
        Once wired, a live model run must be able to report "on" -- otherwise the field is
        decorative, which is exactly the kind of claim pc-red-team is briefed to attack."""
        with mock.patch("model.explain.call", side_effect=_fake_gemini_response):
            on = _run_gate_with_env(PLEDGECHECK_NO_MODEL=None)
        self.assertEqual(on["model_layer"], "on")

    def test_results_json_sha256_matches_model_on_and_off(self):
        with mock.patch("model.explain.call", side_effect=_fake_gemini_response):
            on = _run_gate_with_env(PLEDGECHECK_NO_MODEL=None)
        off = _run_gate_with_env(PLEDGECHECK_NO_MODEL="1")
        self.assertEqual(_stable_hash(on), _stable_hash(off))

    def test_verdicts_identical_across_gemini_featherless_and_off(self):
        """The whole architecture claim, pinned directly: every provider this repo can
        route through, and the kill switch, must produce byte-identical scores/verdicts.
        Patches `model.gemini.call` / `model.featherless.call` themselves -- the exact
        two callables `model.provider.PROVIDERS` holds -- so this exercises the real
        registry/selection-order logic in `model/provider.py`, not a bypass of it."""
        with mock.patch("model.gemini.call", side_effect=_fake_provider_response("gemini")), mock.patch(
            "model.featherless.call", return_value=None
        ):
            gemini_arm = _run_gate_with_env(PLEDGECHECK_NO_MODEL=None)

        with mock.patch("model.gemini.call", return_value=None), mock.patch(
            "model.featherless.call", side_effect=_fake_provider_response("featherless")
        ):
            featherless_arm = _run_gate_with_env(PLEDGECHECK_NO_MODEL=None)

        off_arm = _run_gate_with_env(PLEDGECHECK_NO_MODEL="1")

        scoring = [_scoring_only(arm["claims"]) for arm in (gemini_arm, featherless_arm, off_arm)]
        self.assertEqual(scoring[0], scoring[1], "gemini-served and featherless-served verdicts diverged")
        self.assertEqual(scoring[0], scoring[2], "model-on and model-off verdicts diverged")
        self.assertEqual(gemini_arm["corpus"], featherless_arm["corpus"])
        self.assertEqual(gemini_arm["corpus"], off_arm["corpus"])

        # model_provider must truthfully name which backend served each arm -- this is
        # the field a writeup would quote, so it is asserted directly, not just implied
        # by the explanation text.
        self.assertEqual(gemini_arm["model_provider"], "gemini")
        self.assertEqual(featherless_arm["model_provider"], "featherless")
        self.assertEqual(off_arm["model_provider"], "none")

        # and confirm the fields that ARE allowed -- expected -- to differ actually did
        # differ, per arm, so this test cannot pass by a provider silently never firing
        gemini_explained = [c["explanation"] for c in gemini_arm["claims"] if c["score"] < c["max_score"]]
        featherless_explained = [c["explanation"] for c in featherless_arm["claims"] if c["score"] < c["max_score"]]
        off_explained = [c["explanation"] for c in off_arm["claims"] if c["score"] < c["max_score"]]
        self.assertTrue(gemini_explained and featherless_explained and off_explained)
        self.assertTrue(all("gemini" in e for e in gemini_explained))
        self.assertTrue(all("featherless" in e for e in featherless_explained))
        self.assertTrue(all(e == "[model layer disabled]" for e in off_explained))

    def test_model_fallback_path_logs_loudly_to_stderr(self):
        with mock.patch.dict(os.environ, {"PLEDGECHECK_NO_MODEL": "1"}):
            captured = io.StringIO()
            with contextlib.redirect_stderr(captured):
                result = gemini.call("does this claim hold up?")
        self.assertIsNone(result)
        self.assertIn("MODEL FALLBACK", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
