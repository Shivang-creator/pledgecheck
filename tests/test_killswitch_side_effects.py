"""Named regression test for a shipping bug found by the Crew Chief: running
`./run.sh killswitch` (and therefore `./run.sh all`, which runs killswitch last) used to
destroy the shipped deliverable.

BUG: `harness/killswitch.py` ran `harness/run_gate.py` twice — once with the model on,
once with `PLEDGECHECK_NO_MODEL=1` — and neither invocation passed `--out`, so BOTH arms
wrote straight to `run_gate.py`'s default output path, `deliverables/results.json`. The
model-off arm always ran second, so every killswitch run silently left the real
deliverable — the file the README points a judge at as evidence of 93 real Featherless
explanations — in the model-OFF state: 0 real explanations, every one replaced by
`[model layer disabled]`. Reproduced on disk before this fix: `deliverables/results.json`
had `model_layer: "off"`, `model_provider: "none"`, and 0 of 97 claims with a real
explanation.

FIX (see `harness/killswitch.py`'s module docstring for the full account): both arms now
run with an explicit `--out` pointing at `deliverables/runs/killswitch.{on,off}.json`, so
neither one has a default path left to fall back to clobbering; `main()` additionally
snapshots `deliverables/results.json`'s exact bytes before either arm runs and restores
them in a `finally` block regardless of how the run ends, as a second, independent layer
of the same guarantee.

This test suite never spawns a real `run_gate.py` subprocess (that would mean a live
network call to Featherless/Gemini every test run, which must stay both fast and
deterministic on a machine with no API keys configured at all — e.g. a judge's). Instead
`subprocess.run` is patched with a fake that writes a small, schema-shaped fixture to
whatever `--out` path it is given, so these tests exercise the actual code path that
caused the bug (does killswitch.py pass --out? does it ever target the real path? does the
restore fire even on a mid-run failure?) without depending on live model access.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest import mock

import harness.killswitch as killswitch

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "deliverables" / "results.json"


def _fake_result(*, layer: str, provider: str) -> dict:
    return {
        "pack_version": "test",
        "generated_at": "2026-08-24T00:00:00+00:00",
        "model_layer": layer,
        "model_provider": provider,
        "claim_source": "frozen",
        "claims": [
            {
                "claim_id": "fake-claim-1",
                "text": "fixture claim",
                "score": 3,
                "max_score": 5,
                "verdicts": {},
                "explanation": f"fixture explanation ({layer})",
            }
        ],
        "documents": [],
        "corpus": {"num_claims": 1},
    }


def _fake_subprocess_run(cmd, **kwargs):
    """Stands in for `subprocess.run([python, run_gate.py, "--out", <path>], ...)`:
    inspects the real command line killswitch.py built, and writes a fixture result to
    whatever --out path it named — never to deliverables/results.json — so these tests
    exercise killswitch.py's own wiring, not a real run_gate.py process."""
    out_path = Path(cmd[cmd.index("--out") + 1])
    env = kwargs.get("env") or {}
    no_model = env.get("PLEDGECHECK_NO_MODEL") == "1"
    layer, provider = ("off", "none") if no_model else ("on", "featherless")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(_fake_result(layer=layer, provider=provider)))

    class _CompletedProcess:
        returncode = 0

    return _CompletedProcess()


class TestKillswitchDoesNotClobberResults(unittest.TestCase):
    def setUp(self):
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        self._original = RESULTS.read_bytes() if RESULTS.exists() else None
        # A sentinel deliberately unlike anything either arm's fake subprocess would
        # produce, so a passing test can't be an accident of an absent/empty file.
        self._sentinel = json.dumps(
            {"sentinel": "pre-killswitch deliverable", "model_layer": "on", "real": True}
        ).encode()
        RESULTS.write_bytes(self._sentinel)

    def tearDown(self):
        if self._original is not None:
            RESULTS.write_bytes(self._original)
        elif RESULTS.exists():
            RESULTS.unlink()

    def test_killswitch_does_not_clobber_deliverables_results_json(self):
        """The named regression: this is the exact assertion that would have failed
        against the pre-fix killswitch.py, which left results.json in the model-off
        arm's state after every run."""
        with mock.patch("harness.killswitch.subprocess.run", side_effect=_fake_subprocess_run):
            exit_code = killswitch.main()
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            RESULTS.read_bytes(),
            self._sentinel,
            "deliverables/results.json changed as a side effect of running the killswitch",
        )

    def test_killswitch_never_invokes_run_gate_without_an_explicit_out_path(self):
        """Pins the mechanism of the fix, not just its outcome: every subprocess call
        killswitch.py makes must carry --out, and that --out must never resolve to the
        live deliverable path — omitting --out is exactly what caused the bug."""
        calls = []

        def _spy(cmd, **kwargs):
            calls.append(cmd)
            return _fake_subprocess_run(cmd, **kwargs)

        with mock.patch("harness.killswitch.subprocess.run", side_effect=_spy):
            killswitch.main()

        self.assertEqual(len(calls), 2, "expected exactly one run_gate.py invocation per arm")
        for cmd in calls:
            self.assertIn(
                "--out", cmd, "run_gate.py invoked without --out — falls back to writing deliverables/results.json"
            )
            out_arg = Path(cmd[cmd.index("--out") + 1])
            self.assertNotEqual(
                out_arg.resolve(),
                RESULTS.resolve(),
                "an arm's --out pointed directly at the live deliverable",
            )

    def test_killswitch_restores_results_json_even_if_the_off_arm_raises(self):
        """The finally-block restore (layer 2 of the fix) must fire on a mid-run failure,
        not just on the happy path -- otherwise a flaky subprocess call could still leave
        the deliverable in whatever partial state the on-arm left it."""

        def _flaky_run(cmd, **kwargs):
            out_path_arg = cmd[cmd.index("--out") + 1]
            if "killswitch.off" in out_path_arg:
                raise RuntimeError("simulated failure in the model-off arm")
            return _fake_subprocess_run(cmd, **kwargs)

        with mock.patch("harness.killswitch.subprocess.run", side_effect=_flaky_run):
            with self.assertRaises(RuntimeError):
                killswitch.main()

        self.assertEqual(
            RESULTS.read_bytes(),
            self._sentinel,
            "a mid-run failure in one arm left deliverables/results.json mutated",
        )


if __name__ == "__main__":
    unittest.main()
