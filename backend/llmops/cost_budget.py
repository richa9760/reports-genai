from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from llmops.models import LLMRequest


class LLMCostBudgetExceeded(Exception):
    """Raised when the monthly LLM cost budget is exceeded."""


class LLMCostBudgetService:

    @staticmethod
    def get_current_month_cost():
        now = timezone.now()

        total_cost = (
            LLMRequest.objects
            .filter(
                created_at__year=now.year,
                created_at__month=now.month,
                status=LLMRequest.STATUS_SUCCESS,
                total_cost__isnull=False,
            )
            .aggregate(total=Sum("total_cost"))
            ["total"]
        )

        return total_cost or Decimal("0")

    @staticmethod
    def get_budget():
        return Decimal(
            str(settings.LLM_MONTHLY_COST_BUDGET)
        )

    @classmethod
    def is_budget_exceeded(cls):
        return (
            cls.get_current_month_cost()
            >= cls.get_budget()
        )

    @classmethod
    def check_budget(cls):
        if cls.is_budget_exceeded():
            raise LLMCostBudgetExceeded(
                "Monthly LLM cost budget exceeded."
            )