"""Named regression test for R-05 (red team, `.crew/BOARD.md`), the worst-shaped defect
found in this repo: `tests/test_killswitch_side_effects.py` was writing its subprocess
mocks straight to the real, git-tracked `deliverables/runs/killswitch.{on,off}.json` —
whichever of `./run.sh test` or `./run.sh killswitch` ran last decided what a judge would
find on disk, and the red team watched it happen twice live (real 97-claim data at 01:56,
reverted to `{"claim_id": "fake-claim-1", "text": "fixture claim", ...}` by a sibling's test
run at 02:03).

The fix for that specific file (redirecting `killswitch.RUNS_DIR` / `ON_SNAPSHOT` /
`OFF_SNAPSHOT` to a temp directory for the duration of its tests) closes the one hole found.
This file closes the *class* of bug instead of the one instance: it asserts, directly, that
running the test suite never changes a single byte under `deliverables/` — the shipped,
git-tracked packet a judge reads. Any future test that writes a fixture to a real
deliverable path, whether under `deliverables/runs/` or anywhere else, fails this test by
construction, without needing to know in advance which file it mutated.

MECHANISM: this test spawns the *entire* suite (`python3 -m unittest discover -s tests`) as
a subprocess and hashes every file under `deliverables/` before and after. Spawning it as a
subprocess, rather than importing and running it in-process, matters: an in-process
re-invocation of `unittest.discover` would re-collect and re-run this very test, which would
spawn another subprocess, which would re-collect this test again — unbounded recursion. The
`PLEDGECHECK_SUITE_PURITY_CHECK_RUNNING` environment variable breaks that cycle: this test
sets it only on the *nested* subprocess's environment, and skips itself immediately if it
finds the flag already set, so the nested run executes every other test in the suite (a real
end-to-end check, not a mock of one) but never re-spawns itself.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DELIVERABLES = ROOT / "deliverables"
GUARD_ENV_VAR = "PLEDGECHECK_SUITE_PURITY_CHECK_RUNNING"


def _hash_tree(root: Path) -> dict[str, str]:
    """{relative path: sha256 of file contents} for every file under `root`, skipping
    __pycache__. Comparing this dict before/after catches an added, removed, or modified
    file anywhere in the tree — not just a changed byte in a file we already know about."""
    hashes: dict[str, str] = {}
    if not root.is_dir():
        return hashes
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


class TestFullSuiteLeavesDeliverablesByteIdentical(unittest.TestCase):
    def test_running_the_full_test_suite_leaves_deliverables_byte_identical(self):
        """The named regression for R-05: no test anywhere in tests/ may change a byte
        under deliverables/, in either direction (order run.sh dispatches: `test` then
        `killswitch`, or `killswitch` then `test` -- both must leave deliverables/
        untouched by the *test suite itself*; `./run.sh killswitch`/`gate`/`compare` are
        expected to write there when run directly, that's their job, but `./run.sh test`
        must not)."""
        if os.environ.get(GUARD_ENV_VAR):
            self.skipTest(
                "running inside the nested suite invocation this test itself starts; "
                "skipping to avoid unbounded recursion"
            )

        before = _hash_tree(DELIVERABLES)

        env = dict(os.environ)
        env[GUARD_ENV_VAR] = "1"
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        after = _hash_tree(DELIVERABLES)

        self.assertEqual(
            result.returncode,
            0,
            f"nested test suite run failed (exit {result.returncode}):\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}",
        )

        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(p for p in (set(before) & set(after)) if before[p] != after[p])

        self.assertEqual(
            (added, removed, changed),
            ([], [], []),
            "running the test suite mutated deliverables/ on disk -- this is the exact "
            f"shape of R-05. added={added} removed={removed} changed={changed}",
        )


if __name__ == "__main__":
    unittest.main()
