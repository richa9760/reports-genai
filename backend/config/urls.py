"""
URL configuration for config project.

API routes are mounted under /api/. The Django admin is available at /admin/.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("reports.urls")),
    path("api/llmops/",include("llmops.urls")),
]
