from rest_framework.generics import ListAPIView
from rest_framework.generics import ListCreateAPIView
from llmops.cost_budget import LLMCostBudgetService

from llmops.models import LLMRequest
from llmops.serializers import LLMRequestSerializer
from llmops.prompt_models import PromptVersion
from llmops.serializers import PromptVersionSerializer
from llmops.prompt_service import PromptVersionService
from llmops.evaluation_models import LLMEvaluation

from django.db.models import Avg, Sum, Count
from django.db.models.functions import TruncDate
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import models
from rest_framework.generics import get_object_or_404


class LLMRequestListView(ListAPIView):
    serializer_class = LLMRequestSerializer

    def get_queryset(self):
        queryset = LLMRequest.objects.all().order_by("-created_at")

        feature = self.request.query_params.get("feature")
        status = self.request.query_params.get("status")
        prompt_version = self.request.query_params.get("prompt_version")
        trace_id = self.request.query_params.get("trace_id")
        operation = self.request.query_params.get("operation")

        if feature:
            queryset = queryset.filter(feature=feature)

        if status:
            queryset = queryset.filter(status=status)

        if prompt_version:
            queryset = queryset.filter(prompt_version=prompt_version)

        if trace_id:
            queryset = queryset.filter(trace_id=trace_id)

        if operation:
            queryset = queryset.filter(operation=operation)

        return queryset
    
