"""STUB — raw urllib REST call to gemini-3.6-flash lands in T-06.

call(prompt: str, *, timeout=60) -> str | None
Kill switch: PLEDGECHECK_NO_MODEL=1 or missing GEMINI_API_KEY -> no call, returns None,
logs "MODEL FALLBACK: <reason>" to stderr.
"""
import os
import sys


def call(prompt: str, *, timeout: int = 60):
    if os.environ.get("PLEDGECHECK_NO_MODEL") == "1":
        print("MODEL FALLBACK: PLEDGECHECK_NO_MODEL=1 (stub, T-06 not yet built)", file=sys.stderr)
        return None
    print("MODEL FALLBACK: model/gemini.py is still a T-01 stub (T-06 not yet built)", file=sys.stderr)
    return None
