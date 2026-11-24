"""Regression: a per-minute 429 must be retried with the SAME request body.

The 429 handler reused the name `body` for the error text it read back, so the retry
POSTed that string (a str, not bytes) instead of the prompt. urllib raised TypeError,
which was caught as "unparseable response", and the call gave up after one attempt —
the advertised 429 retry never happened.
"""
import io
import json
import unittest
import urllib.error
from unittest import mock

from model import gemini


def _ok_response():
    payload = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
    resp = mock.MagicMock()
    resp.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
    return resp


class GeminiRetryTest(unittest.TestCase):
    def test_per_minute_429_is_retried_with_the_original_prompt(self):
        sent = []

        def fake_urlopen(request, timeout):
            sent.append(request.data)
            if len(sent) == 1:
                raise urllib.error.HTTPError(
                    gemini.API_URL, 429, "Too Many Requests", {},
                    io.BytesIO(b'{"error": "PerMinute quota"}'),
                )
            return _ok_response()

        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), \
                mock.patch.object(gemini, "_daily_quota_confirmed_exhausted", False), \
                mock.patch.object(gemini, "_respect_call_spacing"), \
                mock.patch.object(gemini.time, "sleep"), \
                mock.patch.object(gemini.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = gemini.call("the prompt")

        self.assertEqual(result, "ok")
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[0], sent[1])
        self.assertIn(b"the prompt", sent[1])


if __name__ == "__main__":
    unittest.main()
