"""Isolated LLM integration.

The rest of the application talks to an OpenAI-compatible chat-completions
endpoint through :class:`LLMService`, so no other module depends on a specific
provider. Configuration comes from Django settings (``LLM_*`` environment
variables).
"""

import json
import urllib.error
import urllib.request
from llmops.services import ( LLMTrackingService, LLM_ERROR_HTTP, LLM_ERROR_CONNECTION, LLM_ERROR_CONFIGURATION,
                            LLM_ERROR_TIMEOUT, LLM_ERROR_EMPTY_RESPONSE, LLM_ERROR_INVALID_RESPONSE)
from llmops.rate_limiter import (
    LLMRateLimiter,
    LLMRateLimitExceeded,
)

from llmops.cost_budget import (
    LLMCostBudgetService,
    LLMCostBudgetExceeded,
)
from llmops.mlflow_service import MLflowTrackingService
from llmops.provider_config import (
    LLMProviderConfig,
    LLMProviderConfigService,
    LLMProviderConfigurationError,
)
from llmops.cost_alerts import LLMCostAlertService
from django.conf import settings

import uuid
import time
import logging

logger = logging.getLogger(__name__)

class LLMConfigurationError(Exception):
    """Raised when the LLM is not configured (e.g. missing API key)."""


class LLMResponseError(Exception):
    """Raised when the LLM call fails or returns nothing usable."""

class LLMRetryableError(LLMResponseError):
    """Raised when an LLM failure may be retried."""

    def __init__(self, message, error_type, error_code=None):
        super().__init__(message)
        self.error_type = error_type
        self.error_code = error_code
        
