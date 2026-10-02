from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from llmops.prompt_models import PromptVersion
from llmops.prompt_service import PromptVersionService


class PromptVersionServiceTests(TestCase):
    def setUp(self):
        PromptVersion.objects.all().delete()

    def make(self, version, feature="employee_summary", is_active=False):
        return PromptVersion.objects.create(
            feature=feature,
            version=version,
            prompt_template=(
                "You are an AI assistant writing a professional monthly "
                "status summary for an employee. Do not invent facts."
            ),
            is_active=is_active,
        )

    def test_get_active_prompt_returns_active_latest(self):
        self.make("v1", is_active=True)
        older = self.make("v2", is_active=False)
        # Make v2 created later by touching it.
        older.save()

        result = PromptVersionService.get_active_prompt("employee_summary")

        self.assertIsNotNone(result)
        self.assertEqual(result.version, "v1")
        self.assertTrue(result.is_active)

    def test_get_active_prompt_respects_feature(self):
        self.make("v1", feature="employee_summary", is_active=True)
        self.make("v1", feature="monthly_team_report", is_active=True)

        result = PromptVersionService.get_active_prompt("monthly_team_report")

        self.assertEqual(result.feature, "monthly_team_report")

    def test_get_active_prompt_returns_latest_of_multiple_active(self):
        from django.utils import timezone
        from datetime import timedelta

        v1 = self.make("v1", is_active=True)
        v2 = PromptVersion.objects.create(
            feature="employee_summary",
            version="v2",
            prompt_template=(
                "You are an AI assistant writing a professional monthly "
                "status summary for an employee. Do not invent facts."
            ),
            is_active=True,
        )
        v3 = PromptVersion.objects.create(
            feature="employee_summary",
            version="v3",
            prompt_template=(
                "You are an AI assistant writing a professional monthly "
                "status summary for an employee. Do not invent facts."
            ),
            is_active=True,
        )

        PromptVersion.objects.filter(pk=v1.pk).update(
            created_at=timezone.now() - timedelta(minutes=2)
        )
        PromptVersion.objects.filter(pk=v2.pk).update(
            created_at=timezone.now() - timedelta(minutes=1)
        )
        PromptVersion.objects.filter(pk=v3.pk).update(
            created_at=timezone.now()
        )

        result = PromptVersionService.get_active_prompt("employee_summary")

        self.assertIsNotNone(result)
        self.assertEqual(result.version, "v3")

    def test_get_active_prompt_returns_none_when_no_active(self):
        self.make("v1", is_active=False)

        self.assertIsNone(
            PromptVersionService.get_active_prompt("employee_summary")
        )

    def test_get_prompt_finds_exact_version(self):
        self.make("v1")
        self.make("v2")

        result = PromptVersionService.get_prompt("employee_summary", "v2")

        self.assertIsNotNone(result)
        self.assertEqual(result.version, "v2")

    def test_get_prompt_returns_none_for_missing_version(self):
        self.make("v1")

        self.assertIsNone(
            PromptVersionService.get_prompt("employee_summary", "v9")
        )

    def test_activate_prompt_deactivates_other_active_versions(self):
        v1 = self.make("v1", is_active=True)
        v2 = self.make("v2", is_active=False)

        PromptVersionService.activate_prompt(v2)

        self.assertFalse(
            PromptVersion.objects.get(pk=v1.pk).is_active
        )
        self.assertTrue(
            PromptVersion.objects.get(pk=v2.pk).is_active
        )

    def test_activate_prompt_keeps_only_target_active(self):
        v1 = self.make("v1", is_active=True)
        v2 = self.make("v2", is_active=True)

        PromptVersionService.activate_prompt(v2)

        active = list(
            PromptVersion.objects.filter(is_active=True).values_list(
                "version", flat=True
            )
        )
        self.assertEqual(active, ["v2"])

    def test_duplicate_feature_and_version_is_rejected(self):
        self.make("v1")

        from llmops.prompt_models import PromptVersion as PV

        duplicate = PV(
            feature="employee_summary",
            version="v1",
            prompt_template=(
                "You are an AI assistant writing a professional monthly "
                "status summary for an employee. Do not invent facts."
            ),
            is_active=False,
        )

        with self.assertRaises(IntegrityError):
            duplicate.save()


class PromptVersionApiTests(APITestCase):
    def setUp(self):
        PromptVersion.objects.all().delete()

    def list_url(self):
        return reverse("prompt-version-list-create")

    def activate_url(self, pk):
        return reverse("prompt-version-activate", args=[pk])

    def valid_payload(self, version="v1", **overrides):
        payload = {
            "feature": "employee_summary",
            "version": version,
            "prompt_template": (
                "You are an AI assistant writing a professional monthly "
                "status summary for an employee. Do not invent facts. "
            ),
        }
        payload.update(overrides)
        return payload

    def test_create_prompt_version(self):
        response = self.client.post(
            self.list_url(),
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            PromptVersion.objects.count(), 1
        )
        self.assertFalse(response.data["is_active"])

    def test_create_ignores_requested_is_active_true(self):
        response = self.client.post(
            self.list_url(),
            self.valid_payload(is_active=True),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["is_active"])

    def test_duplicate_feature_version_rejected(self):
        self.client.post(
            self.list_url(),
            self.valid_payload(version="v1"),
            format="json",
        )
        response = self.client.post(
            self.list_url(),
            self.valid_payload(version="v1"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activate_endpoint(self):
        created = self.client.post(
            self.list_url(),
            self.valid_payload(version="v1"),
            format="json",
        ).data

        response = self.client.post(
            self.activate_url(created["id"]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            PromptVersion.objects.get(pk=created["id"]).is_active
        )

    def test_activate_missing_version_returns_404(self):
        response = self.client.post(
            self.activate_url(9999),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_prompt_template_must_be_20_chars(self):
        response = self.client.post(
            self.list_url(),
            self.valid_payload(prompt_template="Too short."),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("prompt_template", response.data)