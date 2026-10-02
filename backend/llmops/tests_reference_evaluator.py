from unittest import mock

from django.test import TestCase

from llmops.reference_evaluator import ReferenceBasedEvaluator


class FakeEmbeddingModel:
    def encode(self, texts):
        return [
            [1.0, 0.0, 0.0],
            [1.0, 0.5, 0.0],
        ]


class ReferenceBasedEvaluatorTests(TestCase):
    def test_evaluate_returns_rouge_and_similarity_scores(self):
        reference = (
            "Completed implementation of API validation using swagger."
        )
        generated = (
            "Completed API validation implementation using swagger tools."
        )

        with mock.patch.object(
            ReferenceBasedEvaluator,
            "_get_embedding_model",
            return_value=FakeEmbeddingModel(),
        ):
            result = ReferenceBasedEvaluator.evaluate(
                reference,
                generated,
            )

        self.assertIn("rouge1", result)
        self.assertIn("rouge2", result)
        self.assertIn("rougeL", result)
        self.assertIn("semantic_similarity", result)

        self.assertGreaterEqual(result["semantic_similarity"], -1.0)
        self.assertLessEqual(result["semantic_similarity"], 1.0)

        for metric in ["rouge1", "rouge2", "rougeL"]:
            self.assertGreaterEqual(result[metric], 0.0)
            self.assertLessEqual(result[metric], 1.0)

    def test_identical_texts_get_high_similarity(self):
        text = "The quick brown fox jumps over the lazy dog."

        with mock.patch.object(
            ReferenceBasedEvaluator,
            "_get_embedding_model",
            return_value=FakeEmbeddingModel(),
        ):
            result = ReferenceBasedEvaluator.evaluate(text, text)

        self.assertEqual(result["rouge1"], 1.0)
        self.assertEqual(result["rougeL"], 1.0)