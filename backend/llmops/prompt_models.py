from django.db import models


class PromptVersion(models.Model):
    feature = models.CharField(max_length=100)

    version = models.CharField(max_length=50)

    prompt_template = models.TextField()

    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["feature", "version"],
                name="unique_prompt_feature_version",
            )
        ]
        indexes = [
            models.Index(fields=["feature"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.feature} - {self.version}"