class LLMService:
    """Minimal OpenAI-compatible chat completions client."""

    def __init__(self, api_key=None, model=None, base_url=None, timeout=None):
        self.config = LLMProviderConfigService.get_primary()

        self.api_key = api_key if api_key is not None else self.config.api_key
        self.model = model if model is not None else self.config.model
        self.base_url = (
            base_url if base_url is not None else self.config.base_url
        ).rstrip("/")
        self.timeout = timeout if timeout is not None else self.config.timeout
        self.max_retries = settings.LLM_MAX_RETRIES
        self.retry_delay = settings.LLM_RETRY_DELAY_SECONDS

    def _validate_config(self):
        try:
            LLMProviderConfigService.validate(self.config)
        except LLMProviderConfigurationError as exc:
            raise LLMConfigurationError(str(exc)) from exc
        
    def _wait_before_retry(self):
        time.sleep(self.retry_delay)

    def _get_fallback_config(self):
        return LLMProviderConfigService.get_fallback()
    
    def _validate_fallback_config(self, config):
        try:
            LLMProviderConfigService.validate(
                config,
                is_fallback=True,
            )
        except LLMProviderConfigurationError as exc:
            raise LLMConfigurationError(str(exc)) from exc

        
    @staticmethod
    def _is_retryable_error(error_type, error_code=None):
        if error_type in {
            LLM_ERROR_CONNECTION,
            LLM_ERROR_TIMEOUT,
        }:
            return True

        if error_type == LLM_ERROR_HTTP:
            if error_code is None:
                return False

            try:
                status_code = int(error_code)
            except (TypeError, ValueError):
                return False

            return status_code == 429 or 500 <= status_code < 600

        return False

    def generate(self, prompt, feature="unknown", prompt_version=None, operation=None, trace_id=None,):
        """Send ``prompt`` and return the resulting text."""

        LLMRateLimiter.check_and_record()
        LLMCostBudgetService.check_budget()
       
        if trace_id is None:
            trace_id = uuid.uuid4()
            
        tracking_record, start_time = LLMTrackingService.start_request(
            feature=feature,
            provider=self.config.provider,
            model=self.model,
            prompt_version=prompt_version,
            trace_id=trace_id,
            operation=operation,
        )

        try:
            self._validate_config()
        except LLMConfigurationError as exc:
            LLMTrackingService.mark_failed(
                tracking_record,
                start_time,
                error_type=LLM_ERROR_CONFIGURATION,
                error_code="INVALID_CONFIGURATION",
            )
            raise

        primary_config = self.config

        try:
            body = self._generate_with_config(
                prompt=prompt,
                config=primary_config,
            )

        except LLMRetryableError as primary_exc:
            fallback_config = self._get_fallback_config()

            if fallback_config is None:
                LLMTrackingService.mark_failed(
                    tracking_record,
                    start_time,
                    error_type=primary_exc.error_type,
                    error_code=primary_exc.error_code,
                )
                raise

            try:
                self._validate_fallback_config(fallback_config)
            except LLMConfigurationError:
                LLMTrackingService.mark_failed(
                    tracking_record,
                    start_time,
                    error_type=LLM_ERROR_CONFIGURATION,
                    error_code="INVALID_FALLBACK_CONFIGURATION",
                )
                raise

            logger.warning(
                "Primary LLM failed. Attempting fallback model: %s",
                fallback_config.model,
            )

            try:
                body = self._generate_with_config(
                    prompt=prompt,
                    config=fallback_config,
                )

                tracking_record.model = fallback_config.model
                tracking_record.provider = "fallback"

                tracking_record.save(
                    update_fields=["model", "provider"]
                )

                MLflowTrackingService.update_model_provider(
                    provider=fallback_config.provider,
                    model=fallback_config.model,
                )

            except LLMRetryableError as fallback_exc:
                LLMTrackingService.mark_failed(
                    tracking_record,
                    start_time,
                    error_type=fallback_exc.error_type,
                    error_code=fallback_exc.error_code,
                )
                raise
                
        try:
            content = self._extract_content(body)
        except LLMResponseError:
            LLMTrackingService.mark_failed(
                tracking_record,
                start_time,
                error_type=LLM_ERROR_INVALID_RESPONSE,
                error_code="INVALID_RESPONSE_STRUCTURE",
            )
            raise

        if not content:
            LLMTrackingService.mark_failed(
                tracking_record,
                start_time,
                error_type=LLM_ERROR_EMPTY_RESPONSE,
                error_code="EMPTY_CONTENT",
            )

            raise LLMResponseError(
                "The LLM API returned an empty response."
            )

        usage = body.get("usage", {})

        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")

        LLMTrackingService.mark_success(
            tracking_record,
            start_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

        LLMCostAlertService.check_and_alert()

        return content

    @staticmethod
    def _extract_content(body):
        try:
            return (
                body["choices"][0]["message"]["content"] or ""
            ).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError(
                "The LLM API returned an invalid response structure."
            ) from exc
        
    def _generate_with_config(self, prompt, config):
        payload = {
            "model": config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You write professional monthly status summaries.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.3,
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 reports-genai",
        }

        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        request = urllib.request.Request(
            f"{config.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        attempt = 0

        while attempt <= self.max_retries:
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=config.timeout,
                ) as response:
                    return json.loads(
                        response.read().decode("utf-8")
                    )

            except urllib.error.HTTPError as exc:
                exc.read()

                error_type = LLM_ERROR_HTTP
                error_code = str(exc.code)

                if (
                    self._is_retryable_error(error_type, error_code)
                    and attempt < self.max_retries
                ):
                    attempt += 1
                    logger.warning(
                        "LLM request retrying: attempt %s of %s",
                        attempt + 1,
                        self.max_retries + 1,
                    )
                    self._wait_before_retry()
                    continue

                raise LLMRetryableError(
                    f"The LLM API returned HTTP {exc.code}.",
                    error_type=error_type,
                    error_code=error_code,
                ) from exc

            except TimeoutError as exc:
                error_type = LLM_ERROR_TIMEOUT
                error_code = "REQUEST_TIMEOUT"

                if attempt < self.max_retries:
                    attempt += 1
                    logger.warning(
                        "LLM request retrying: attempt %s of %s",
                        attempt + 1,
                        self.max_retries + 1,
                    )
                    self._wait_before_retry()
                    continue

                raise LLMRetryableError(
                    "The LLM API request timed out.",
                    error_type=error_type,
                    error_code=error_code,
                ) from exc

            except (
                urllib.error.URLError,
                ConnectionError,
            ) as exc:
                error_type = LLM_ERROR_CONNECTION
                error_code = "CONNECTION_FAILED"

                if attempt < self.max_retries:
                    attempt += 1
                    logger.warning(
                        "LLM request retrying: attempt %s of %s",
                        attempt + 1,
                        self.max_retries + 1,
                    )
                    self._wait_before_retry()
                    continue

                raise LLMRetryableError(
                    "The LLM API could not be reached.",
                    error_type=error_type,
                    error_code=error_code,
                ) from exc