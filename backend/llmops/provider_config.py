from dataclasses import dataclass
from django.conf import settings


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str
    model: str
    base_url: str
    api_key: str
    timeout: int

class LLMProviderConfigurationError(Exception):
    """Raised when an LLM provider configuration is invalid."""

class LLMProviderConfigService:

    @staticmethod
    def get_primary() -> LLMProviderConfig:
        return LLMProviderConfig(
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            timeout=settings.LLM_TIMEOUT,
        )

    @staticmethod
    def get_fallback():
        if not settings.LLM_FALLBACK_MODEL:
            return None

        return LLMProviderConfig(
            provider=settings.LLM_FALLBACK_PROVIDER,
            model=settings.LLM_FALLBACK_MODEL,
            base_url=settings.LLM_FALLBACK_BASE_URL,
            api_key=settings.LLM_FALLBACK_API_KEY,
            timeout=settings.LLM_FALLBACK_TIMEOUT,
        )
            
    @staticmethod
    def validate(config: LLMProviderConfig, is_fallback=False):
        if not config.model:
            if is_fallback:
                raise LLMProviderConfigurationError(
                    "LLM_FALLBACK_MODEL is not configured."
                )
            raise LLMProviderConfigurationError(
                "LLM_MODEL is not configured."
            )

        if not config.base_url:
            if is_fallback:
                raise LLMProviderConfigurationError(
                    "LLM_FALLBACK_BASE_URL is not configured."
                )
            raise LLMProviderConfigurationError(
                "LLM_BASE_URL is not configured."
            )

        if not config.api_key and "api.openai.com" in config.base_url:
            if is_fallback:
                raise LLMProviderConfigurationError(
                    "LLM_FALLBACK_API_KEY is not configured."
                )
            raise LLMProviderConfigurationError(
                "LLM_API_KEY is not configured."
            )