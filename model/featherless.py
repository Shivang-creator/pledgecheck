"""model/featherless.py — second model provider (Featherless.AI), added after Gemini's
free-tier daily quota (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, limit 20,
model gemini-3.6-flash) was exhausted mid-build and would not reset until ~12:30 IST,
after the 07:00 IST deadline (see .crew/DECISIONS.md, the T-06 amendment).

call(prompt: str, *, timeout=60) -> str | None

Same public shape as `model.gemini.call` on purpose: `model/provider.py` (the registry)
treats every provider module interchangeably by that shape alone, so this file is the
proof the abstraction is real — nothing outside `model/` changed to add it.

Featherless is Shivang's flat-rate, OpenAI-compatible subscription: no per-token billing
and (unlike Gemini's free tier) no daily request quota, so it is the second rung of the
selection order (Gemini if it has quota, else Featherless, else the deterministic
fallback), not a replacement for Gemini.

Kill switch: identical contract to every other provider — PLEDGECHECK_NO_MODEL=1, or no
usable key, means no network call is made, "MODEL FALLBACK: <reason>" is logged to
stderr, and None is returned. Every other failure (bad status, timeout, unparseable
response) also returns None with the same loud log.

Key/base-url/model resolution, in order: `os.environ` first (lets a test or a deployment
override without touching disk), else all three (`FEATHERLESS_API_KEY`,
`FEATHERLESS_BASE_URL`, `FEATHERLESS_MODEL`) sourced fresh from
`/Users/shivang/Projects/deadline-agent/.env.local` on every call, deliberately read
together from ONE file rather than merged across files: `common-ground/.env.local` also
defines `FEATHERLESS_API_KEY` but with a *different* value and no base-url/model at all —
pairing a key from one file with a base-url/model default from elsewhere risks sending a
request under the wrong account. `deadline-agent/.env.local` is the only file tonight with
all three vars defined together, so that is the one source of truth here. Never logged,
never written back to os.environ, never hardcoded (the module-level constants below are
fallback *defaults* only, used if the env/file value is genuinely absent — not silent
overrides of a present value).

SPONSOR-SDK BUG FOUND AND WORKED AROUND: a bare `urllib.request` POST to
`https://api.featherless.ai/v1/chat/completions` with no `User-Agent` header gets
`HTTP 403` with body `error code: 1010` from Cloudflare — "no User-Agent, or a blocked
one" (Cloudflare's own error-code page for 1010), not anything about the API key or the
request body. It is not documented on Featherless's own API reference as a requirement.
Minimal repro: same request, add a real `User-Agent` string, 403 -> 200. Worked around by
always sending one below; nothing else about the request changed between the failing and
passing attempt (verified by hand before this module was written, not assumed).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

NAME = "featherless"

DEFAULT_BASE_URL = "https://api.featherless.ai/v1"
DEFAULT_MODEL_ID = "deepseek-ai/DeepSeek-V3-0324"
ENV_FILE = "/Users/shivang/Projects/deadline-agent/.env.local"
USER_AGENT = "pledgecheck/1.0 (+reverie-2026 hackathon build; contact via Devpost)"

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0
RATE_LIMIT_BACKOFF_SECONDS = 5.0


def _log_fallback(reason: str) -> None:
    print(f"MODEL FALLBACK: {reason}", file=sys.stderr)


def _source_env_file(path: str) -> dict[str, str]:
    """Parse simple KEY=VALUE lines — no quoting, no `export`, no interpolation. Returns
    {} (never raises) if the file is missing; never logs a value. Mirrors
    model.gemini._source_env_file exactly; duplicated rather than shared so each provider
    module stays a fully self-contained, independently-removable file."""
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


def _resolve_config() -> tuple[str, str, str]:
    """Returns (api_key, base_url, model_id). api_key is "" if unresolvable anywhere —
    the caller treats that as "no usable key", same as every other provider."""
    api_key = os.environ.get("FEATHERLESS_API_KEY")
    base_url = os.environ.get("FEATHERLESS_BASE_URL")
    model_id = os.environ.get("FEATHERLESS_MODEL")
    if not (api_key and base_url and model_id):
        file_values = _source_env_file(ENV_FILE)
        api_key = api_key or file_values.get("FEATHERLESS_API_KEY", "")
        base_url = base_url or file_values.get("FEATHERLESS_BASE_URL") or DEFAULT_BASE_URL
        model_id = model_id or file_values.get("FEATHERLESS_MODEL") or DEFAULT_MODEL_ID
    return api_key, base_url, model_id


def _retry_after_seconds(exc: urllib.error.HTTPError) -> float | None:
    value = exc.headers.get("Retry-After") if exc.headers else None
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _extract_text(payload: dict) -> str:
    """Schema-validation step (engineering-craft §6): a malformed or unexpected OpenAI-
    compatible response shape raises here, and the caller treats that identically to a
    network failure — fallback, not a crash."""
    return payload["choices"][0]["message"]["content"]


def call(prompt: str, *, timeout: int = 60) -> str | None:
    """POST one prompt to Featherless's OpenAI-compatible chat/completions endpoint.
    Returns the model's text, or None on any failure — kill switch, missing config, or a
    real network/API failure — always with a loud stderr log naming the reason. Hard
    `timeout` seconds per HTTP attempt."""
    if os.environ.get("PLEDGECHECK_NO_MODEL") == "1":
        _log_fallback("PLEDGECHECK_NO_MODEL=1 (kill switch engaged, no call made) [featherless]")
        return None

    api_key, base_url, model_id = _resolve_config()
    if not api_key:
        _log_fallback(
            f"FEATHERLESS_API_KEY not set (checked environment and {ENV_FILE}, no call made) [featherless]"
        )
        return None

    body = json.dumps({"model": model_id, "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")

    last_reason = "unknown error"
    attempt = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                # Required: Cloudflare in front of api.featherless.ai returns HTTP 403
                # ("error code: 1010") for requests with no/blocked User-Agent — see the
                # module docstring for the minimal repro. Dropping this header silently
                # turns a working key into what looks like an auth failure.
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return _extract_text(payload)
        except urllib.error.HTTPError as exc:
            last_reason = f"HTTP {exc.code} from Featherless ({exc.reason})"
            retry_after = _retry_after_seconds(exc)
            if exc.code == 429 or exc.code >= 500:
                # Transient — rate-limited or a server-side error — worth a retry with
                # backoff, same policy as model/gemini.py.
                if attempt < MAX_ATTEMPTS:
                    time.sleep(retry_after if retry_after is not None else RATE_LIMIT_BACKOFF_SECONDS * attempt)
                continue
            # Any other 4xx (bad key, bad model id, bad request...) — retrying the
            # identical request will not fix it.
            break
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            last_reason = f"unparseable response ({exc})"
            break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_reason = f"network error ({exc})"
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    _log_fallback(f"{last_reason} — giving up after {attempt} attempt(s) [featherless]")
    return None
