"""T-01 walking skeleton: one real, passing test so the suite is green from minute one.

This is not a stub — it genuinely checks the tree that the rest of the board depends on.
The 52-test suite (test_probes, test_engine, test_purity, test_killswitch, test_corpus)
lands in T-05; this file is deliberately small and will keep passing after that lands.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestRepoSkeleton(unittest.TestCase):
    def test_required_tree_exists(self):
        required = [
            "core/__init__.py",
            "core/probes.py",
            "core/engine.py",
            "core/scoring.py",
            "rules/climate.v1.json",
            "model/__init__.py",
            "model/gemini.py",
            "model/segment.py",
            "model/explain.py",
            "harness/run_gate.py",
            "harness/run_baseline.py",
            "harness/compare.py",
            "run.sh",
            "README.md",
            ".gitignore",
            "deliverables/results.json",
            "deliverables/COMPARISON.md",
            "deliverables/NODES.md",
            "deliverables/HONESTY.md",
            "deliverables/flowchart.html",
        ]
        missing = [p for p in required if not (ROOT / p).exists()]
        self.assertEqual(missing, [], f"missing from tree: {missing}")

    def test_gitignore_excludes_env_files(self):
        gitignore = (ROOT / ".gitignore").read_text()
        self.assertIn(".env*", gitignore)


if __name__ == "__main__":
    unittest.main()
