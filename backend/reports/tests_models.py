from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Employee, MonthlyReport, Project, ReportItem, ReportItemType


class EmployeeTests(TestCase):
    def test_employee_can_be_created(self):
        employee = Employee.objects.create(name="Ada Lovelace", email="ada@example.com")

        self.assertEqual(employee.name, "Ada Lovelace")
        self.assertEqual(employee.email, "ada@example.com")
        self.assertIsNotNone(employee.pk)
        self.assertIsNotNone(employee.created_at)
        self.assertIsNotNone(employee.updated_at)

    def test_email_uniqueness_is_enforced(self):
        Employee.objects.create(name="Ada Lovelace", email="ada@example.com")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.create(name="Ada Clone", email="ada@example.com")

    def test_employee_name_cannot_be_blank(self):
        employee = Employee(name="", email="blank@example.com")

        with self.assertRaises(ValidationError):
            employee.full_clean()

    def test_invalid_email_is_rejected(self):
        employee = Employee(name="Bad Email", email="not-an-email")

        with self.assertRaises(ValidationError):
            employee.full_clean()


class ProjectTests(TestCase):
    def test_project_can_be_created(self):
        project = Project.objects.create(name="Apollo", business_group="Engineering")

        self.assertEqual(project.name, "Apollo")
        self.assertEqual(project.business_group, "Engineering")
        self.assertIsNotNone(project.pk)

    def test_project_business_group_cannot_be_blank(self):
        project = Project(name="Apollo", business_group="")

        with self.assertRaises(ValidationError):
            project.full_clean()


class MonthlyReportTests(TestCase):
    def setUp(self):
        self.report_data = {
            "employee_name": "Ada Lovelace",
            "project_name": "Apollo",
            "business_group": "Engineering",
        }

    def test_report_can_be_created(self):
        report = MonthlyReport.objects.create(
            **self.report_data,
            month=5,
            year=2026,
            summary="Worked on the guidance computer.",
        )

        self.assertEqual(report.month, 5)
        self.assertEqual(report.year, 2026)
        self.assertEqual(report.employee_name, "Ada Lovelace")
        self.assertEqual(report.project_name, "Apollo")
        self.assertEqual(report.business_group, "Engineering")

    def test_summary_is_optional(self):
        report = MonthlyReport.objects.create(**self.report_data, month=6, year=2026)

        self.assertEqual(report.summary, "")

    def test_report_names_must_not_be_blank(self):
        report = MonthlyReport(employee_name="", project_name="", business_group="", month=1, year=2026)

        with self.assertRaises(ValidationError):
            report.full_clean()

    def test_duplicate_employee_project_business_group_month_year_is_rejected(self):
        MonthlyReport.objects.create(**self.report_data, month=3, year=2026)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MonthlyReport.objects.create(**self.report_data, month=3, year=2026)

    def test_same_month_and_year_allowed_for_different_project(self):
        MonthlyReport.objects.create(**self.report_data, month=3, year=2026)
        MonthlyReport.objects.create(
            employee_name="Ada Lovelace",
            project_name="Gemini",
            business_group="Engineering",
            month=3,
            year=2026,
        )

        self.assertEqual(MonthlyReport.objects.filter(month=3, year=2026).count(), 2)

    def test_invalid_month_is_rejected_by_validation(self):
        report = MonthlyReport(**self.report_data, month=13, year=2026)

        with self.assertRaises(ValidationError) as context:
            report.full_clean()

        self.assertIn("month", context.exception.error_dict)

    def test_invalid_month_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MonthlyReport.objects.create(**self.report_data, month=0, year=2026)

    def test_invalid_year_is_rejected_by_validation(self):
        report = MonthlyReport(**self.report_data, month=1, year=0)

        with self.assertRaises(ValidationError) as context:
            report.full_clean()

        self.assertIn("year", context.exception.error_dict)


class ReportItemTests(TestCase):
    def setUp(self):
        self.report = MonthlyReport.objects.create(
            employee_name="Ada Lovelace",
            project_name="Apollo",
            business_group="Engineering",
            month=7,
            year=2026,
        )

    def test_report_item_can_be_created(self):
        item = ReportItem.objects.create(
            report=self.report,
            item_type=ReportItemType.TASK,
            content="Wrote the analytical engine notes.",
        )

        self.assertEqual(item.report, self.report)
        self.assertEqual(item.item_type, ReportItemType.TASK)
        self.assertEqual(item.content, "Wrote the analytical engine notes.")
        self.assertIsNotNone(item.pk)

    def test_all_item_types_are_available(self):
        expected = {"TASK", "ACHIEVEMENT", "COURSE", "HOLIDAY", "IDEA"}

        self.assertEqual({value for value, _ in ReportItemType.choices}, expected)

    def test_item_type_can_be_each_choice(self):
        for item_type in ReportItemType:
            item = ReportItem.objects.create(
                report=self.report,
                item_type=item_type,
                content=f"Content for {item_type.value}",
            )

            self.assertEqual(item.item_type, item_type.value)

    def test_invalid_item_type_is_rejected(self):
        item = ReportItem(report=self.report, item_type="UNKNOWN", content="Nope")

        with self.assertRaises(ValidationError) as context:
            item.full_clean()

        self.assertIn("item_type", context.exception.error_dict)

    def test_report_items_relationship(self):
        ReportItem.objects.create(
            report=self.report, item_type=ReportItemType.TASK, content="Task A"
        )
        ReportItem.objects.create(
            report=self.report, item_type=ReportItemType.COURSE, content="Course A"
        )

        self.assertEqual(self.report.items.count(), 2)
        self.assertEqual(self.report.items.filter(item_type=ReportItemType.COURSE).count(), 1)

    def test_items_are_deleted_with_report(self):
        ReportItem.objects.create(
            report=self.report, item_type=ReportItemType.IDEA, content="Idea A"
        )

        self.report.delete()

        self.assertEqual(ReportItem.objects.count(), 0)
