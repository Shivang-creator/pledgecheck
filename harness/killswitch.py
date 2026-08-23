"""harness/killswitch.py — proves the kill switch (T-11's board row, done here on the
Chief's explicit instruction after T-06 landed a real model call: the board's own T-11
spec, written before N5 was wired for real, undercounts what needs stripping — see below).

Runs the full pipeline twice — once with the model on, once with `PLEDGECHECK_NO_MODEL=1`
— writes each raw result to `deliverables/runs/killswitch.on.json` /
`deliverables/runs/killswitch.off.json` (never to `deliverables/results.json`, the shipped
deliverable — see the SHIPPING BUG note below), and diffs them by sha256 after stripping
the fields that are *expected* to differ between the two runs.

SHIPPING BUG FOUND AND FIXED (pc-debugger, flagged in `.crew/DECISIONS.md`): the original
version of this script called `harness/run_gate.py` with no `--out` flag for EITHER arm,
so both the model-on run and the model-off run wrote straight to the default
`deliverables/results.json` path — the file the README tells a judge to inspect as
evidence of the 93 real Featherless explanations. Because the model-off arm always ran
second, every `./run.sh killswitch` (and every `./run.sh all`, which runs killswitch last)
left the shipped deliverable permanently in the model-OFF state: 0 real explanations, 93
placeholders, `model_layer: "off"`. Reproduced before fixing: `deliverables/results.json`
on disk was found in exactly that clobbered state.

The fix is two independent layers, either one of which alone would have been enough:
  1. Both arms are now given an explicit `--out` pointing at a run-scoped file under
     `deliverables/runs/`, so `harness/run_gate.py` never writes to its own default path
     at all during a killswitch run.
  2. `main()` additionally snapshots `deliverables/results.json`'s exact bytes before
     either arm runs, and restores them in a `finally` block regardless of how the run
     ends — so even a future regression that reintroduces a write to the default path
     cannot leave the shipped deliverable mutated.

Named regression test:
`tests/test_killswitch_side_effects.py::TestKillswitchDoesNotClobberResults`.

That strip list is `generated_at`, every claim's `explanation`, `model_layer`, and (added
when the Featherless provider landed) `model_provider` — the board's original T-11 row
named only the first two. `model_layer`/`model_provider` were added here because neither
was meaningful when that row was written: `harness/run_gate.py` hardcoded `model_layer` to
`"off"` unconditionally until T-06 wired a real call, and `model_provider` did not exist
until a second provider did. Once wired, both legitimately differ between the on-arm and
the off-arm BY DESIGN — they are metadata *about which arm ran, and which backend served
it*, exactly like `generated_at` is metadata about *when* it ran. Diffing them alongside
the scores would make this script cry wolf on every single successful proof: two arms that
agree on every verdict would still print DIFF: DIVERGED solely because one arm's labels
correctly say "on"/"featherless" and the other's correctly say "off"/"none". That is not
gaming the check — it is applying the same exclusion principle the board already
established for `generated_at`, extended to the two other fields the board's authors did
not yet know would exist.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "deliverables" / "results.json"
RUNS_DIR = ROOT / "deliverables" / "runs"
ON_SNAPSHOT = RUNS_DIR / "killswitch.on.json"
OFF_SNAPSHOT = RUNS_DIR / "killswitch.off.json"

# Fields expected to differ between the model-on and model-off arms, by design — stripped
# before hashing so the comparison is only over what the guarantee actually covers: every
# score, verdict, band and count.
VOLATILE_TOP_LEVEL_FIELDS = ("generated_at", "model_layer", "model_provider")
VOLATILE_CLAIM_FIELDS = ("explanation",)


def _run_gate(*, no_model: bool, out_path: Path) -> dict:
    """Runs harness/run_gate.py as a subprocess, writing its result to `out_path` —
    NEVER to the default `deliverables/results.json` path. This is layer 1 of the fix for
    the shipping bug described in this module's docstring: passing an explicit --out means
    run_gate.py has no default path to fall back to clobbering."""
    env = dict(os.environ)
    if no_model:
        env["PLEDGECHECK_NO_MODEL"] = "1"
    else:
        env.pop("PLEDGECHECK_NO_MODEL", None)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, str(ROOT / "harness" / "run_gate.py"), "--out", str(out_path)],
        check=True,
        env=env,
        cwd=ROOT,
    )
    return json.loads(out_path.read_text())


def _stable_hash(data: dict) -> str:
    data = dict(data)
    for field in VOLATILE_TOP_LEVEL_FIELDS:
        data.pop(field, None)
    data["claims"] = [
        {k: v for k, v in claim.items() if k not in VOLATILE_CLAIM_FIELDS}
        for claim in data.get("claims", [])
    ]
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def main() -> int:
    # Layer 2 of the fix: snapshot deliverables/results.json's exact bytes (or its
    # absence) before either arm runs, and restore that exact state in `finally` no matter
    # what happens above — a real safety net, not a courtesy, since layer 1 (the --out
    # flag in _run_gate) already means neither arm SHOULD touch this path at all.
    original_results = RESULTS.read_bytes() if RESULTS.exists() else None

    exit_code = 1
    try:
        on = _run_gate(no_model=False, out_path=ON_SNAPSHOT)
        off = _run_gate(no_model=True, out_path=OFF_SNAPSHOT)

        h_on = _stable_hash(on)
        h_off = _stable_hash(off)

        print("=" * 64)
        print(f"MODEL ON  (layer={on['model_layer']!r}, provider={on.get('model_provider')!r}) sha256: {h_on}")
        print(f"MODEL OFF (layer={off['model_layer']!r}, provider={off.get('model_provider')!r}) sha256: {h_off}")
        print("=" * 64)

        if h_on == h_off:
            print("DIFF: IDENTICAL")
            exit_code = 0
        else:
            print("DIFF: DIVERGED")
            exit_code = 1
    finally:
        if original_results is not None:
            RESULTS.write_bytes(original_results)
            print(f"deliverables/results.json restored to its pre-killswitch state ({len(original_results)} bytes) — untouched by this run")
        elif RESULTS.exists():
            RESULTS.unlink()
            print("deliverables/results.json did not exist before this run — removed")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
