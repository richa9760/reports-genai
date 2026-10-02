from django.test import TestCase

from llmops.pii_sanitizer import sanitize_report_data, sanitize_text


class SanitizeTextTests(TestCase):
    def test_email_is_replaced(self):
        self.assertEqual(
            sanitize_text("Contact richa.verma@example.com today"),
            "Contact [EMAIL] today",
        )

    def test_phone_number_is_replaced(self):
        self.assertEqual(
            sanitize_text("Call me at 123-456-7890 today"),
            "Call me at [PHONE] today",
        )

    def test_multiple_pii_instances_are_replaced(self):
        result = sanitize_text(
            "Email a@b.com and then call +1 123 456 7890 maybe"
        )
        self.assertIn("[EMAIL]", result)
        self.assertIn("[PHONE]", result)
        self.assertNotIn("a@b.com", result)

    def test_ordinary_text_is_unchanged(self):
        self.assertEqual(
            sanitize_text("Completed API implementation"),
            "Completed API implementation",
        )

    def test_empty_value_returns_value(self):
        self.assertIsNone(sanitize_text(None))
        self.assertEqual(sanitize_text(""), "")


class SanitizeReportDataTests(TestCase):
    def setUp(self):
        self.payload = {
            "employee_name": "Richa Verma <richa.verma@example.com>",
            "project_name": "AI Platform",
            "business_group": "Engineering",
            "tasks": ["Fixed auth bug 123-456-7890"],
            "achievements": ["Named engineer of the month"],
            "courses": ["Advanced PostgreSQL 41"],
            "planned_holidays": ["Oct 5-9"],
            "ideas": ["Automate the CI pipeline"],
        }

    def test_scalar_fields_are_sanitized(self):
        sanitized = sanitize_report_data(self.payload)
        self.assertIn("[EMAIL]", sanitized["employee_name"])
        self.assertNotIn("richa.verma@example.com", sanitized["employee_name"])

    def test_list_fields_are_sanitized(self):
        sanitized = sanitize_report_data(self.payload)
        self.assertIn("[PHONE]", sanitized["tasks"][0])
        self.assertNotIn("123-456-7890", sanitized["tasks"][0])

    def test_original_dict_is_not_mutated(self):
        original = {
            "employee_name": "Richa <richa@example.com>",
            "tasks": ["Call 123-456-7890"],
        }
        snapshot = {
            key: list(value) if isinstance(value, list) else value
            for key, value in original.items()
        }

        sanitize_report_data(original)

        self.assertEqual(original, snapshot)

    def test_returns_a_new_dict(self):
        original = {"employee_name": "Richa"}
        result = sanitize_report_data(original)
        self.assertIsNot(result, original)

    def test_missing_optional_fields_are_ignored(self):
        sanitized = sanitize_report_data({"employee_name": "Richa"})
        self.assertEqual(sanitized["employee_name"], "Richa")
        self.assertNotIn("tasks", sanitized)