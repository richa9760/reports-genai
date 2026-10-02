from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Employee, MonthlyReport, Project, ReportItem
from .serializers import (
    EmployeeSerializer,
    GenerateSummarySerializer,
    MonthlyParamsSerializer,
    MonthlyReportDetailSerializer,
    MonthlyReportSerializer,
    ProjectSerializer,
    QuarterlyParamsSerializer,
    ReportItemSerializer,
)
from .services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from .services.manager_report_prompt import build_monthly_team_report_prompt
from .services.prompt_builder import build_employee_summary_prompt
from .services.quarterly_report_prompt import (
    QUARTER_MONTHS,
    build_quarterly_team_report_prompt,
)
from llmops.rate_limiter import LLMRateLimitExceeded
from llmops.cost_budget import LLMCostBudgetExceeded


@api_view(["GET"])
def health(request):
    """Basic liveness check used to verify the frontend can reach the API."""
    return Response({"status": "ok"}, status=status.HTTP_200_OK)


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class MonthlyReportViewSet(viewsets.ModelViewSet):
    """Monthly reports, filterable by name, business group, month and year."""

    queryset = MonthlyReport.objects.all()
    serializer_class = MonthlyReportSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        filters = {}
        for field in ("employee_name", "project_name", "business_group"):
            value = params.get(field)
            if value is None or value == "":
                continue
            filters[f"{field}__icontains"] = value

        for field in ("month", "year"):
            value = params.get(field)
            if value is None or value == "":
                continue
            if not value.lstrip("-").isdigit():
                raise ValidationError({field: ["Must be an integer."]})
            filters[field] = int(value)

        if filters:
            queryset = queryset.filter(**filters)

        if self.action == "retrieve":
            return queryset.prefetch_related("items")

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MonthlyReportDetailSerializer
        return MonthlyReportSerializer

    @action(detail=True, methods=["get", "post"])
    def items(self, request, pk=None):
        """List or create the items belonging to a single report."""
        report = self.get_object()
        items = report.items.all()

        if request.method == "GET":
            return Response(ReportItemSerializer(items, many=True).data)

        serializer = ReportItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(report=report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="generate-summary")
    def generate_summary(self, request):
        """Generate an AI summary draft from the current unsaved form data.

        Generation-only: this endpoint never persists anything. The final
        report is saved later through the normal create/items endpoints.
        """
        serializer = GenerateSummarySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt, prompt_version = build_employee_summary_prompt(serializer.validated_data)
        try:
            summary = LLMService().generate(prompt, feature="employee_summary", prompt_version=prompt_version, operation="employee_summary_generation",)
        except LLMRateLimitExceeded:
            return Response(
                {
                    "detail": "Too many LLM requests. Please try again later."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except LLMCostBudgetExceeded:
            return Response(
                {
                    "detail": (
                        "The monthly LLM cost budget has been reached. "
                        "Please try again later."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except LLMConfigurationError:
            return Response(
                {"detail": "AI summary generation is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except LLMResponseError:
            return Response(
                {"detail": "The AI summary could not be generated. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"summary": summary})


class ReportItemViewSet(viewsets.ModelViewSet):
    queryset = ReportItem.objects.select_related("report")
    serializer_class = ReportItemSerializer
    http_method_names = ["get", "put", "patch", "delete"]


class ManagerReportViewSet(viewsets.ViewSet):
    """Collective manager reports.

    The manager report is generated from the employee reports already stored
    in PostgreSQL. Generation-only: nothing here is automatically saved.
    """

    @action(detail=False, methods=["post"], url_path="monthly/generate")
    def monthly_generate(self, request):
        """Generate a collective monthly team report for a month/year."""
        serializer = MonthlyParamsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        month = serializer.validated_data["month"]
        year = serializer.validated_data["year"]

        reports = (
            MonthlyReport.objects.filter(month=month, year=year)
            .prefetch_related("items")
            .order_by("employee_name", "id")
        )

        if not reports.exists():
            return Response(
                {
                    "month": month,
                    "year": year,
                    "reports_count": 0,
                    "report": "",
                },
                status=status.HTTP_200_OK,
            )

        prompt, prompt_version = build_monthly_team_report_prompt(reports, month, year)
        try:
            report = LLMService().generate(prompt, feature="monthly_team_report", prompt_version=prompt_version, operation="monthly_team_report_generation",)
        except LLMRateLimitExceeded:
            return Response(
                {
                    "detail": "Too many LLM requests. Please try again later."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except LLMCostBudgetExceeded:
            return Response(
                {
                    "detail": (
                        "The monthly LLM cost budget has been reached. "
                        "Please try again later."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except LLMConfigurationError:
            return Response(
                {"detail": "AI team report generation is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except LLMResponseError:
            return Response(
                {"detail": "The AI team report could not be generated. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not isinstance(report, str):
            return Response(
                {"detail": "The AI team report could not be generated. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "month": month,
                "year": year,
                "reports_count": reports.count(),
                "report": report,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="quarterly/generate")
    def quarterly_generate(self, request):
        """Generate a collective quarterly team report for a quarter/year."""
        serializer = QuarterlyParamsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quarter = serializer.validated_data["quarter"]
        year = serializer.validated_data["year"]
        months = QUARTER_MONTHS[quarter]

        reports = (
            MonthlyReport.objects.filter(year=year, month__in=months)
            .prefetch_related("items")
            .order_by("month", "employee_name", "id")
        )

        if not reports.exists():
            return Response(
                {"detail": f"No employee reports found for Q{quarter} {year}."},
                status=status.HTTP_200_OK,
            )

        prompt, prompt_version = build_quarterly_team_report_prompt(reports, quarter, year)
        try:
            report = LLMService().generate(prompt, feature="quarterly_team_report", prompt_version=prompt_version, operation="quarterly_team_report_generation",)
        except LLMRateLimitExceeded:
            return Response(
                {
                    "detail": "Too many LLM requests. Please try again later."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except LLMCostBudgetExceeded:
            return Response(
                {
                    "detail": (
                        "The monthly LLM cost budget has been reached. "
                        "Please try again later."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except LLMConfigurationError:
            return Response(
                {"detail": "AI team report generation is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except LLMResponseError:
            return Response(
                {"detail": "The AI team report could not be generated. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not isinstance(report, str):
            return Response(
                {"detail": "The AI team report could not be generated. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "year": year,
                "quarter": quarter,
                "months": list(months),
                "report_count": reports.count(),
                "report": report,
            },
            status=status.HTTP_200_OK,
        )
