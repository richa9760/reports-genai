from llmops.evaluation_models import LLMEvaluation

class EvaluationResultService:

    @staticmethod
    def save_reference_scores(
        request_id,
        feature,
        dataset_id,
        scores,
    ):
        
        evaluations = []

        for metric, score in scores.items():
            evaluations.append(
                LLMEvaluation(
                    request_id=request_id,
                    feature=feature,
                    evaluation_type=LLMEvaluation.EVALUATION_REFERENCE,
                    metric=metric,
                    score=score,
                    reference_dataset_id=dataset_id
                )
            )

        LLMEvaluation.objects.bulk_create(evaluations)

        return evaluations
    
    @staticmethod
    def save_llm_judge_scores(
        request_id,
        feature,
        evaluator_model,
        scores,
    ):
        evaluations = []

        for metric, score in scores.items():
            evaluations.append(
                LLMEvaluation(
                    request_id=request_id,
                    feature=feature,
                    evaluation_type=LLMEvaluation.EVALUATION_LLM_JUDGE,
                    metric=metric,
                    score=score,
                    evaluator_model=evaluator_model,
                )
            )

        LLMEvaluation.objects.bulk_create(evaluations)

        return evaluations
    
    @staticmethod
    def save_quality_score(
        request_id,
        feature,
        quality_score,
        evaluator_model=None,
    ):
        return LLMEvaluation.objects.create(
            request_id=request_id,
            feature=feature,
            evaluation_type=LLMEvaluation.EVALUATION_LLM_JUDGE,
            metric="quality_score",
            score=quality_score,
            evaluator_model=evaluator_model,
        )