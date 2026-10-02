from decimal import Decimal

from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from llmops.models import LLMRequest


def make_request(
    status_=LLMRequest.STATUS_SUCCESS,
    latency_ms=None,
    total_cost=None,
    error_type=None,
    error_code=None,
):
    from django.utils import timezone

    return LLMRequest.objects.create(
        feature="employee_summary",
        provider="groq",
        model="openai/gpt-oss-120b",
        started_at=timezone.now(),
        status=status_,
        latency_ms=latency_ms,
        total_cost=total_cost,
        error_type=error_type,
        error_code=error_code,
    )


class LLMHealthApiTests(APITestCase):
    def setUp(self):
        LLMRequest.objects.all().delete()

    def url(self):
        return "/api/llmops/health/"

    def test_healthy_when_no_requests(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")
        self.assertEqual(response.data["llm"]["total_requests"], 0)
        self.assertEqual(float(response.data["cost"]["current_month"]), 0.0)
        self.assertEqual(response.data["cost"]["usage_percentage"], 0.0)

    def test_healthy_when_all_successful(self):
        make_request()
        make_request()

        response = self.client.get(self.url())

        self.assertEqual(response.data["status"], "healthy")
        self.assertEqual(response.data["llm"]["successful_requests"], 2)
        self.assertEqual(response.data["llm"]["failed_requests"], 0)
        self.assertEqual(response.data["llm"]["error_rate"], 0)

    @override_settings(LLM_MONTHLY_COST_BUDGET=1.00)
    def test_healthy_below_10_percent_error_rate(self):
        for _ in range(10):
            make_request()
        make_request(
            status_=LLMRequest.STATUS_FAILED,
            error_type="timeout",
        )

        response = self.client.get(self.url())

        self.assertEqual(response.data["status"], "healthy")
        self.assertAlmostEqual(response.data["llm"]["error_rate"], 9.09, places=2)

    @override_settings(LLM_MONTHLY_COST_BUDGET=1.00)
    def test_degraded_at_80_percent_budget_usage(self):
        make_request(total_cost=Decimal("0.80"))

        response = self.client.get(self.url())

        self.assertEqual(response.data["status"], "degraded")
        self.assertEqual(response.data["cost"]["usage_percentage"], 80.0)

    @override_settings(LLM_MONTHLY_COST_BUDGET=1.00)
    def test_unhealthy_when_budget_exceeded(self):
        make_request(total_cost=Decimal("1.00"))

        response = self.client.get(self.url())

        self.assertEqual(response.data["status"], "unhealthy")

    @override_settings(LLM_MONTHLY_COST_BUDGET=1.00)
    def test_degraded_when_error_rate_between_10_and_50(self):
        for _ in range(9):
            make_request()
        make_request(
            status_=LLMRequest.STATUS_FAILED,
            error_type="http_error",
            error_code="500",
        )

        response = self.client.get(self.url())

        self.assertEqual(response.data["status"], "degraded")
        self.assertAlmostEqual(response.data["llm"]["error_rate"], 10.0, places=4)

    @override_settings(LLM_MONTHLY_COST_BUDGET=1.00)
    def test_unhealthy_when_error_rate_above_50(self):
        for _ in range(5):
            make_request()
        for _ in range(5):
            make_request(
                status_=LLMRequest.STATUS_FAILED,
                error_type="timeout",
            )

        response = self.client.get(self.url())

        self.assertEqual(response.data["status"], "unhealthy")
        self.assertAlmostEqual(response.data["llm"]["error_rate"], 50.0, places=4)

    def test_reporting_provider_usage(self):
        make_request()
        make_request(status_=LLMRequest.STATUS_FAILED, error_type="timeout")

        response = self.client.get(self.url())

        provider = response.data["providers"][0]
        self.assertEqual(provider["provider"], "groq")
        self.assertEqual(provider["requests"], 2)
        self.assertEqual(provider["failed_requests"], 1)

    def test_recent_errors_lists_latest_failures(self):
        make_request(status_=LLMRequest.STATUS_FAILED, error_type="timeout")
        make_request(status_=LLMRequest.STATUS_FAILED, error_type="http_error")

        response = self.client.get(self.url())

        self.assertEqual(len(response.data["recent_errors"]), 2)
        error_types = {
            entry["error_type"]
            for entry in response.data["recent_errors"]
        }
        self.assertIn("timeout", error_types)
        self.assertIn("http_error", error_types)

    def test_lists_no_recent_errors_when_all_successful(self):
        make_request()

        response = self.client.get(self.url())

        self.assertEqual(response.data["recent_errors"], [])

    def test_average_latency_ignores_nulls(self):
        make_request(latency_ms=100)
        make_request(latency_ms=None)

        response = self.client.get(self.url())

        self.assertEqual(response.data["llm"]["average_latency_ms"], 100)