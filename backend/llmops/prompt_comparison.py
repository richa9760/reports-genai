from llmops.evaluation_data import EMPLOYEE_SUMMARY_EVALUATION_DATASET
from llmops.evaluation_service import EvaluationResultService
from reports.services.prompt_builder import build_employee_summary_prompt_for_version
from llmops.reference_evaluator import ReferenceBasedEvaluator
from reports.services.llm_service import LLMService
from llmops.models import LLMRequest


class PromptComparisonService:

    @staticmethod
    def compare_employee_summary(case, version_a="v1", version_b="v2"):
        service = LLMService()

        results = {}

        for version in [version_a, version_b]:
            prompt, prompt_version = (
                build_employee_summary_prompt_for_version(
                    case["input"],
                    version,
                )
            )

            summary = service.generate(
                prompt=prompt,
                feature="employee_summary",
                prompt_version=prompt_version,
                operation=f"prompt_comparison_{version}",
            )

            scores = ReferenceBasedEvaluator.evaluate(
                reference=case["reference_summary"],
                generated=summary,
            )

            request = (
                LLMRequest.objects
                .filter(
                    feature="employee_summary",
                    prompt_version=prompt_version,
                    operation=f"prompt_comparison_{version}",
                )
                .order_by("-created_at")
                .first()
            )

            if request is None:
                raise ValueError(
                    f"LLM request not found for prompt version {version}."
                )

            EvaluationResultService.save_reference_scores(
                request_id=request.request_id,
                feature="employee_summary",
                dataset_id=case["id"],
                scores=scores,
            )

            results[version] = {
                "request_id": request.request_id,
                "summary": summary,
                "scores": scores,
            }

        return results