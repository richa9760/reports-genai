from rouge_score import rouge_scorer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class ReferenceBasedEvaluator:

    _embedding_model = None

    @classmethod
    def _get_embedding_model(cls):
        if cls._embedding_model is None:
            cls._embedding_model = SentenceTransformer(
                "all-MiniLM-L6-v2"
            )

        return cls._embedding_model

    @classmethod
    def evaluate(cls, reference, generated):
        rouge = rouge_scorer.RougeScorer(
            ["rouge1", "rouge2", "rougeL"],
            use_stemmer=True,
        )

        rouge_scores = rouge.score(reference, generated)

        model = cls._get_embedding_model()

        reference_embedding = model.encode([reference])
        generated_embedding = model.encode([generated])

        semantic_score = cosine_similarity(
            reference_embedding,
            generated_embedding,
        )[0][0]

        return {
            "rouge1": rouge_scores["rouge1"].fmeasure,
            "rouge2": rouge_scores["rouge2"].fmeasure,
            "rougeL": rouge_scores["rougeL"].fmeasure,
            "semantic_similarity": float(semantic_score),
        }