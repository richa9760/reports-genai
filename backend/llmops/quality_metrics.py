class LLMQualityMetricsService:

    REQUIRED_METRICS = [
        "relevance",
        "faithfulness",
        "completeness",
        "clarity",
    ]

    @classmethod
    def calculate_quality_score(cls, scores):
        missing_metrics = [
            metric
            for metric in cls.REQUIRED_METRICS
            if metric not in scores
        ]

        if missing_metrics:
            raise ValueError(
                f"Missing quality metrics: {missing_metrics}"
            )

        return sum(
            scores[metric]
            for metric in cls.REQUIRED_METRICS
        ) / len(cls.REQUIRED_METRICS)