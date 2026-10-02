import uuid
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from llmops.evaluation_models import LLMEvaluation
from llmops.models import LLMRequest


def make_request(
    feature="employee_summary",
    provider="groq",
    model="openai/gpt-oss-120b",
    status_=LLMRequest.STATUS_SUCCESS,
    latency_ms=None,
    input_tokens=None,
    output_tokens=None,
    total_tokens=None,
    input_cost=None,
    output_cost=None,
    total_cost=None,
    error_type=None,
    error_code=None,
    prompt_version=None,
    operation=None,
    started_at=None,
):
    return LLMRequest.objects.create(
        feature=feature,
        provider=provider,
        model=model,
        started_at=started_at or timezone.now(),
        status=status_,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost,
        error_type=error_type,
        error_code=error_code,
        prompt_version=prompt_version,
        operation=operation,
    )


class LLMRequestListApiTests(APITestCase):
    def url(self, **query):
        base = reverse("llm-request-list")
        if query:
            return base + "?" + "&".join(
                f"{key}={value}" for key, value in query.items()
            )
        return base

    def test_lists_latest_requests_first(self):
        first = make_request(feature="employee_summary")
        second = make_request(feature="monthly_team_report")
        # Deterministic ordering: force distinct created_at values.
        LLMRequest.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timezone.timedelta(minutes=5)
        )

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        features = [
            item["feature"] for item in response.data
        ]
        self.assertEqual(
            features,
            ["monthly_team_report", "employee_summary"],
        )

    def test_filters_by_feature(self):
        make_request()
        make_request(feature="monthly_team_report")

        response = self.client.get(self.url(feature="monthly_team_report"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["feature"], "monthly_team_report"
        )

    def test_filters_by_status(self):
        make_request()
        make_request(status_=LLMRequest.STATUS_FAILED, error_type="timeout")

        response = self.client.get(self.url(status="FAILED"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], "FAILED")

    def test_filters_by_prompt_version(self):
        make_request(prompt_version="v1")
        make_request(prompt_version="v2")

        response = self.client.get(self.url(prompt_version="v2"))

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["prompt_version"], "v2")


