import json
import uuid
from unittest import mock

from django.test import TestCase

from llmops.evaluation_models import LLMEvaluation
from llmops.evaluation_runner import EvaluationRunner
from llmops.evaluation_service import EvaluationResultService
from llmops.judge_service import LLMJudgeService
from llmops.models import LLMRequest
from llmops.quality_metrics import LLMQualityMetricsService


class JudgeParseScoresTests(TestCase):
    def test_valid_json_scores_are_parsed(self):
        response_text = json.dumps(
            {
                "relevance": 4,
                "faithfulness": 5,
                "completeness": 3,
                "clarity": 4,
            }
        )

        scores = LLMJudgeService.parse_scores(response_text)

        self.assertEqual(
            scores,
            {
                "relevance": 4,
                "faithfulness": 5,
                "completeness": 3,
                "clarity": 4,
            },
        )

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            LLMJudgeService.parse_scores("not-json")

    def test_missing_metric_raises(self):
        response_text = json.dumps(
            {
                "relevance": 4,
                "faithfulness": 5,
                "completeness": 3,
            }
        )

        with self.assertRaises(ValueError) as exc:
            LLMJudgeService.parse_scores(response_text)

        self.assertIn("clarity", str(exc.exception))

    def test_non_integer_score_raises(self):
        response_text = json.dumps(
            {
                "relevance": 4.5,
                "faithfulness": 5,
                "completeness": 3,
                "clarity": 4,
            }
        )

        with self.assertRaises(ValueError):
            LLMJudgeService.parse_scores(response_text)

    def test_out_of_range_score_raises(self):
        response_text = json.dumps(
            {
                "relevance": 6,
                "faithfulness": 5,
                "completeness": 3,
                "clarity": 4,
            }
        )

        with self.assertRaises(ValueError):
            LLMJudgeService.parse_scores(response_text)

    def test_zero_score_raises(self):
        response_text = json.dumps(
            {
                "relevance": 0,
                "faithfulness": 5,
                "completeness": 3,
                "clarity": 4,
            }
        )

        with self.assertRaises(ValueError):
            LLMJudgeService.parse_scores(response_text)

    def test_bool_score_is_rejected(self):
        response_text = json.dumps(
            {
                "relevance": True,
                "faithfulness": 5,
                "completeness": 3,
                "clarity": 4,
            }
        )

        with self.assertRaises(ValueError):
            LLMJudgeService.parse_scores(response_text)


class JudgeBuildPromptTests(TestCase):
    def test_prompt_includes_input_data_and_summary(self):
        prompt = LLMJudgeService.build_prompt(
            {"month": 9},
            "Generated summary text.",
        )

        self.assertIn("Generated summary text.", prompt)
        self.assertIn('"month": 9', prompt)
        self.assertIn("relevance", prompt)


class QualityMetricsTests(TestCase):
    def test_calculate_quality_score_averages_required_metrics(self):
        scores = {
            "relevance": 4,
            "faithfulness": 5,
            "completeness": 3,
            "clarity": 4,
        }

        self.assertEqual(
            LLMQualityMetricsService.calculate_quality_score(scores),
            4.0,
        )

    def test_missing_metric_raises(self):
        with self.assertRaises(ValueError) as exc:
            LLMQualityMetricsService.calculate_quality_score(
                {"relevance": 4}
            )

        self.assertIn("faithfulness", str(exc.exception))


class EvaluationResultServiceTests(TestCase):
    def test_save_reference_scores_creates_reference_rows(self):
        request_id = uuid.uuid4()
        scores = {
            "rouge1": 0.5,
            "rouge2": 0.4,
            "rougeL": 0.45,
            "semantic_similarity": 0.8,
        }

        EvaluationResultService.save_reference_scores(
            request_id=request_id,
            feature="employee_summary",
            dataset_id="employee_summary_001",
            scores=scores,
        )

        self.assertEqual(
            LLMEvaluation.objects.filter(
                evaluation_type=LLMEvaluation.EVALUATION_REFERENCE
            ).count(),
            4,
        )
        row = LLMEvaluation.objects.get(metric="rouge1")
        self.assertEqual(row.request_id, request_id)
        self.assertEqual(row.feature, "employee_summary")
        self.assertEqual(row.reference_dataset_id, "employee_summary_001")
        self.assertEqual(row.score, 0.5)

    def test_save_llm_judge_scores_creates_judge_rows(self):
        request_id = uuid.uuid4()
        scores = {
            "relevance": 4,
            "faithfulness": 5,
            "completeness": 3,
            "clarity": 4,
        }

        EvaluationResultService.save_llm_judge_scores(
            request_id=request_id,
            feature="employee_summary",
            evaluator_model="llm-x",
            scores=scores,
        )

        self.assertEqual(
            LLMEvaluation.objects.filter(
                evaluation_type=LLMEvaluation.EVALUATION_LLM_JUDGE
            ).count(),
            4,
        )
        row = LLMEvaluation.objects.get(metric="completeness")
        self.assertEqual(row.evaluator_model, "llm-x")
        self.assertEqual(row.score, 3)

    def test_save_quality_score_creates_quality_row(self):
        request_id = uuid.uuid4()

        EvaluationResultService.save_quality_score(
            request_id=request_id,
            feature="employee_summary",
            quality_score=4.25,
        )

        row = LLMEvaluation.objects.get(metric="quality_score")
        self.assertEqual(row.evaluation_type, LLMEvaluation.EVALUATION_LLM_JUDGE)
        self.assertEqual(row.score, 4.25)


class EvaluationRunnerTests(TestCase):
    def setUp(self):
        LLMRequest.objects.all().delete()
        LLMEvaluation.objects.all().delete()

    @mock.patch("llmops.evaluation_runner.MLflowTrackingService.log_evaluation_run")
    @mock.patch("llmops.evaluation_runner.LLMJudgeService.evaluate")
    def test_evaluate_employee_summary_persists_scores_and_quality(
        self, mock_evaluate, mock_log_evaluation
    ):
        mock_evaluate.return_value = {
            "request_id": uuid.uuid4(),
            "model": "llm-judge-x",
            "scores": {
                "relevance": 4,
                "faithfulness": 5,
                "completeness": 3,
                "clarity": 4,
            },
        }

        result = EvaluationRunner.evaluate_employee_summary(
            case={
                "input": {"month": 9},
                "reference_summary": "x",
            },
            generated_summary="Generated summary.",
        )

        self.assertEqual(result["quality_score"], 4.0)
        self.assertEqual(LLMEvaluation.objects.count(), 5)
        quality_row = LLMEvaluation.objects.get(metric="quality_score")
        self.assertEqual(quality_row.score, 4.0)
        mock_log_evaluation.assert_called_once()