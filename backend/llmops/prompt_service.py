from llmops.prompt_models import PromptVersion


class PromptVersionService:

    @staticmethod
    def get_active_prompt(feature):
        return (
            PromptVersion.objects
            .filter(
                feature=feature,
                is_active=True,
            )
            .order_by("-created_at")
            .first()
        )
    
    @staticmethod
    def activate_prompt(prompt_version):
        PromptVersion.objects.filter(
            feature=prompt_version.feature,
            is_active=True,
        ).exclude(
            id=prompt_version.id
        ).update(
            is_active=False
        )

        prompt_version.is_active = True
        prompt_version.save(
            update_fields=["is_active"]
        )

    @staticmethod
    def get_prompt(feature, version):
        return (
            PromptVersion.objects
            .filter(
                feature=feature,
                version=version,
            )
            .first()
        )
