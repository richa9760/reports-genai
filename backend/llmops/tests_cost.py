from decimal import Decimal
from unittest import mock
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from llmops.cost_alerts import LLMCostAlertService
from llmops.cost_budget import (
    LLMCostBudgetExceeded,
    LLMCostBudgetService,
)
from llmops.models import LLMRequest


def make_request(
    status=LLMRequest.STATUS_SUCCESS,
    total_cost=None,
    input_cost=None,
    output_cost=None,
    started_at=None,
):
    record = LLMRequest.objects.create(
        feature="employee_summary",
        provider="groq",
        model="openai/gpt-oss-120b",
        started_at=started_at or timezone.now(),
        status=status,
        total_cost=total_cost,
        input_cost=input_cost,
        output_cost=output_cost,
    )

    return record


class GetCurrentMonthCostTests(TestCase):
    def setUp(self):
        LLMRequest.objects.all().delete()

    def test_sums_successful_costs_in_current_month(self):
        make_request(total_cost=Decimal("1.50"))
        make_request(total_cost=Decimal("2.50"))

        self.assertEqual(
            LLMCostBudgetService.get_current_month_cost(),
            Decimal("4.00"),
        )

    def test_ignores_failed_requests(self):
        make_request(total_cost=Decimal("1.00"))
        make_request(total_cost=Decimal("5.00"), status=LLMRequest.STATUS_FAILED)
        make_request(total_cost=Decimal("3.00"), status=LLMRequest.STATUS_PENDING)

        self.assertEqual(
            LLMCostBudgetService.get_current_month_cost(),
            Decimal("1.00"),
        )

    def test_ignores_null_costs(self):
        make_request(total_cost=None)

        self.assertEqual(
            LLMCostBudgetService.get_current_month_cost(),
            Decimal("0"),
        )

    def test_excludes_other_months(self):
        current = make_request(total_cost=Decimal("2.00"))

        previous_month = timezone.now() - timedelta(days=40)
        old = make_request(total_cost=Decimal("9.00"))
        LLMRequest.objects.filter(pk=old.pk).update(created_at=previous_month)

        self.assertEqual(
            LLMCostBudgetService.get_current_month_cost(),
            Decimal("2.00"),
        )

    def test_returns_zero_when_no_records(self):
        self.assertEqual(
            LLMCostBudgetService.get_current_month_cost(),
            Decimal("0"),
        )


class GetBudgetTests(TestCase):
    @override_settings(LLM_MONTHLY_COST_BUDGET=10.00)
    def test_returns_configured_budget(self):
        self.assertEqual(
            LLMCostBudgetService.get_budget(),
            Decimal("10.00"),
        )


class CheckBudgetTests(TestCase):
    def test_raises_when_cost_reaches_budget(self):
        make_request(total_cost=Decimal("5.00"))
        make_request(total_cost=Decimal("5.00"))

        with self.assertRaises(LLMCostBudgetExceeded):
            LLMCostBudgetService.check_budget()

    @override_settings(LLM_MONTHLY_COST_BUDGET=100.00)
    def test_does_not_raise_below_budget(self):
        make_request(total_cost=Decimal("5.00"))

        self.assertIsNone(LLMCostBudgetService.check_budget())

    @override_settings(LLM_MONTHLY_COST_BUDGET=100.00)
    def test_is_budget_exceeded_returns_false_below_budget(self):
        make_request(total_cost=Decimal("5.00"))

        self.assertFalse(LLMCostBudgetService.is_budget_exceeded())

    def test_is_budget_exceeded_returns_true_at_budget(self):
        make_request(total_cost=Decimal("10.00"))

        self.assertTrue(LLMCostBudgetService.is_budget_exceeded())


class CostAlertTests(TestCase):
    def setUp(self):
        LLMRequest.objects.all().delete()

    @override_settings(LLM_MONTHLY_COST_BUDGET=100.00)
    @mock.patch("llmops.cost_alerts.logger.warning")
    def test_no_warning_below_80_percent(self, mock_warning):
        make_request(total_cost=Decimal("79.00"))

        LLMCostAlertService.check_and_alert()

        mock_warning.assert_not_called()

    @override_settings(LLM_MONTHLY_COST_BUDGET=100.00)
    @mock.patch("llmops.cost_alerts.logger.warning")
    def test_warning_at_80_percent(self, mock_warning):
        make_request(total_cost=Decimal("80.00"))

        LLMCostAlertService.check_and_alert()

        mock_warning.assert_called_once()

    @override_settings(LLM_MONTHLY_COST_BUDGET=100.00)
    @mock.patch("llmops.cost_alerts.logger.warning")
    def test_warning_above_80_percent(self, mock_warning):
        make_request(total_cost=Decimal("99.00"))

        LLMCostAlertService.check_and_alert()

        mock_warning.assert_called_once()

    @override_settings(LLM_MONTHLY_COST_BUDGET=0)
    @mock.patch("llmops.cost_alerts.logger.warning")
    def test_zero_budget_is_safely_skipped(self, mock_warning):
        make_request(total_cost=Decimal("50.00"))

        self.assertIsNone(LLMCostAlertService.check_and_alert())

        mock_warning.assert_not_called()