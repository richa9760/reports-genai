from django.test import TestCase, override_settings

from llmops.provider_config import (
    LLMProviderConfigService,
    LLMProviderConfigurationError,
)


class GetPrimaryTests(TestCase):
    @override_settings(
        LLM_PROVIDER="groq",
        LLM_MODEL="openai/gpt-oss-120b",
        LLM_BASE_URL="https://api.groq.com/openai/v1",
        LLM_API_KEY="test-key",
        LLM_TIMEOUT=60,
    )
    def test_get_primary_reads_settings(self):
        config = LLMProviderConfigService.get_primary()

        self.assertEqual(config.provider, "groq")
        self.assertEqual(config.model, "openai/gpt-oss-120b")
        self.assertEqual(config.base_url, "https://api.groq.com/openai/v1")
        self.assertEqual(config.api_key, "test-key")
        self.assertEqual(config.timeout, 60)


class GetFallbackTests(TestCase):
    @override_settings(LLM_FALLBACK_MODEL="")
    def test_get_fallback_returns_none_when_model_empty(self):
        self.assertIsNone(LLMProviderConfigService.get_fallback())

    @override_settings(
        LLM_FALLBACK_PROVIDER="openrouter",
        LLM_FALLBACK_MODEL="openrouter/free",
        LLM_FALLBACK_BASE_URL="https://openrouter.ai/api/v1",
        LLM_FALLBACK_API_KEY="fb-key",
        LLM_FALLBACK_TIMEOUT=30,
    )
    def test_get_fallback_reads_settings(self):
        config = LLMProviderConfigService.get_fallback()

        self.assertIsNotNone(config)
        self.assertEqual(config.provider, "openrouter")
        self.assertEqual(config.model, "openrouter/free")
        self.assertEqual(config.base_url, "https://openrouter.ai/api/v1")
        self.assertEqual(config.api_key, "fb-key")
        self.assertEqual(config.timeout, 30)


class ValidateTests(TestCase):
    def make_config(self, **overrides):
        defaults = {
            "provider": "groq",
            "model": "openai/gpt-oss-120b",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": "test-key",
            "timeout": 60,
        }
        defaults.update(overrides)
        from llmops.provider_config import LLMProviderConfig

        return LLMProviderConfig(**defaults)

    def test_valid_primary_config_passes(self):
        config = self.make_config()
        self.assertIsNone(LLMProviderConfigService.validate(config))

    def test_missing_model_raises(self):
        config = self.make_config(model="")
        with self.assertRaises(LLMProviderConfigurationError) as exc:
            LLMProviderConfigService.validate(config)
        self.assertIn("LLM_MODEL is not configured.", str(exc.exception))

    def test_missing_model_raises_fallback_message(self):
        config = self.make_config(model="")
        with self.assertRaises(LLMProviderConfigurationError) as exc:
            LLMProviderConfigService.validate(config, is_fallback=True)
        self.assertIn("LLM_FALLBACK_MODEL is not configured.", str(exc.exception))

    def test_missing_base_url_raises(self):
        config = self.make_config(base_url="")
        with self.assertRaises(LLMProviderConfigurationError) as exc:
            LLMProviderConfigService.validate(config)
        self.assertIn("LLM_BASE_URL is not configured.", str(exc.exception))

    def test_missing_base_url_raises_fallback_message(self):
        config = self.make_config(base_url="")
        with self.assertRaises(LLMProviderConfigurationError) as exc:
            LLMProviderConfigService.validate(config, is_fallback=True)
        self.assertIn("LLM_FALLBACK_BASE_URL is not configured.", str(exc.exception))

    def test_openai_missing_api_key_raises(self):
        config = self.make_config(
            api_key="",
            base_url="https://api.openai.com/v1",
        )
        with self.assertRaises(LLMProviderConfigurationError) as exc:
            LLMProviderConfigService.validate(config)
        self.assertIn("LLM_API_KEY is not configured.", str(exc.exception))

    def test_openai_missing_api_key_raises_fallback_message(self):
        config = self.make_config(
            api_key="",
            base_url="https://api.openai.com/v1",
        )
        with self.assertRaises(LLMProviderConfigurationError) as exc:
            LLMProviderConfigService.validate(config, is_fallback=True)
        self.assertIn("LLM_FALLBACK_API_KEY is not configured.", str(exc.exception))

    @override_settings(LLM_BASE_URL="http://localhost:11434/v1")
    def test_custom_base_url_does_not_require_api_key(self):
        config = self.make_config(
            api_key="",
            base_url="http://localhost:11434/v1",
        )
        self.assertIsNone(LLMProviderConfigService.validate(config))