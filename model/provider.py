"""model/provider.py — the model layer's ONE public entry point and provider registry.

`model/segment.py` (N1) and `model/explain.py` (N5) call `model.provider.call(...)` and
nothing else — they do not know or care whether a given prompt was ultimately answered by
Gemini, Featherless, or nobody. Everything about *which backend served this call, and in
what order backends are tried* is decided here, in exactly one place. That is the whole
point of the abstraction, and this file is the proof it held: adding Featherless tonight
was one new module (`model/featherless.py`, same `call(prompt, *, timeout=60) -> str|None`
shape as `model/gemini.py`) plus one line in PROVIDERS below. Nothing in `core/`, nothing
in `harness/run_gate.py`'s scoring path, and nothing in the Checkability Gate itself
changed to add a provider — if it had, the boundary would have been wrong.

Selection order: PROVIDERS, tried in order, first call() that returns non-None wins.
Tonight that is (gemini, featherless) — Gemini if it still has quota, else Featherless,
else the deterministic fallback every caller already implements for "the model returned
None" (model/segment.py falls back to the naive splitter's caller; model/explain.py's
DISABLED_PLACEHOLDER). Every provider module owns its OWN kill-switch check and its own
loud "MODEL FALLBACK: <reason>" log on every failure path (defense in depth: a provider
called directly, bypassing this router, still degrades safely and loudly) — this module
adds ONE more kill-switch check ahead of all of them so that, when the switch is engaged,
no provider is attempted at all and exactly one top-level log line is produced instead of
one per provider.

`providers_used` / `reset_providers_used()` / `last_provider`: lightweight, best-effort
provenance for the one honest claim this file exists to make possible — "which model
actually wrote these explanations" (engineering-craft §6/§7: a fallback must never hide
which arm ran). `providers_used` accumulates the NAME of every provider whose call()
returned non-None text since the last reset; `harness/run_gate.py` resets it at the start
of each run and reads it back into a `model_provider` field on the deliverable. This is a
call-level signal ("a provider answered"), not a claim-level one ("this exact sentence was
written by X") — N5 batches several claims per call, and if a batch's JSON happens to fail
to parse after a provider answered, that provider still appears in `providers_used` even
though every claim in that batch fell back to the disabled placeholder. Given tonight's
real behaviour (Gemini's failure is a daily quota, uniform for the whole process — see
model/gemini.py's `_daily_quota_confirmed_exhausted` — so a run is served by exactly one
provider throughout, not a shifting mix), this granularity is honest in practice; it is
documented here rather than engineered away because the finer-grained (per-claim) version
was judged not worth the added schema complexity tonight.
"""
from __future__ import annotations

import os
import sys

from model import gemini, featherless

# The registry. Each entry must expose call(prompt: str, *, timeout: int = 60) -> str|None
# and a module-level NAME string. Adding a provider: write model/<name>.py with that
# shape, import it above, add it to this tuple. No caller of model.provider.call changes.
PROVIDERS = (gemini, featherless)

# Names of every provider that has successfully returned text since the last
# reset_providers_used() call. A plain set, not a dict-of-counts: harness/run_gate.py only
# ever needs to report WHICH provider(s) served a run, not how many times each did.
providers_used: set[str] = set()

# The provider that served the most recent successful call(), or None if the last call
# (if any) returned nothing. Read by nothing today beyond providers_used bookkeeping
# below, but exposed for any future per-call caller that wants finer-grained attribution
# than the run-level `providers_used` set gives.
last_provider: str | None = None


def reset_providers_used() -> None:
    """Called once per pipeline run (harness/run_gate.py, harness/run_baseline.py) before
    any model calls are made, so provenance from a previous run/test in the same process
    never leaks into this one."""
    global last_provider
    providers_used.clear()
    last_provider = None


def call(prompt: str, *, timeout: int = 60) -> str | None:
    """Try each provider in PROVIDERS, in order; return the first non-None result. Logs
    loudly which provider served the call, or that every provider failed. Returns None
    only if the kill switch is engaged or every provider in the registry failed — in both
    cases every provider (or this function itself) has already logged the reason to
    stderr; nothing here duplicates or swallows that."""
    global last_provider

    if os.environ.get("PLEDGECHECK_NO_MODEL") == "1":
        print(
            "MODEL FALLBACK: PLEDGECHECK_NO_MODEL=1 (kill switch engaged, no provider attempted)",
            file=sys.stderr,
        )
        last_provider = None
        return None

    for provider in PROVIDERS:
        result = provider.call(prompt, timeout=timeout)
        if result is not None:
            print(f"MODEL PROVIDER: {provider.NAME} served this call", file=sys.stderr)
            providers_used.add(provider.NAME)
            last_provider = provider.NAME
            return result

    print(
        "MODEL FALLBACK: every provider in the registry failed this call "
        f"({', '.join(p.NAME for p in PROVIDERS)}) — degrading to the deterministic "
        "fallback (see the MODEL FALLBACK line above from each provider for why)",
        file=sys.stderr,
    )
    last_provider = None
    return None
