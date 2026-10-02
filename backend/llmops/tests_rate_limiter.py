from django.core.cache import cache
from django.test import TestCase, override_settings

from llmops.rate_limiter import LLMRateLimiter, LLMRateLimitExceeded


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "llmops-rate-limit-tests",
        }
    }
)
class RateLimiterTests(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        super().tearDown()
        cache.clear()

    @override_settings(
        LLM_RATE_LIMIT_REQUESTS=3,
        LLM_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_allows_requests_within_limit(self):
        for _ in range(3):
            LLMRateLimiter.check_and_record()

    @override_settings(
        LLM_RATE_LIMIT_REQUESTS=3,
        LLM_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_raises_when_limit_exceeded(self):
        for _ in range(3):
            LLMRateLimiter.check_and_record()

        with self.assertRaises(LLMRateLimitExceeded):
            LLMRateLimiter.check_and_record()

    @override_settings(
        LLM_RATE_LIMIT_REQUESTS=1,
        LLM_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_respects_configured_limit_of_one(self):
        LLMRateLimiter.check_and_record()

        with self.assertRaises(LLMRateLimitExceeded):
            LLMRateLimiter.check_and_record()

    @override_settings(
        LLM_RATE_LIMIT_REQUESTS=2,
        LLM_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_reset_after_window_allows_requests_again(self):
        LLMRateLimiter.check_and_record()
        LLMRateLimiter.check_and_record()

        # Simulate the window expiring (LocMem has no clock-based eviction
        # granularity we can wait for, so delete the key directly).
        cache.delete(LLMRateLimiter.CACHE_KEY)

        LLMRateLimiter.check_and_record()

    def test_cache_key_is_namespaced_under_llmops(self):
        self.assertEqual(LLMRateLimiter.CACHE_KEY, "llmops:rate_limit")