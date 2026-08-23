"""Unit tests for model/provider.py — the registry/router added when Featherless became a
second provider. Complements tests/test_killswitch.py's end-to-end
`test_verdicts_identical_across_gemini_featherless_and_off`: these tests are about the
router's own selection-order/logging/bookkeeping logic in isolation, not about
`harness/run_gate.py`'s wiring around it. No test here makes a real network call — every
provider's `call` is mocked directly.
"""
from __future__ import annotations

import contextlib
import io
import os
import unittest
from unittest import mock

import model.provider as provider


class TestProviderRegistry(unittest.TestCase):
    def setUp(self):
        provider.reset_providers_used()

    def test_registry_contains_gemini_then_featherless_in_that_order(self):
        # Selection order is architecturally significant (Gemini if it has quota, else
        # Featherless) -- pin the order itself, not just that both are present.
        names = [p.NAME for p in provider.PROVIDERS]
        self.assertEqual(names, ["gemini", "featherless"])

    def test_kill_switch_prevents_every_provider_from_being_called(self):
        with mock.patch("model.gemini.call") as gemini_call, mock.patch("model.featherless.call") as featherless_call:
            with mock.patch.dict(os.environ, {"PLEDGECHECK_NO_MODEL": "1"}):
                captured = io.StringIO()
                with contextlib.redirect_stderr(captured):
                    result = provider.call("does this claim hold up?")
        self.assertIsNone(result)
        gemini_call.assert_not_called()
        featherless_call.assert_not_called()
        self.assertIn("MODEL FALLBACK", captured.getvalue())
        self.assertIn("PLEDGECHECK_NO_MODEL=1", captured.getvalue())
        self.assertEqual(provider.providers_used, set())

    def test_gemini_success_short_circuits_featherless(self):
        with mock.patch("model.gemini.call", return_value="gemini text") as gemini_call, mock.patch(
            "model.featherless.call"
        ) as featherless_call:
            captured = io.StringIO()
            with contextlib.redirect_stderr(captured):
                result = provider.call("prompt")
        self.assertEqual(result, "gemini text")
        gemini_call.assert_called_once()
        featherless_call.assert_not_called()
        self.assertIn("MODEL PROVIDER: gemini served this call", captured.getvalue())
        self.assertEqual(provider.providers_used, {"gemini"})
        self.assertEqual(provider.last_provider, "gemini")

    def test_gemini_failure_falls_through_to_featherless(self):
        with mock.patch("model.gemini.call", return_value=None), mock.patch(
            "model.featherless.call", return_value="featherless text"
        ) as featherless_call:
            captured = io.StringIO()
            with contextlib.redirect_stderr(captured):
                result = provider.call("prompt")
        self.assertEqual(result, "featherless text")
        featherless_call.assert_called_once()
        self.assertIn("MODEL PROVIDER: featherless served this call", captured.getvalue())
        self.assertEqual(provider.providers_used, {"featherless"})
        self.assertEqual(provider.last_provider, "featherless")

    def test_every_provider_failing_returns_none_and_logs_loudly(self):
        with mock.patch("model.gemini.call", return_value=None), mock.patch(
            "model.featherless.call", return_value=None
        ):
            captured = io.StringIO()
            with contextlib.redirect_stderr(captured):
                result = provider.call("prompt")
        self.assertIsNone(result)
        self.assertIn("MODEL FALLBACK", captured.getvalue())
        self.assertIn("every provider", captured.getvalue())
        self.assertEqual(provider.providers_used, set())
        self.assertIsNone(provider.last_provider)

    def test_providers_used_accumulates_across_calls_until_reset(self):
        with mock.patch("model.gemini.call", return_value="a"), mock.patch("model.featherless.call", return_value=None):
            provider.call("prompt one")
        with mock.patch("model.gemini.call", return_value=None), mock.patch(
            "model.featherless.call", return_value="b"
        ):
            provider.call("prompt two")
        self.assertEqual(provider.providers_used, {"gemini", "featherless"})

        provider.reset_providers_used()
        self.assertEqual(provider.providers_used, set())
        self.assertIsNone(provider.last_provider)

    def test_call_signature_matches_every_provider_module(self):
        # The whole abstraction rests on every provider exposing the identical shape.
        # Adding a provider that doesn't match this would be a silent contract break.
        import inspect

        for mod in provider.PROVIDERS:
            sig = inspect.signature(mod.call)
            params = list(sig.parameters)
            self.assertEqual(params[0], "prompt")
            self.assertIn("timeout", sig.parameters)
            self.assertTrue(hasattr(mod, "NAME") and isinstance(mod.NAME, str) and mod.NAME)


if __name__ == "__main__":
    unittest.main()
