from django.urls import path

from llmops.views import LLMMetricsView
from llmops.views import LLMRequestListView
from llmops.views import PromptVersionListCreateView
from llmops.views import PromptVersionActivateView
from llmops.views import LLMHealthView


urlpatterns = [
    path(
        "requests/",
        LLMRequestListView.as_view(),
        name="llm-request-list",
    ),
    path(
        "metrics/",
        LLMMetricsView.as_view(),
        name="llm-metrics",
    ),
    path(
        "prompts/",
        PromptVersionListCreateView.as_view(),
        name="prompt-version-list-create",
    ),

    path(
        "prompts/<int:pk>/activate/",
        PromptVersionActivateView.as_view(),
        name="prompt-version-activate",
    ),
    path("health/", LLMHealthView.as_view()),
]
