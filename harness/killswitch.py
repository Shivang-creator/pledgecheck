"""STUB — real T-11 implementation runs the full pipeline twice (model on / off) and
diffs deliverables/results.json by sha256, ignoring generated_at and explanation.

Runnable today: runs the current (stub) run_gate.py twice, once with
PLEDGECHECK_NO_MODEL unset and once set, strips generated_at, and diffs. Since run_gate
is itself still a fixture, this is honest about what it is testing right now — it proves
the plumbing, not yet the real model boundary. T-11 replaces the body.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "deliverables" / "results.json"


def _run_gate_and_hash(no_model: bool) -> str:
    env = dict(os.environ)
    if no_model:
        env["PLEDGECHECK_NO_MODEL"] = "1"
    else:
        env.pop("PLEDGECHECK_NO_MODEL", None)
    subprocess.run([sys.executable, str(ROOT / "harness" / "run_gate.py")], check=True, env=env, cwd=ROOT)
    data = json.loads(RESULTS.read_text())
    data.pop("generated_at", None)
    for c in data.get("claims", []):
        c.pop("explanation", None)
    stable = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(stable).hexdigest()


def main():
    h_on = _run_gate_and_hash(no_model=False)
    h_off = _run_gate_and_hash(no_model=True)
    print(h_on)
    print(h_off)
    if h_on == h_off:
        print("DIFF: IDENTICAL")
        return 0
    print("DIFF: DIVERGED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
