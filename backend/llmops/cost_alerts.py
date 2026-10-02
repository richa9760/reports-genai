import logging
from decimal import Decimal

from llmops.cost_budget import LLMCostBudgetService

logger = logging.getLogger(__name__)


class LLMCostAlertService:

    @staticmethod
    def check_and_alert():
        current_cost = (
            LLMCostBudgetService.get_current_month_cost()
        )
        budget = LLMCostBudgetService.get_budget()

        if budget <= Decimal("0"):
            return

        usage_percentage = (
            current_cost / budget
        ) * Decimal("100")

        if usage_percentage >= Decimal("80"):
            logger.warning(
                "LLM monthly cost budget usage is %.2f%% "
                "(%s / %s).",
                usage_percentage,
                current_cost,
                budget,
            )