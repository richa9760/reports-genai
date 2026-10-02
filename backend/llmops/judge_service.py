import json
import uuid


from llmops.judge_prompts import EMPLOYEE_SUMMARY_JUDGE_PROMPT
from reports.services.llm_service import LLMService
from llmops.models import LLMRequest
from llmops.mlflow_service import MLflowTrackingService


class LLMJudgeService:

    @staticmethod
    def build_prompt(input_data, generated_summary):
        return EMPLOYEE_SUMMARY_JUDGE_PROMPT.format(
            input_data=json.dumps(
                input_data,
                indent=2,
                ensure_ascii=False,
            ),
            generated_summary=generated_summary,
        )

    @staticmethod
    def parse_scores(response_text):
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "LLM judge returned invalid JSON."
            ) from exc

        required_metrics = [
            "relevance",
            "faithfulness",
            "completeness",
            "clarity",
        ]

        for metric in required_metrics:
            if metric not in result:
                raise ValueError(
                    f"LLM judge response missing metric: {metric}"
                )

            score = result[metric]

            if (
                not isinstance(score, int)
                or isinstance(score, bool)
                or score < 1
                or score > 5
            ):
                raise ValueError(
                    f"Invalid score for {metric}: {score}"
                )

        return {
            metric: result[metric]
            for metric in required_metrics
        }
    
    @staticmethod
    def evaluate(input_data, generated_summary):
        prompt = LLMJudgeService.build_prompt(
            input_data=input_data,
            generated_summary=generated_summary,
        )

        trace_id = uuid.uuid4()

        llm_service = LLMService()

        response = llm_service.generate(
            prompt=prompt,
            feature="llm_evaluation",
            operation="employee_summary_llm_judge",
            trace_id=trace_id,
        )

        scores = LLMJudgeService.parse_scores(response)

        request = (
            LLMRequest.objects
            .filter(trace_id=trace_id)
            .order_by("-created_at")
            .first()
        )

        MLflowTrackingService.log_evaluation_run(
            scores=scores,
            feature="employee_summary",
            evaluator_model=request.model,
        )

        if request is None:
            raise ValueError(
                "LLM evaluation request could not be found."
            )

        return {
            "request_id": request.request_id,
            "model": request.model,
            "scores": scores,
        }