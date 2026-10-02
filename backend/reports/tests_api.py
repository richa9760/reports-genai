from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Employee, MonthlyReport, Project, ReportItem, ReportItemType


class EmployeeApiTests(APITestCase):
    def test_create_employee(self):
        response = self.client.post(
            reverse("reports:employee-list"),
            {"name": "Ada Lovelace", "email": "ada@example.com"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Ada Lovelace")
        self.assertEqual(response.data["email"], "ada@example.com")
        self.assertEqual(Employee.objects.count(), 1)

    def test_list_employees(self):
        Employee.objects.create(name="Ada Lovelace", email="ada@example.com")
        Employee.objects.create(name="Alan Turing", email="alan@example.com")

        response = self.client.get(reverse("reports:employee-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_employee(self):
        employee = Employee.objects.create(name="Ada Lovelace", email="ada@example.com")

        response = self.client.get(
            reverse("reports:employee-detail", args=[employee.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], employee.id)
        self.assertEqual(response.data["name"], "Ada Lovelace")

    def test_retrieve_missing_employee_returns_404(self):
        response = self.client.get(reverse("reports:employee-detail", args=[9999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_employee(self):
        employee = Employee.objects.create(name="Ada Lovelace", email="ada@example.com")

        response = self.client.patch(
            reverse("reports:employee-detail", args=[employee.id]),
            {"name": "Ada L."},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        employee.refresh_from_db()
        self.assertEqual(employee.name, "Ada L.")

    def test_delete_employee(self):
        employee = Employee.objects.create(name="Ada Lovelace", email="ada@example.com")

        response = self.client.delete(
            reverse("reports:employee-detail", args=[employee.id])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Employee.objects.count(), 0)

    def test_create_employee_with_duplicate_email_is_rejected(self):
        Employee.objects.create(name="Ada Lovelace", email="ada@example.com")

        response = self.client.post(
            reverse("reports:employee-list"),
            {"name": "Ada Clone", "email": "ada@example.com"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_create_employee_missing_name_is_rejected(self):
        response = self.client.post(
            reverse("reports:employee-list"),
            {"email": "nameless@example.com"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)


class ProjectApiTests(APITestCase):
    def test_create_project(self):
        response = self.client.post(
            reverse("reports:project-list"),
            {"name": "Apollo", "business_group": "Engineering"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Apollo")
        self.assertEqual(response.data["business_group"], "Engineering")
        self.assertEqual(Project.objects.count(), 1)

    def test_list_projects(self):
        Project.objects.create(name="Apollo", business_group="Engineering")
        Project.objects.create(name="Gemini", business_group="Research")

        response = self.client.get(reverse("reports:project-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_project_missing_business_group_is_rejected(self):
        response = self.client.post(reverse("reports:project-list"), {"name": "Apollo"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("business_group", response.data)

    def test_retrieve_project(self):
        project = Project.objects.create(name="Apollo", business_group="Engineering")

        response = self.client.get(reverse("reports:project-detail", args=[project.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], project.id)


class MonthlyReportApiTests(APITestCase):
    def create_report(self, **overrides):
        payload = {
            "employee_name": "Ada Lovelace",
            "project_name": "Apollo",
            "business_group": "Engineering",
            "month": 9,
            "year": 2026,
            "summary": "September summary",
        }
        payload.update(overrides)
        return self.client.post(reverse("reports:monthlyreport-list"), payload, format="json")

    def test_create_report(self):
        response = self.create_report()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["employee_name"], "Ada Lovelace")
        self.assertEqual(response.data["project_name"], "Apollo")
        self.assertEqual(response.data["business_group"], "Engineering")
        self.assertEqual(response.data["month"], 9)
        self.assertEqual(response.data["year"], 2026)
        self.assertEqual(response.data["summary"], "September summary")
        self.assertEqual(MonthlyReport.objects.count(), 1)

    def test_list_reports(self):
        self.create_report()

        response = self.client.get(reverse("reports:monthlyreport-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_reports_includes_names_and_business_group(self):
        self.create_report()

        response = self.client.get(reverse("reports:monthlyreport-list"))

        self.assertEqual(response.data[0]["employee_name"], "Ada Lovelace")
        self.assertEqual(response.data[0]["project_name"], "Apollo")
        self.assertEqual(response.data[0]["business_group"], "Engineering")

    def test_retrieve_report(self):
        report = MonthlyReport.objects.create(
            employee_name="Ada Lovelace",
            project_name="Apollo",
            business_group="Engineering",
            month=9,
            year=2026,
        )

        response = self.client.get(
            reverse("reports:monthlyreport-detail", args=[report.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], report.id)
        self.assertEqual(response.data["employee_name"], "Ada Lovelace")
        self.assertEqual(response.data["project_name"], "Apollo")
        self.assertEqual(response.data["business_group"], "Engineering")

    def test_update_report(self):
        report = MonthlyReport.objects.create(
            employee_name="Ada Lovelace",
            project_name="Apollo",
            business_group="Engineering",
            month=9,
            year=2026,
        )

        response = self.client.patch(
            reverse("reports:monthlyreport-detail", args=[report.id]),
            {"summary": "Updated summary"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.summary, "Updated summary")

    def test_delete_report(self):
        report = MonthlyReport.objects.create(
            employee_name="Ada Lovelace",
            project_name="Apollo",
            business_group="Engineering",
            month=9,
            year=2026,
        )

        response = self.client.delete(
            reverse("reports:monthlyreport-detail", args=[report.id])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(MonthlyReport.objects.count(), 0)

    def test_filter_by_employee_name(self):
        self.create_report()
        self.create_report(employee_name="Alan Turing", month=10)

        response = self.client.get(
            reverse("reports:monthlyreport-list"),
            {"employee_name": "Ada"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["employee_name"], "Ada Lovelace")

    def test_filter_by_project_name(self):
        self.create_report()
        self.create_report(project_name="Gemini", month=10)

        response = self.client.get(
            reverse("reports:monthlyreport-list"),
            {"project_name": "Gemini"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["project_name"], "Gemini")

    def test_filter_by_business_group(self):
        self.create_report()
        self.create_report(business_group="Research", month=10)

        response = self.client.get(
            reverse("reports:monthlyreport-list"),
            {"business_group": "research"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["business_group"], "Research")

    def test_filter_by_month_and_year(self):
        self.create_report()
        self.create_report(month=10, year=2026)
        self.create_report(month=9, year=2025)

        response = self.client.get(
            reverse("reports:monthlyreport-list"), {"month": 9, "year": 2026}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["month"], 9)
        self.assertEqual(response.data[0]["year"], 2026)

    def test_filter_by_employee_month_and_year(self):
        self.create_report()
        self.create_report(employee_name="Alan Turing")

        response = self.client.get(
            reverse("reports:monthlyreport-list"),
            {"employee_name": "Ada Lovelace", "month": 9, "year": 2026},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_with_no_matches_returns_empty_list(self):
        self.create_report()

        response = self.client.get(
            reverse("reports:monthlyreport-list"), {"month": 1, "year": 1999}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_filter_with_non_integer_value_is_rejected(self):
        response = self.client.get(
            reverse("reports:monthlyreport-list"), {"month": "not-a-number"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("month", response.data)

    def test_invalid_month_is_rejected(self):
        response = self.create_report(month=13)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("month", response.data)
        self.assertEqual(MonthlyReport.objects.count(), 0)

    def test_missing_required_fields_are_rejected(self):
        response = self.client.post(
            reverse("reports:monthlyreport-list"), {"month": 9}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("employee_name", response.data)
        self.assertIn("project_name", response.data)
        self.assertIn("business_group", response.data)
        self.assertIn("year", response.data)

    def test_employee_name_is_trimmed(self):
        response = self.create_report(employee_name="  Ada Lovelace  ")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["employee_name"], "Ada Lovelace")

    def test_blank_employee_name_is_rejected(self):
        response = self.create_report(employee_name="   ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("employee_name", response.data)
        self.assertEqual(MonthlyReport.objects.count(), 0)

    def test_duplicate_report_is_rejected(self):
        self.assertEqual(self.create_report().status_code, status.HTTP_201_CREATED)

        response = self.create_report()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(MonthlyReport.objects.count(), 1)


class ReportItemApiTests(APITestCase):
    def setUp(self):
        self.report = MonthlyReport.objects.create(
            employee_name="Ada Lovelace",
            project_name="Apollo",
            business_group="Engineering",
            month=9,
            year=2026,
        )

    def create_item(self, item_type=ReportItemType.TASK, content="Some content"):
        return self.client.post(
            reverse("reports:monthlyreport-items", args=[self.report.id]),
            {"item_type": item_type, "content": content},
        )

    def test_create_item(self):
        response = self.create_item(content="Completed API implementation")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["item_type"], ReportItemType.TASK)
        self.assertEqual(response.data["content"], "Completed API implementation")
        self.assertEqual(ReportItem.objects.count(), 1)
        self.assertEqual(ReportItem.objects.first().report, self.report)

    def test_create_item_with_invalid_type_is_rejected(self):
        response = self.create_item(item_type="NOT_A_TYPE")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("item_type", response.data)

    def test_create_item_missing_content_is_rejected(self):
        response = self.client.post(
            reverse("reports:monthlyreport-items", args=[self.report.id]),
            {"item_type": ReportItemType.TASK},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_create_item_for_unknown_report_returns_404(self):
        response = self.client.post(
            reverse("reports:monthlyreport-items", args=[9999]),
            {"item_type": ReportItemType.TASK, "content": "Orphan"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_items_for_report(self):
        self.create_item(content="Task A")
        self.create_item(item_type=ReportItemType.COURSE, content="Course A")

        response = self.client.get(
            reverse("reports:monthlyreport-items", args=[self.report.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_items_only_returns_items_for_that_report(self):
        self.create_item(content="Task A")
        other_report = MonthlyReport.objects.create(
            employee_name="Ada Lovelace",
            project_name="Apollo",
            business_group="Engineering",
            month=10,
            year=2026,
        )
        ReportItem.objects.create(
            report=other_report, item_type=ReportItemType.TASK, content="Task B"
        )

        response = self.client.get(
            reverse("reports:monthlyreport-items", args=[self.report.id])
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["content"], "Task A")

    def test_retrieve_report_groups_items_by_type(self):
        for item_type in ReportItemType:
            ReportItem.objects.create(
                report=self.report, item_type=item_type, content=f"Content {item_type.value}"
            )

        response = self.client.get(
            reverse("reports:monthlyreport-detail", args=[self.report.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["items"]
        for item_type in ReportItemType:
            self.assertIn(item_type.value, items)
            self.assertEqual(len(items[item_type.value]), 1)
            self.assertEqual(items[item_type.value][0]["content"], f"Content {item_type.value}")

    def test_retrieve_report_includes_business_group(self):
        response = self.client.get(
            reverse("reports:monthlyreport-detail", args=[self.report.id])
        )

        self.assertEqual(response.data["business_group"], "Engineering")

    def test_retrieve_report_with_no_items_returns_empty_groups(self):
        response = self.client.get(
            reverse("reports:monthlyreport-detail", args=[self.report.id])
        )

        items = response.data["items"]
        for item_type in ReportItemType:
            self.assertEqual(items[item_type.value], [])

    def test_update_item(self):
        item = ReportItem.objects.create(
            report=self.report, item_type=ReportItemType.TASK, content="Old content"
        )

        response = self.client.patch(
            reverse("reports:reportitem-detail", args=[item.id]),
            {"content": "New content"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.content, "New content")

    def test_update_item_type(self):
        item = ReportItem.objects.create(
            report=self.report, item_type=ReportItemType.TASK, content="Some task"
        )

        response = self.client.patch(
            reverse("reports:reportitem-detail", args=[item.id]),
            {"item_type": ReportItemType.ACHIEVEMENT},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.item_type, ReportItemType.ACHIEVEMENT)

    def test_delete_item(self):
        item = ReportItem.objects.create(
            report=self.report, item_type=ReportItemType.TASK, content="Some task"
        )

        response = self.client.delete(
            reverse("reports:reportitem-detail", args=[item.id])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ReportItem.objects.count(), 0)

    def test_update_missing_item_returns_404(self):
        response = self.client.patch(
            reverse("reports:reportitem-detail", args=[9999]), {"content": "Nope"}
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_report_items_endpoint_does_not_allow_post(self):
        response = self.client.post(
            reverse("reports:reportitem-list"), {"item_type": "TASK", "content": "x"}
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
