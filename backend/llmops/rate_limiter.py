from django.conf import settings
from django.core.cache import cache


class LLMRateLimitExceeded(Exception):
    """Raised when the LLM rate limit has been exceeded."""


class LLMRateLimiter:

    CACHE_KEY = "llmops:rate_limit"

    @classmethod
    def check_and_record(cls):
        window = settings.LLM_RATE_LIMIT_WINDOW_SECONDS
        limit = settings.LLM_RATE_LIMIT_REQUESTS

        created = cache.add(
            cls.CACHE_KEY,
            1,
            timeout=window,
        )

        if created:
            return

        try:
            count = cache.incr(cls.CACHE_KEY)
        except ValueError:
            # The key may have expired between add() and incr().
            cache.add(
                cls.CACHE_KEY,
                1,
                timeout=window,
            )
            return

        if count > limit:
            raise LLMRateLimitExceeded(
                "LLM rate limit exceeded."
            )