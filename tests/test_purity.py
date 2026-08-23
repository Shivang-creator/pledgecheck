"""T-05: the boundary test. `core/` is the deterministic Checkability Gate — it must import
no model, no network, no framework, ever. This file is what makes that a provable claim
instead of a sentence in a writeup.

Judgment call (recorded in .crew/DECISIONS.md): the board's allowlist is
{re, json, hashlib, dataclasses, pathlib}. Two additions were necessary to avoid a vacuous
allowlist that fails on the code as written, for reasons that have nothing to do with the
model/network/framework boundary the test exists to protect:
  - `__future__` (the `from __future__ import annotations` pragma): a compile-time typing
    directive built into the language itself, not a third-party or stdlib runtime dependency.
  - intra-package imports (`core.probes`, `core.scoring`, ...): core/ modules importing each
    other is exactly the boundary staying inside itself, not crossing it.
Both are still enforced against everything else — `import os`, `import requests`,
`from model import gemini`, etc. all still fail this test.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"

ALLOWED_TOP_LEVEL = {"re", "json", "hashlib", "dataclasses", "pathlib", "__future__"}

# The known real modules as of T-04/T-05. Used only as a *floor* for the anti-vacuous check
# below (test_core_imports_only_allowlisted_stdlib), never as an exact-set match — new core
# modules are allowed to exist later without breaking this test. What must never happen again
# is the scan finding zero files and passing by default, which is what a renamed/typo'd CORE
# path would silently do.
KNOWN_CORE_MODULES = {"probes.py", "engine.py", "scoring.py"}


def _core_python_files() -> list[Path]:
    if not CORE.is_dir():
        return []
    return sorted(p for p in CORE.rglob("*.py") if "__pycache__" not in p.parts)


def _imported_top_level_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.module is None:
                # `from . import x` style relative import — stays inside the package.
                names.add("core")
            else:
                names.add((node.module or "").split(".")[0])
    return names


def _is_allowed(name: str) -> bool:
    return name in ALLOWED_TOP_LEVEL or name == "core"


class TestCorePurity(unittest.TestCase):
    def test_core_imports_only_allowlisted_stdlib(self):
        files = _core_python_files()

        # Anti-vacuous half: prove the scan actually looked at real files, not an empty or
        # missing directory. If `core/` were renamed, `files` would be `[]` and every
        # assertion below this point would trivially pass — that is the exact failure mode
        # this guards against.
        self.assertGreaterEqual(
            len(files), 4,
            f"expected to scan at least 4 files under {CORE}, found {len(files)}: {files} "
            "— if this is 0, the scan is vacuous (wrong path / renamed directory), not clean",
        )
        scanned_names = {p.name for p in files}
        missing_known = KNOWN_CORE_MODULES - scanned_names
        self.assertEqual(
            missing_known, set(),
            f"expected known core modules {KNOWN_CORE_MODULES} to be part of the scan; "
            f"missing {missing_known} — the guard did not actually see them",
        )

        violations: dict[str, set[str]] = {}
        for path in files:
            tree = ast.parse(path.read_text(), filename=str(path))
            imported = _imported_top_level_names(tree)
            forbidden = {n for n in imported if not _is_allowed(n)}
            if forbidden:
                violations[str(path.relative_to(ROOT))] = forbidden

        self.assertEqual(
            violations, {},
            f"core/ imported something outside {ALLOWED_TOP_LEVEL} (+ intra-package): "
            f"{violations}",
        )

    def test_core_never_reads_os_environ(self):
        files = _core_python_files()
        self.assertGreaterEqual(len(files), 4, "vacuous scan: found no core/ files")
        offenders = [
            str(p.relative_to(ROOT)) for p in files if "os.environ" in p.read_text()
        ]
        self.assertEqual(offenders, [], f"core/ reads os.environ in: {offenders}")

    def test_core_never_contains_http_substring(self):
        files = _core_python_files()
        self.assertGreaterEqual(len(files), 4, "vacuous scan: found no core/ files")
        offenders = [
            str(p.relative_to(ROOT)) for p in files if "http" in p.read_text().lower()
        ]
        self.assertEqual(offenders, [], f"core/ contains the substring 'http' in: {offenders}")


if __name__ == "__main__":
    unittest.main()
