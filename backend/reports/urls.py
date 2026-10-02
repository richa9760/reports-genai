from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "reports"

router = DefaultRouter()
router.register("employees", views.EmployeeViewSet)
router.register("projects", views.ProjectViewSet)
router.register("reports", views.MonthlyReportViewSet)
router.register("report-items", views.ReportItemViewSet)
router.register("manager-reports", views.ManagerReportViewSet, basename="manager-report")

urlpatterns = [
    path("health/", views.health, name="health"),
    path("", include(router.urls)),
]
