from llmops.evaluation_service import EvaluationResultService
from llmops.judge_service import LLMJudgeService
from llmops.mlflow_service import MLflowTrackingService
from llmops.quality_metrics import LLMQualityMetricsService


class EvaluationRunner:

    @staticmethod
    def evaluate_employee_summary(case, generated_summary):
        result = LLMJudgeService.evaluate(
            input_data=case["input"],
            generated_summary=generated_summary,
        )

        EvaluationResultService.save_llm_judge_scores(
            request_id=result["request_id"],
            feature="employee_summary",
            evaluator_model=result["model"],
            scores=result["scores"],
        )

        quality_score = (
            LLMQualityMetricsService.calculate_quality_score(
                result["scores"]
            )
        )

        EvaluationResultService.save_quality_score(
            request_id=result["request_id"],
            feature="employee_summary",
            quality_score=quality_score,
            evaluator_model=result["model"],
        )

        MLflowTrackingService.log_evaluation_run(
            scores=result["scores"],
            feature="employee_summary",
            evaluator_model=result["model"],
            quality_score=quality_score,
        )

        return {
            **result,
            "quality_score": quality_score,
        }