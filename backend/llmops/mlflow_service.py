import mlflow

from django.conf import settings

class MLflowTrackingService:

    @staticmethod
    def configure():
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)

        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)

    @staticmethod
    def start_run():
        MLflowTrackingService.configure()

        return mlflow.start_run()

    @staticmethod
    def end_run():
        return mlflow.end_run() 
    
    @staticmethod
    def log_parameters(
        feature,
        provider,
        model,
        prompt_version=None,
        operation=None,
    ):
        mlflow.log_params(
            {
                "feature": feature,
                "provider": provider,
                "model": model,
                "prompt_version": prompt_version or "",
                "operation": operation or "",
            }
        )

    @staticmethod
    def log_metrics(
        latency_ms=None,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        total_cost=None,
    ):
        metrics = {}

        if latency_ms is not None:
            metrics["latency_ms"] = latency_ms

        if input_tokens is not None:
            metrics["input_tokens"] = input_tokens

        if output_tokens is not None:
            metrics["output_tokens"] = output_tokens

        if total_tokens is not None:
            metrics["total_tokens"] = total_tokens

        if total_cost is not None:
            metrics["total_cost"] = float(total_cost)

        if metrics:
            mlflow.log_metrics(metrics)

    @staticmethod
    def log_tags(
        request_id=None,
        trace_id=None,
        status=None,
        error_type=None,
    ):
        tags = {}

        if request_id:
            tags["request_id"] = str(request_id)

        if trace_id:
            tags["trace_id"] = str(trace_id)

        if status:
            tags["status"] = status

        if error_type:
            tags["error_type"] = error_type

        if tags:
            mlflow.set_tags(tags)

    @staticmethod
    def log_evaluation_run(
        scores,
        feature,
        evaluator_model,
        quality_score=None,
    ):
        MLflowTrackingService.configure()

        with mlflow.start_run():
            mlflow.log_params({
                "feature": feature,
                "evaluator_model": evaluator_model,
                "evaluation_type": "llm_judge",
            })

            metrics = {
                f"evaluation_{metric}": float(score)
                for metric, score in scores.items()
            }

            if quality_score is not None:
                metrics["quality_score"] = float(quality_score)

            mlflow.log_metrics(metrics)

    @staticmethod
    def update_model_provider(provider, model):
        mlflow.log_params({
            "provider": provider,
            "model": model,
        })