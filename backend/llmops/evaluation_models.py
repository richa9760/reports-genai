from django.db import models


class LLMEvaluation(models.Model):
    EVALUATION_REFERENCE = "reference"
    EVALUATION_LLM_JUDGE = "llm_judge"

    EVALUATION_TYPES = [
        (EVALUATION_REFERENCE, "Reference Based"),
        (EVALUATION_LLM_JUDGE, "LLM Judge"),
    ]

    id = models.BigAutoField(primary_key=True)

    request_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )

    feature = models.CharField(
        max_length=100,
        db_index=True,
    )

    evaluation_type = models.CharField(
        max_length=30,
        choices=EVALUATION_TYPES,
    )

    metric = models.CharField(
        max_length=100,
    )

    score = models.FloatField()

    reference_dataset_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    evaluator_model = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.feature} - "
            f"{self.evaluation_type} - "
            f"{self.metric}"
        )