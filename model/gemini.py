"""model/gemini.py — the only place in the repo that opens a socket (T-06).

call(prompt: str, *, timeout=60) -> str | None

Kill switch: PLEDGECHECK_NO_MODEL=1, or GEMINI_API_KEY unavailable everywhere this module
checks, means no network call is made at all, "MODEL FALLBACK: <reason>" is logged to
stderr, and None is returned. Every other failure (bad status, timeout, unparseable
response) also returns None with the same loud log — a silent fallback is the bug
(engineering-craft §5.2). Observability and fault-tolerance are different things: the
degraded *output* looks the same in both cases (a caller gets None either way), but the
*reason* is always on stderr, never swallowed.

Key resolution, in order: `os.environ["GEMINI_API_KEY"]` if a caller has already set it
(lets a test or a deployment override without touching disk), otherwise sourced fresh from
`/Users/shivang/Projects/common-ground/.env.local` on every call — a few hundred bytes, so
re-reading it is not worth caching, and re-reading means a value pasted into that file
mid-run takes effect on the next call with no restart. The value is never logged, never
written back to os.environ (no global side effect), never hardcoded.

Model id: gemini-3.6-flash — verified live and present in ListModels as of 23:00 IST
23 Aug 2026 (PLAN.md §12). Do not substitute gemini-2.5-flash (retired, 404s for new
callers) and do not route through ~/.gemini-router (not running tonight, no live keys).

This is the FIRST provider `model/provider.py`'s registry tries each call (see that
module for the selection order and the fallback to `model/featherless.py`, added after
this key's free-tier daily quota was exhausted mid-build — see the "daily-quota fast
fail" note below).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

NAME = "gemini"

MODEL_ID = "gemini-3.6-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent"
ENV_FILE = "/Users/shivang/Projects/common-ground/.env.local"

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0
CALL_SPACING_SECONDS = 4.0
RATE_LIMIT_BACKOFF_SECONDS = 5.0

_last_call_started_at: float | None = None

# Set for the rest of THIS PROCESS the first time a 429 body is confirmed to be Google's
# per-DAY quota (not a per-minute one) — see call()'s 429 handler. A daily cap cannot
# clear itself between the next call and this one a second later, so once confirmed,
# every later call in the same process fails fast instead of burning MAX_ATTEMPTS retries
# and their backoff sleeps on a request that is certain to fail. Each `./run.sh ...`
# subcommand is its own fresh interpreter (see run.sh), so this only saves time *within*
# one multi-batch run (N1's 8 documents, N5's ~7 batches) — it does not, and should not,
# persist across separate invocations, since a fresh key or a quota reset would need a
# fresh check.
_daily_quota_confirmed_exhausted = False


def _log_fallback(reason: str) -> None:
    print(f"MODEL FALLBACK: {reason}", file=sys.stderr)


def _source_env_file(path: str) -> dict[str, str]:
    """Parse simple KEY=VALUE lines — no quoting, no `export`, no interpolation, which
    matches every .env.local this project touches. Returns {} (never raises) if the file
    is missing; never logs a value."""
    try:
        text = open(path, "r", encoding="utf-8").read()
    except OSError:
        return {}
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _resolve_api_key() -> str:
    env_value = os.environ.get("GEMINI_API_KEY")
    if env_value:
        return env_value
    return _source_env_file(ENV_FILE).get("GEMINI_API_KEY", "")


def _retry_after_seconds(exc: urllib.error.HTTPError) -> float | None:
    """Honour a `Retry-After` header if the server sent one (seconds, integer form —
    the only form Gemini's 429 responses use). Returns None if absent or unparsable, so
    the caller falls back to its own backoff schedule."""
    value = exc.headers.get("Retry-After") if exc.headers else None
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _extract_text(payload: dict) -> str:
    """The schema-validation step (engineering-craft §6): a malformed or unexpected
    response shape raises here, and the caller treats that identically to a network
    failure — fallback, not a crash."""
    return payload["candidates"][0]["content"]["parts"][0]["text"]


def _respect_call_spacing() -> None:
    global _last_call_started_at
    if _last_call_started_at is not None:
        elapsed = time.monotonic() - _last_call_started_at
        if elapsed < CALL_SPACING_SECONDS:
            time.sleep(CALL_SPACING_SECONDS - elapsed)
    _last_call_started_at = time.monotonic()


def call(prompt: str, *, timeout: int = 60) -> str | None:
    """POST one prompt to gemini-3.6-flash. Returns the model's text, or None on any
    failure — kill switch, missing key, or a real network/API failure — always with a
    loud stderr log naming the reason. Hard `timeout` seconds per HTTP attempt."""
    global _daily_quota_confirmed_exhausted

    if os.environ.get("PLEDGECHECK_NO_MODEL") == "1":
        _log_fallback("PLEDGECHECK_NO_MODEL=1 (kill switch engaged, no call made)")
        return None

    api_key = _resolve_api_key()
    if not api_key:
        _log_fallback(f"GEMINI_API_KEY not set (checked environment and {ENV_FILE}, no call made)")
        return None

    if _daily_quota_confirmed_exhausted:
        _log_fallback(
            "Gemini daily quota already confirmed exhausted earlier this process "
            "(RESOURCE_EXHAUSTED / GenerateRequestsPerDayPerProjectPerModel) — skipping "
            "retry, no call made"
        )
        return None

    _respect_call_spacing()

    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

    last_reason = "unknown error"
    attempt = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = urllib.request.Request(
            API_URL,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return _extract_text(payload)
        except urllib.error.HTTPError as exc:
            last_reason = f"HTTP {exc.code} from Gemini ({exc.reason})"
            retry_after = _retry_after_seconds(exc)
            if exc.code == 429:
                # Not `body`: that name holds the request payload the retry re-sends.
                error_body = ""
                try:
                    error_body = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
                if "PerDay" in error_body:
                    # Confirmed: Google's own RESOURCE_EXHAUSTED body naming a *daily*
                    # quota metric (e.g. GenerateRequestsPerDayPerProjectPerModel-
                    # FreeTier), not a per-minute one — retrying THIS call cannot
                    # succeed, and neither can any other call in this process today.
                    _daily_quota_confirmed_exhausted = True
                    last_reason = f"HTTP 429 RESOURCE_EXHAUSTED — daily quota (not per-minute): {error_body[:200]}"
                    break
            if exc.code == 429 or exc.code >= 500:
                # Rate-limited or a server-side error — both transient, both worth a
                # retry with backoff. 429 in particular is EXPECTED tonight: this key is
                # shared across every concurrently-running agent in this repo, so
                # "too many requests" is a real, recoverable condition, not a dead key —
                # treating it as non-retryable (the original bug here) turned ordinary
                # contention into what looked like a fully dead model layer.
                if attempt < MAX_ATTEMPTS:
                    time.sleep(retry_after if retry_after is not None else RATE_LIMIT_BACKOFF_SECONDS * attempt)
                continue
            # Any other 4xx (bad key, retired model id, bad request...) — retrying the
            # identical request will not fix it. Fail fast rather than burn attempts and
            # wall-clock time on a request that cannot succeed.
            break
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            last_reason = f"unparseable response ({exc})"
            break  # a parse failure won't be fixed by retrying either
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_reason = f"network error ({exc})"
            # transient — worth a retry with backoff
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    _log_fallback(f"{last_reason} — giving up after {attempt} attempt(s)")
    return None
