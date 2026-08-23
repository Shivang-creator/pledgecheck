"""harness/killswitch.py — proves the kill switch (T-11's board row, done here on the
Chief's explicit instruction after T-06 landed a real model call: the board's own T-11
spec, written before N5 was wired for real, undercounts what needs stripping — see below).

Runs the full pipeline twice — once with the model on, once with `PLEDGECHECK_NO_MODEL=1`
— writes each raw result to `/tmp/pc_on.json` / `/tmp/pc_off.json`, and diffs them by
sha256 after stripping the fields that are *expected* to differ between the two runs.

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
ON_SNAPSHOT = Path("/tmp/pc_on.json")
OFF_SNAPSHOT = Path("/tmp/pc_off.json")

# Fields expected to differ between the model-on and model-off arms, by design — stripped
# before hashing so the comparison is only over what the guarantee actually covers: every
# score, verdict, band and count.
VOLATILE_TOP_LEVEL_FIELDS = ("generated_at", "model_layer", "model_provider")
VOLATILE_CLAIM_FIELDS = ("explanation",)


def _run_gate(*, no_model: bool) -> dict:
    env = dict(os.environ)
    if no_model:
        env["PLEDGECHECK_NO_MODEL"] = "1"
    else:
        env.pop("PLEDGECHECK_NO_MODEL", None)
    subprocess.run(
        [sys.executable, str(ROOT / "harness" / "run_gate.py")],
        check=True,
        env=env,
        cwd=ROOT,
    )
    return json.loads(RESULTS.read_text())


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
    on = _run_gate(no_model=False)
    ON_SNAPSHOT.write_text(json.dumps(on, indent=2) + "\n")

    off = _run_gate(no_model=True)
    OFF_SNAPSHOT.write_text(json.dumps(off, indent=2) + "\n")

    h_on = _stable_hash(on)
    h_off = _stable_hash(off)

    print("=" * 64)
    print(f"MODEL ON  (layer={on['model_layer']!r}, provider={on.get('model_provider')!r}) sha256: {h_on}")
    print(f"MODEL OFF (layer={off['model_layer']!r}, provider={off.get('model_provider')!r}) sha256: {h_off}")
    print("=" * 64)

    if h_on == h_off:
        print("DIFF: IDENTICAL")
        return 0
    print("DIFF: DIVERGED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
