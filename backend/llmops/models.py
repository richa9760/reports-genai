import uuid

from django.db import models


class LLMRequest(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.BigAutoField(primary_key=True)

    request_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    trace_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )

    operation = models.CharField(
    max_length=100,
    null=True,
    blank=True,
    db_index=True,
    )

    feature = models.CharField(max_length=100)

    provider = models.CharField(max_length=50)

    model = models.CharField(max_length=200)

    started_at = models.DateTimeField()

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    latency_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
    )

    input_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    output_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    total_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    input_cost = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        null=True,
        blank=True,
    )

    output_cost = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        null=True,
        blank=True,
    )

    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        null=True,
        blank=True,
    )

    error_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    error_code = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    prompt_version = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["feature"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.feature} - {self.status}"
    
from .prompt_models import PromptVersion
from .evaluation_models import LLMEvaluation