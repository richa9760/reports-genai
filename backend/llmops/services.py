import time
from datetime import datetime, timezone

from llmops.models import LLMRequest
from llmops.pricing import calculate_cost
from llmops.mlflow_service import MLflowTrackingService

LLM_ERROR_HTTP = "http_error"
LLM_ERROR_CONNECTION = "connection_error"
LLM_ERROR_TIMEOUT = "timeout"
LLM_ERROR_EMPTY_RESPONSE = "empty_response"
LLM_ERROR_INVALID_RESPONSE = "invalid_response"
LLM_ERROR_CONFIGURATION = "configuration_error"
LLM_ERROR_UNKNOWN = "unknown_error"


class LLMTrackingService:

    @staticmethod
    def start_request(feature, provider, model, prompt_version=None, trace_id=None, operation=None,):
        """
        Create an LLM request tracking record and return
        the record along with a monotonic start time.
        """

        tracking_record = LLMRequest.objects.create(
            feature=feature,
            provider=provider,
            model=model,
            started_at=datetime.now(timezone.utc),
            status=LLMRequest.STATUS_PENDING,
            prompt_version=prompt_version,
            trace_id=trace_id,
            operation=operation,
        )

        mlflow_run = MLflowTrackingService.start_run()

        MLflowTrackingService.log_parameters(
            feature=feature,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            operation=operation,
        )

        MLflowTrackingService.log_tags(
            request_id=tracking_record.request_id,
            trace_id=trace_id,
            status=LLMRequest.STATUS_PENDING,
        )

        start_time = time.monotonic()

        return tracking_record, start_time

    @staticmethod
    def mark_success(
        tracking_record,
        start_time,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
    ):
        """
        Mark an LLM request as successfully completed.
        """

        elapsed = time.monotonic() - start_time

        tracking_record.completed_at = datetime.now(timezone.utc)
        tracking_record.latency_ms = round(elapsed * 1000)

        tracking_record.status = LLMRequest.STATUS_SUCCESS

        tracking_record.input_tokens = input_tokens
        tracking_record.output_tokens = output_tokens
        tracking_record.total_tokens = total_tokens

        input_cost, output_cost, total_cost = calculate_cost(tracking_record.model, input_tokens, output_tokens,)

        tracking_record.input_cost = input_cost
        tracking_record.output_cost = output_cost
        tracking_record.total_cost = total_cost

        tracking_record.save(
            update_fields=[
                "completed_at",
                "latency_ms",
                "status",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "input_cost",
                "output_cost",
                "total_cost",
            ]
        )

        MLflowTrackingService.log_metrics(
            latency_ms=tracking_record.latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            total_cost=tracking_record.total_cost,
        )

        MLflowTrackingService.log_tags(
            status=LLMRequest.STATUS_SUCCESS,
        )

        MLflowTrackingService.end_run()

    @staticmethod
    def mark_failed(
        tracking_record,
        start_time,
        error_type,
        error_code=None,
    ):
        """
        Mark an LLM request as failed.
        """

        elapsed = time.monotonic() - start_time

        tracking_record.completed_at = datetime.now(timezone.utc)
        tracking_record.latency_ms = round(elapsed * 1000)

        tracking_record.status = LLMRequest.STATUS_FAILED
        tracking_record.error_type = error_type
        tracking_record.error_code = error_code

        tracking_record.save(
            update_fields=[
                "completed_at",
                "latency_ms",
                "status",
                "error_type",
                "error_code",
            ]
        )
        