"""The five Checkability Gate probes (T-04).

Pure functions over a claim's text plus the rule-pack's `params` for this clause and the
pack's shared `lexicons`. No model, no network — every literal that decides a verdict
(a regex, a year range, a lexicon term) lives in the rule-pack JSON, not here. See
rules/climate.v1.json.

Allowed imports in core/: re, json, hashlib, dataclasses, pathlib. Nothing else.
Enforced by tests/test_purity.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProbeResult:
    present: bool
    span: tuple[int, int] | None
    matched: str | None


class UnknownProbe(Exception):
    """Raised when a rule pack names a probe with no matching function in PROBES."""


def probe_quantity(text: str, params: dict, lexicons: dict) -> ProbeResult:
    """Is there a quantified amount (a number, percentage or unit) in the claim?

    Deliberately narrow: word-numbers like "halve" or "net-zero" are a DOCUMENTED miss
    (params["known_miss_words"] exists for the test suite to pin, not for this function to
    special-case). A claim that only uses a word-number scores this probe absent — that is
    the Gate's honest weakness, not a bug.
    """
    for pattern in params.get("regexes", []):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return ProbeResult(True, (m.start(), m.end()), m.group())
    return ProbeResult(False, None, None)


def _year_with_context(text: str, params: dict) -> ProbeResult:
    """Shared logic for target_year and baseline_year: a year in range, near a context word."""
    year_re = re.compile(params["year_regex"])
    min_year = params["min_year"]
    max_year = params["max_year"]
    window = params.get("context_window_chars", 60)
    context_words = [w.lower() for w in params.get("context_words", [])]
    lower_text = text.lower()

    for m in year_re.finditer(text):
        try:
            year = int(m.group())
        except ValueError:
            continue
        if not (min_year <= year <= max_year):
            continue
        start = max(0, m.start() - window)
        end = min(len(text), m.end() + window)
        surrounding = lower_text[start:end]
        if any(word in surrounding for word in context_words):
            return ProbeResult(True, (m.start(), m.end()), m.group())
    return ProbeResult(False, None, None)


def probe_target_year(text: str, params: dict, lexicons: dict) -> ProbeResult:
    """Is there a future year, in context, that the claim is aiming at?"""
    return _year_with_context(text, params)


def probe_baseline_year(text: str, params: dict, lexicons: dict) -> ProbeResult:
    """Is there a baseline/reference year the claim's reduction is measured against?"""
    return _year_with_context(text, params)


def _term_pattern(term: str) -> str:
    """Build a regex for a lexicon term that matches any whitespace run (regular space,
    non-breaking space, tab...) between its words, not only the literal ASCII space the
    term happens to be authored with. Bug found writing tests/test_probes.py: a multi-word
    lexicon term failed to match text scraped with a non-breaking space between two of its
    words, because re.escape() on a plain space only matches that exact character.
    See test_accountable_party_matches_across_nbsp_word_gap."""
    return r"\s+".join(re.escape(word) for word in term.split())


def _lexicon_search(text: str, params: dict, lexicons: dict) -> ProbeResult:
    lexicon_key = params["lexicon_key"]
    terms = lexicons.get(lexicon_key, [])
    flags = re.IGNORECASE if params.get("case_insensitive", True) else 0
    # Longest term first so a full-name lexicon entry wins over its acronym when both
    # would match at the same position — cosmetic only, does not change presence.
    for term in sorted(terms, key=len, reverse=True):
        m = re.search(_term_pattern(term), text, flags)
        if m:
            return ProbeResult(True, (m.start(), m.end()), text[m.start():m.end()])
    return ProbeResult(False, None, None)


def probe_named_standard(text: str, params: dict, lexicons: dict) -> ProbeResult:
    """Does the claim name a standard, scope or framework a reader could look up?"""
    return _lexicon_search(text, params, lexicons)


def probe_accountable_party(text: str, params: dict, lexicons: dict) -> ProbeResult:
    """Does the claim name a person or body accountable for the commitment?"""
    return _lexicon_search(text, params, lexicons)


PROBES = {
    "quantity": probe_quantity,
    "target_year": probe_target_year,
    "baseline_year": probe_baseline_year,
    "named_standard": probe_named_standard,
    "accountable_party": probe_accountable_party,
}


def get_probe(name: str):
    try:
        return PROBES[name]
    except KeyError as exc:
        raise UnknownProbe(f"no probe function registered for {name!r}") from exc