class LLMMetricsApiTests(APITestCase):
    def setUp(self):
        LLMRequest.objects.all().delete()
        LLMEvaluation.objects.all().delete()

    def url(self):
        return reverse("llm-metrics")

    def test_returns_zeros_when_empty(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_requests"], 0)
        self.assertEqual(response.data["successful_requests"], 0)
        self.assertEqual(response.data["failed_requests"], 0)
        self.assertIsNone(response.data["average_latency_ms"])
        self.assertEqual(response.data["total_cost"], 0)

    def test_aggregates_request_counts_and_costs(self):
        make_request(
            latency_ms=100,
            input_tokens=1000,
            output_tokens=2000,
            total_tokens=3000,
            input_cost=Decimal("0.00015000"),
            output_cost=Decimal("0.00120000"),
            total_cost=Decimal("0.00135000"),
        )
        make_request(
            latency_ms=300,
            input_tokens=500,
            output_tokens=1000,
            total_tokens=1500,
            input_cost=Decimal("0.00007500"),
            output_cost=Decimal("0.00060000"),
            total_cost=Decimal("0.00067500"),
        )
        make_request(
            status_=LLMRequest.STATUS_FAILED,
            error_type="timeout",
            error_code="REQUEST_TIMEOUT",
        )

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_requests"], 3)
        self.assertEqual(response.data["successful_requests"], 2)
        self.assertEqual(response.data["failed_requests"], 1)
        self.assertEqual(response.data["average_latency_ms"], 200)
        self.assertEqual(response.data["total_input_tokens"], 1500)
        self.assertEqual(response.data["total_output_tokens"], 3000)
        self.assertEqual(response.data["total_tokens"], 4500)
        self.assertAlmostEqual(
            float(response.data["total_cost"]),
            0.002025,
            places=6,
        )
        self.assertEqual(
            response.data["error_breakdown"],
            [{"error_type": "timeout", "count": 1}],
        )

    def test_per_second_totals_exclude_nulls(self):
        make_request()
        make_request(
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
            input_cost=Decimal("0.01"),
            output_cost=Decimal("0.02"),
            total_cost=Decimal("0.03"),
        )

        response = self.client.get(self.url())

        self.assertEqual(response.data["total_input_tokens"], 100)

    def test_feature_usage_aggregation(self):
        make_request()
        make_request()
        make_request(feature="monthly_team_report")

        response = self.client.get(self.url())

        by_feature = {
            item["feature"]: item for item in response.data["feature_usage"]
        }
        self.assertEqual(by_feature["employee_summary"]["requests"], 2)
        self.assertEqual(by_feature["monthly_team_report"]["requests"], 1)

    def test_quality_metrics_average_judge_scores(self):
        request_id = uuid.uuid4()
        for metric, score in [
            ("relevance", 4.0),
            ("faithfulness", 5.0),
            ("completeness", 3.0),
            ("clarity", 4.0),
            ("quality_score", 4.0),
        ]:
            LLMEvaluation.objects.create(
                request_id=request_id,
                feature="employee_summary",
                evaluation_type=LLMEvaluation.EVALUATION_LLM_JUDGE,
                metric=metric,
                score=score,
            )
        make_request()

        response = self.client.get(self.url())

        metrics = response.data["quality_metrics"]
        self.assertAlmostEqual(metrics["relevance"], 4.0, places=4)
        self.assertAlmostEqual(metrics["quality_score"], 4.0, places=4)
        self.assertNotIn("rouge1", metrics)

    def test_reference_metrics_average_reference_scores(self):
        request_id = uuid.uuid4()
        for metric, score in [
            ("rouge1", 0.5),
            ("rouge2", 0.4),
            ("rougeL", 0.45),
            ("semantic_similarity", 0.8),
        ]:
            LLMEvaluation.objects.create(
                request_id=request_id,
                feature="employee_summary",
                evaluation_type=LLMEvaluation.EVALUATION_REFERENCE,
                metric=metric,
                score=score,
            )
        make_request()

        response = self.client.get(self.url())

        metrics = response.data["reference_metrics"]
        self.assertAlmostEqual(metrics["rouge1"], 0.5, places=4)
        self.assertAlmostEqual(metrics["semantic_similarity"], 0.8, places=4)

    def test_prompt_comparison_groups_by_version(self):
        v1_request = make_request(
            prompt_version="v1",
            operation="prompt_comparison_v1",
        )
        v2_request = make_request(
            prompt_version="v2",
            operation="prompt_comparison_v2",
        )

        for request_record, v_scores in [
            (
                v1_request,
                {
                    "rouge1": 0.50,
                    "rouge2": 0.40,
                    "rougeL": 0.45,
                    "semantic_similarity": 0.80,
                },
            ),
            (
                v2_request,
                {
                    "rouge1": 0.60,
                    "rouge2": 0.50,
                    "rougeL": 0.55,
                    "semantic_similarity": 0.90,
                },
            ),
        ]:
            for metric, score in v_scores.items():
                LLMEvaluation.objects.create(
                    request_id=request_record.request_id,
                    feature="employee_summary",
                    evaluation_type=LLMEvaluation.EVALUATION_REFERENCE,
                    metric=metric,
                    score=score,
                )

        response = self.client.get(self.url())

        comparison = response.data["prompt_comparison"]
        self.assertIn("v1", comparison)
        self.assertIn("v2", comparison)
        self.assertAlmostEqual(
            comparison["v1"]["semantic_similarity"], 0.80, places=4
        )
        self.assertAlmostEqual(
            comparison["v2"]["rouge1"], 0.60, places=4
        )

    def test_prompt_comparison_empty_when_no_comparison_requests(self):
        make_request()

        response = self.client.get(self.url())

        self.assertEqual(response.data["prompt_comparison"], {})