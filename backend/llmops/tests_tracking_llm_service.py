import io
import json
import urllib.error
import uuid
from unittest import mock
from decimal import Decimal

from django.test import TestCase, override_settings
from django.core.cache import cache

from llmops.models import LLMRequest
from llmops.services import LLMTrackingService
from reports.services.llm_service import (
    LLMConfigurationError,
    LLMResponseError,
    LLMService,
)

from llmops._support import MockLLMResponse, make_openai_body, make_http_error


class MockMLflow:
    """Patches ``mlflow`` inside ``llmops.mlflow_service``."""

    def __enter__(self):
        self._patcher = mock.patch(
            "llmops.mlflow_service.mlflow",
            new=mock.MagicMock(),
        )
        self._mock = self._patcher.start()
        return self._mock

    def __exit__(self, *exc_info):
        self._patcher.stop()
        return False


def make_request_body(content="Generated summary.", **usage):
    body = make_openai_body(content)
    body["usage"] = {
        "prompt_tokens": usage.get("prompt_tokens", 100),
        "completion_tokens": usage.get("completion_tokens", 200),
        "total_tokens": usage.get("total_tokens", 300),
    }
    return body


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "llmops-tracking-tests",
        }
    }
)
@override_settings(
    LLM_API_KEY="test-key",
    LLM_MODEL="openai/gpt-oss-120b",
    LLM_BASE_URL="https://llm.example.com/v1",
    LLM_FALLBACK_MODEL="",
    LLM_MAX_RETRIES=2,
    LLM_RETRY_DELAY_SECONDS=0,
)
class LLMTrackingServiceTests(TestCase):
    def setUp(self):
        super().setUp()
        LLMRequest.objects.all().delete()
        cache.clear()

    def test_start_request_creates_pending_record(self):
        trace_id = uuid.uuid4()

        with MockMLflow() as mock_mlflow:
            record, start_time = LLMTrackingService.start_request(
                feature="employee_summary",
                provider="groq",
                model="openai/gpt-oss-120b",
                prompt_version="v1",
                trace_id=trace_id,
                operation="operation-x",
            )

        self.assertEqual(record.feature, "employee_summary")
        self.assertEqual(record.provider, "groq")
        self.assertEqual(record.model, "openai/gpt-oss-120b")
        self.assertEqual(record.prompt_version, "v1")
        self.assertEqual(record.trace_id, trace_id)
        self.assertEqual(record.operation, "operation-x")
        self.assertEqual(record.status, LLMRequest.STATUS_PENDING)
        self.assertIsInstance(start_time, float)

        mock_mlflow.start_run.assert_called_once()
        mock_mlflow.log_params.assert_called_once()
        mock_mlflow.set_tags.assert_called_once()

    def test_mark_success_updates_record(self):
        with MockMLflow():
            record, start_time = LLMTrackingService.start_request(
                feature="employee_summary",
                provider="groq",
                model="openai/gpt-oss-120b",
            )

            LLMTrackingService.mark_success(
                record,
                start_time,
                input_tokens=1000,
                output_tokens=2000,
                total_tokens=3000,
            )

        record.refresh_from_db()
        self.assertEqual(record.status, LLMRequest.STATUS_SUCCESS)
        self.assertEqual(record.input_tokens, 1000)
        self.assertEqual(record.output_tokens, 2000)
        self.assertEqual(record.total_tokens, 3000)
        self.assertIsNotNone(record.completed_at)
        self.assertEqual(record.input_cost, Decimal("0.00015000"))
        self.assertEqual(record.output_cost, Decimal("0.00120000"))
        self.assertEqual(record.total_cost, Decimal("0.00135000"))

    def test_mark_failed_updates_record(self):
        with MockMLflow():
            record, start_time = LLMTrackingService.start_request(
                feature="employee_summary",
                provider="groq",
                model="openai/gpt-oss-120b",
            )

            LLMTrackingService.mark_failed(
                record,
                start_time,
                error_type="http_error",
                error_code="500",
            )

        record.refresh_from_db()
        self.assertEqual(record.status, LLMRequest.STATUS_FAILED)
        self.assertEqual(record.error_type, "http_error")
        self.assertEqual(record.error_code, "500")
        self.assertIsNotNone(record.completed_at)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "llmops-service-tests",
        }
    }
)
@override_settings(
    LLM_API_KEY="test-key",
    LLM_MODEL="test-model",
    LLM_BASE_URL="https://llm.example.com/v1",
    LLM_FALLBACK_MODEL="",
    LLM_MAX_RETRIES=2,
    LLM_RETRY_DELAY_SECONDS=0,
)
class LLMServiceTests(TestCase):
    def setUp(self):
        super().setUp()
        LLMRequest.objects.all().delete()
        cache.clear()

    def generate(self, **overrides):
        service = LLMService(**overrides)
        return service.generate(
            "Please summarize.",
            feature="employee_summary",
            prompt_version="v1",
            operation="employee_summary_generation",
        )

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_generate_returns_content(self, mock_mlflow, mock_urlopen):
        mock_urlopen.return_value = MockLLMResponse(
            make_request_body("Monthly summary here.")
        )

        result = self.generate()

        self.assertEqual(result, "Monthly summary here.")

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("llmops.mlflow_service.mlflow")
    @override_settings(LLM_MODEL="openai/gpt-oss-120b")
    def test_generate_tracks_successful_request(self, mock_mlflow, mock_urlopen):
        mock_urlopen.return_value = MockLLMResponse(
            make_request_body(
                "x",
                prompt_tokens=1000,
                completion_tokens=2000,
                total_tokens=3000,
            )
        )

        self.generate()

        record = LLMRequest.objects.get()
        self.assertEqual(record.status, LLMRequest.STATUS_SUCCESS)
        self.assertEqual(record.feature, "employee_summary")
        self.assertEqual(record.prompt_version, "v1")
        self.assertEqual(record.operation, "employee_summary_generation")
        self.assertEqual(record.input_tokens, 1000)
        self.assertEqual(record.output_tokens, 2000)
        self.assertEqual(record.total_tokens, 3000)
        self.assertEqual(record.total_cost, Decimal("0.00135000"))

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_generate_tracks_failed_request_on_empty_content(
        self, mock_mlflow, mock_urlopen
    ):
        mock_urlopen.return_value = MockLLMResponse({})

        with self.assertRaises(LLMResponseError):
            self.generate()

        record = LLMRequest.objects.get()
        self.assertEqual(record.status, LLMRequest.STATUS_FAILED)
        self.assertEqual(record.error_type, "invalid_response")
        self.assertEqual(record.error_code, "INVALID_RESPONSE_STRUCTURE")

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_generate_posts_to_openai_compatible_endpoint(
        self, mock_mlflow, mock_urlopen
    ):
        mock_urlopen.return_value = MockLLMResponse(make_request_body("x"))

        self.generate()

        request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://llm.example.com/v1/chat/completions",
        )
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["messages"][-1]["content"], "Please summarize.")

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_non_retryable_http_error_is_not_retried(self, mock_mlflow, mock_urlopen):
        mock_urlopen.side_effect = [
            make_http_error(400, "Bad Request"),
        ]

        with self.assertRaises(LLMResponseError):
            self.generate()

        self.assertEqual(mock_urlopen.call_count, 1)
        record = LLMRequest.objects.get()
        self.assertEqual(record.status, LLMRequest.STATUS_FAILED)
        self.assertEqual(record.error_type, "http_error")
        self.assertEqual(record.error_code, "400")

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("reports.services.llm_service.time.sleep")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_429_retries_then_succeeds(self, mock_mlflow, mock_sleep, mock_urlopen):
        mock_urlopen.side_effect = [
            make_http_error(429, "Rate Limited"),
            MockLLMResponse(make_request_body("Second try success.")),
        ]

        result = self.generate()

        self.assertEqual(result, "Second try success.")
        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once()

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("reports.services.llm_service.time.sleep")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_5xx_retries_then_succeeds(self, mock_mlflow, mock_sleep, mock_urlopen):
        mock_urlopen.side_effect = [
            make_http_error(500, "Server Error"),
            MockLLMResponse(make_request_body("Recovered.")),
        ]

        result = self.generate()

        self.assertEqual(result, "Recovered.")
        self.assertEqual(mock_urlopen.call_count, 2)

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("reports.services.llm_service.time.sleep")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_retries_are_exhausted_after_max_retries(self, mock_mlflow, mock_sleep, mock_urlopen):
        mock_urlopen.side_effect = [
            make_http_error(500, "Server Error"),
            make_http_error(500, "Server Error"),
            make_http_error(500, "Server Error"),
        ]

        with self.assertRaises(LLMResponseError):
            self.generate()

        self.assertEqual(mock_urlopen.call_count, 3)
        record = LLMRequest.objects.get()
        self.assertEqual(record.status, LLMRequest.STATUS_FAILED)
        self.assertEqual(record.error_code, "500")

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("reports.services.llm_service.time.sleep")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_connection_error_retries_then_succeeds(self, mock_mlflow, mock_sleep, mock_urlopen):
        mock_urlopen.side_effect = [
            urllib.error.URLError("Connection refused"),
            MockLLMResponse(make_request_body("Connected.")),
        ]

        result = self.generate()

        self.assertEqual(result, "Connected.")
        self.assertEqual(mock_urlopen.call_count, 2)

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("reports.services.llm_service.time.sleep")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_timeout_retries_then_succeeds(self, mock_mlflow, mock_sleep, mock_urlopen):
        mock_urlopen.side_effect = [
            TimeoutError("timed out"),
            MockLLMResponse(make_request_body("Timed out once.")),
        ]

        result = self.generate()

        self.assertEqual(result, "Timed out once.")
        self.assertEqual(mock_urlopen.call_count, 2)

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_connection_error_after_max_retries_fails(self, mock_mlflow, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with self.assertRaises(LLMResponseError):
            self.generate()

        record = LLMRequest.objects.get()
        self.assertEqual(record.status, LLMRequest.STATUS_FAILED)
        self.assertEqual(record.error_type, "connection_error")
        self.assertEqual(record.error_code, "CONNECTION_FAILED")

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("llmops.mlflow_service.mlflow")
    @override_settings(LLM_MODEL="")
    def test_missing_model_raises_configuration_error(self, mock_mlflow, mock_urlopen):
        with self.assertRaises(LLMConfigurationError):
            LLMService().generate(
                "Please summarize.",
                feature="employee_summary",
                prompt_version="v1",
            )

        record = LLMRequest.objects.get()
        self.assertEqual(record.status, LLMRequest.STATUS_FAILED)
        self.assertEqual(record.error_type, "configuration_error")
        self.assertEqual(record.error_code, "INVALID_CONFIGURATION")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "llmops-fallback-tests",
        }
    }
)
@override_settings(
    LLM_API_KEY="test-key",
    LLM_MODEL="primary-model",
    LLM_BASE_URL="https://llm.example.com/v1",
    LLM_FALLBACK_PROVIDER="openrouter",
    LLM_FALLBACK_MODEL="openrouter/free",
    LLM_FALLBACK_BASE_URL="https://openrouter.example.com/api/v1",
    LLM_FALLBACK_API_KEY="fallback-key",
    LLM_MAX_RETRIES=0,
    LLM_RETRY_DELAY_SECONDS=0,
)
class LLMServiceFallbackTests(TestCase):
    def setUp(self):
        super().setUp()
        LLMRequest.objects.all().delete()
        cache.clear()

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_fallback_is_used_when_primary_fails(self, mock_mlflow, mock_urlopen):
        mock_urlopen.side_effect = [
            make_http_error(500, "Server Error"),
            MockLLMResponse(make_request_body("Fallback success.")),
        ]

        result = LLMService().generate(
            "Please summarize.",
            feature="employee_summary",
            prompt_version="v1",
        )

        self.assertEqual(result, "Fallback success.")
        self.assertEqual(mock_urlopen.call_count, 2)

        record = LLMRequest.objects.get()
        self.assertEqual(record.status, LLMRequest.STATUS_SUCCESS)
        self.assertEqual(record.provider, "fallback")
        self.assertEqual(record.model, "openrouter/free")

    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_failure_is_recorded_when_both_primary_and_fallback_fail(
        self, mock_mlflow, mock_urlopen
    ):
        mock_urlopen.side_effect = [
            make_http_error(500, "Server Error"),
            make_http_error(503, "Unavailable"),
        ]

        with self.assertRaises(LLMResponseError):
            LLMService().generate(
                "Please summarize.",
                feature="employee_summary",
                prompt_version="v1",
            )

        record = LLMRequest.objects.get()
        self.assertEqual(record.status, LLMRequest.STATUS_FAILED)
        self.assertEqual(record.error_type, "http_error")
        self.assertEqual(record.error_code, "503")

    @override_settings(LLM_FALLBACK_BASE_URL="")
    @mock.patch("reports.services.llm_service.urllib.request.urlopen")
    @mock.patch("llmops.mlflow_service.mlflow")
    def test_invalid_fallback_config_marks_record_and_raises(
        self, mock_mlflow, mock_urlopen
    ):
        mock_urlopen.side_effect = [make_http_error(500, "Server Error")]

        with self.assertRaises(LLMConfigurationError):
            LLMService().generate(
                "Please summarize.",
                feature="employee_summary",
                prompt_version="v1",
            )

        record = LLMRequest.objects.get()
        self.assertEqual(record.status, LLMRequest.STATUS_FAILED)
        self.assertEqual(record.error_code, "INVALID_FALLBACK_CONFIGURATION")