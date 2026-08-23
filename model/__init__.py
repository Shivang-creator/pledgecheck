"""Pledgecheck model layer.

The only place in the repo that opens a socket (T-06: gemini.py, featherless.py,
provider.py, segment.py, explain.py). `provider.py` is the one public entry point
(`model.provider.call`) — segment.py and explain.py never talk to a specific provider
module directly. Every entry point here honours PLEDGECHECK_NO_MODEL=1, and every
provider's own key/config being unavailable, as a hard kill switch: no network call is
made, a caller gets None (or the batch-level DISABLED_PLACEHOLDER from explain.py), and
the reason is always logged loudly to stderr — including which provider, if any, actually
served a given call (`MODEL PROVIDER: <name> served this call`).
"""