class LLMMetricsView(APIView):

    def get(self, request):
        queryset = LLMRequest.objects.all()

        total_requests = queryset.count()

        successful_requests = queryset.filter(
            status=LLMRequest.STATUS_SUCCESS
        ).count()

        failed_requests = queryset.filter(
            status=LLMRequest.STATUS_FAILED
        ).count()

        average_latency = queryset.filter(
            latency_ms__isnull=False
        ).aggregate(
            average=Avg("latency_ms")
        )["average"]

        total_input_tokens = queryset.aggregate(
            total=Sum("input_tokens")
        )["total"] or 0

        total_output_tokens = queryset.aggregate(
            total=Sum("output_tokens")
        )["total"] or 0

        total_tokens = queryset.aggregate(
            total=Sum("total_tokens")
        )["total"] or 0

        total_input_cost = queryset.aggregate(
            total=Sum("input_cost")
        )["total"] or 0

        total_output_cost = queryset.aggregate(
            total=Sum("output_cost")
        )["total"] or 0

        total_cost = queryset.aggregate(
            total=Sum("total_cost")
        )["total"] or 0

        error_breakdown = list(
            queryset
            .filter(
                status=LLMRequest.STATUS_FAILED,
                error_type__isnull=False,
            )
            .values("error_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        daily_usage = list(
            queryset
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(
                requests=Count("id"),
                total_tokens=Sum("total_tokens"),
                total_cost=Sum("total_cost"),
            )
            .order_by("date")
        )

        feature_usage = list(
            queryset
            .values("feature")
            .annotate(
                requests=Count("id"),
                successful_requests=Count(
                    "id",
                    filter=models.Q(
                        status=LLMRequest.STATUS_SUCCESS
                    ),
                ),
                failed_requests=Count(
                    "id",
                    filter=models.Q(
                        status=LLMRequest.STATUS_FAILED
                    ),
                ),
                total_tokens=Sum("total_tokens"),
                total_cost=Sum("total_cost"),
                average_latency_ms=Avg("latency_ms"),
            )
            .order_by("-requests")
        )

        quality_metrics = {}

        quality_queryset = LLMEvaluation.objects.filter(
            evaluation_type=LLMEvaluation.EVALUATION_LLM_JUDGE
        )

        for metric in [
            "relevance",
            "faithfulness",
            "completeness",
            "clarity",
            "quality_score",
        ]:
            average_score = quality_queryset.filter(
                metric=metric
            ).aggregate(
                average=Avg("score")
            )["average"]

            if average_score is not None:
                quality_metrics[metric] = average_score

        reference_metrics = {}

        reference_queryset = LLMEvaluation.objects.filter(
            evaluation_type=LLMEvaluation.EVALUATION_REFERENCE
        )

        for metric in [
            "rouge1",
            "rouge2",
            "rougeL",
            "semantic_similarity",
        ]:
            average_score = reference_queryset.filter(
                metric=metric
            ).aggregate(
                average=Avg("score")
            )["average"]

            if average_score is not None:
                reference_metrics[metric] = average_score

        prompt_comparison = {}

        comparison_requests = (
            LLMRequest.objects
            .filter(
                operation__startswith="prompt_comparison_",
            )
            .order_by("-created_at")
        )

        for version in ["v1", "v2"]:
            request_record = (
                comparison_requests
                .filter(prompt_version=version)
                .filter(
                    request_id__in=LLMEvaluation.objects.filter(
                        evaluation_type=LLMEvaluation.EVALUATION_REFERENCE,
                        metric__in=[
                            "rouge1",
                            "rouge2",
                            "rougeL",
                            "semantic_similarity",
                        ],
                    ).values("request_id")
                )
                .first()
            )

            if request_record is None:
                continue

            evaluations = LLMEvaluation.objects.filter(
                request_id=request_record.request_id,
                evaluation_type=LLMEvaluation.EVALUATION_REFERENCE,
                metric__in=[
                    "rouge1",
                    "rouge2",
                    "rougeL",
                    "semantic_similarity",
                ],
            )

            prompt_comparison[version] = {
                evaluation.metric: evaluation.score
                for evaluation in evaluations
            }

        return Response({
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "average_latency_ms": average_latency,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "total_input_cost": total_input_cost,
            "total_output_cost": total_output_cost,
            "total_cost": total_cost,
            "error_breakdown": error_breakdown,
            "daily_usage": daily_usage,
            "feature_usage": feature_usage,
            "quality_metrics": quality_metrics,
            "reference_metrics": reference_metrics,
            "prompt_comparison": prompt_comparison,
        })
    
class PromptVersionListCreateView(ListCreateAPIView):
    serializer_class = PromptVersionSerializer

    def get_queryset(self):
        return PromptVersion.objects.all().order_by(
            "feature",
            "-created_at",
        )
    
class PromptVersionActivateView(APIView):

    def post(self, request, pk):
        prompt_version = get_object_or_404(
            PromptVersion,
            pk=pk,
        )

        PromptVersionService.activate_prompt(
            prompt_version
        )

        serializer = PromptVersionSerializer(
            prompt_version
        )

        return Response(
            serializer.data
        )
    
class LLMHealthView(APIView):

    def get(self, request):
        queryset = LLMRequest.objects.all()

        total_requests = queryset.count()

        successful_requests = queryset.filter(
            status=LLMRequest.STATUS_SUCCESS
        ).count()

        failed_requests = queryset.filter(
            status=LLMRequest.STATUS_FAILED
        ).count()

        average_latency = queryset.filter(
            latency_ms__isnull=False
        ).aggregate(
            average=Avg("latency_ms")
        )["average"]

        if total_requests:
            error_rate = (
                failed_requests / total_requests
            ) * 100
        else:
            error_rate = 0

        provider_usage = list(
            queryset
            .values("provider", "model")
            .annotate(
                requests=Count("id"),
                failed_requests=Count(
                    "id",
                    filter=models.Q(
                        status=LLMRequest.STATUS_FAILED
                    ),
                ),
            )
            .order_by("-requests")
        )

        current_cost = LLMCostBudgetService.get_current_month_cost()
        budget = LLMCostBudgetService.get_budget()

        if budget > 0:
            budget_usage_percentage = (
                current_cost / budget
            ) * 100
        else:
            budget_usage_percentage = 0
    
        recent_errors = list(
            queryset
            .filter(
                status=LLMRequest.STATUS_FAILED,
                error_type__isnull=False,
            )
            .values(
                "request_id",
                "feature",
                "provider",
                "model",
                "error_type",
                "error_code",
                "created_at",
            )
            .order_by("-created_at")[:10]
        )

        return Response({
            "status": self._get_health_status(
                total_requests=total_requests,
                failed_requests=failed_requests,
                budget_usage_percentage=float(
                    budget_usage_percentage
                ),
            ),
            "llm": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "error_rate": round(error_rate, 2),
                "average_latency_ms": average_latency,
            },
            "providers": provider_usage,
            "cost": {
                "current_month": current_cost,
                "budget": budget,
                "usage_percentage": round(
                    float(budget_usage_percentage),
                    2,
                ),
            },
            "recent_errors": recent_errors,
        })

    @staticmethod
    def _get_health_status(
        total_requests,
        failed_requests,
        budget_usage_percentage,
    ):
        if budget_usage_percentage >= 100:
            return "unhealthy"

        if budget_usage_percentage >= 80:
            return "degraded"

        if total_requests == 0:
            return "healthy"

        error_rate = (
            failed_requests / total_requests
        ) * 100

        if error_rate >= 50:
            return "unhealthy"

        if error_rate >= 10:
            return "degraded"

        return "healthy"