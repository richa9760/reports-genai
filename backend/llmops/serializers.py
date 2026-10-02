from rest_framework import serializers

from llmops.models import LLMRequest
from llmops.prompt_models import PromptVersion


class LLMRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMRequest
        fields = [
            "request_id",
            "trace_id",
            "operation",
            "feature",
            "prompt_version",
            "provider",
            "model",
            "started_at",
            "completed_at",
            "latency_ms",
            "status",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "input_cost",
            "output_cost",
            "total_cost",
            "error_type",
            "created_at",
        ]

class PromptVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptVersion
        fields = [
            "id",
            "feature",
            "version",
            "prompt_template",
            "is_active",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "is_active",
        ]
    def validate_is_active(self, value):
        if value:
            raise serializers.ValidationError(
                "New prompt versions must be created inactive. "
                "Use the activation endpoint to activate a version."
            )

        return value
    def validate_prompt_template(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Prompt template cannot be empty."
            )

        if len(value) < 20:
            raise serializers.ValidationError(
                "Prompt template is too short."
            )

        return value
    
    def validate_feature(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Feature cannot be empty."
            )

        return value


    def validate_version(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Version cannot be empty."
            )

        return value