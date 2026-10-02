from rest_framework import serializers

from .models import Employee, MonthlyReport, Project, ReportItem, ReportItemType


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ["id", "name", "email", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "business_group", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ReportItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportItem
        fields = ["id", "item_type", "content"]
        read_only_fields = ["id"]


class GenerateSummarySerializer(serializers.Serializer):
    """Validates the unsaved form data used to generate an AI summary.

    Generation-only: the validated payload is never persisted here.
    """

    employee_name = serializers.CharField(max_length=255)
    project_name = serializers.CharField(max_length=255)
    business_group = serializers.CharField(max_length=255)
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=1970)
    tasks = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    achievements = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    courses = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    planned_holidays = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    ideas = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class MonthlyParamsSerializer(serializers.Serializer):
    """Validates the month/year used to build a collective team report."""

    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=1970)


class QuarterlyParamsSerializer(serializers.Serializer):
    """Validates the quarter/year used to build a collective team report."""

    quarter = serializers.IntegerField(min_value=1, max_value=4)
    year = serializers.IntegerField(min_value=1970)


class MonthlyReportSerializer(serializers.ModelSerializer):
    """Flat representation used for list, create and update responses."""

    items = ReportItemSerializer(many=True, read_only=True)

    class Meta:
        model = MonthlyReport
        fields = [
            "id",
            "employee_name",
            "project_name",
            "business_group",
            "month",
            "year",
            "summary",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MonthlyReportDetailSerializer(MonthlyReportSerializer):
    """Groups items by type for the frontend.

    ``items`` is returned as an object keyed by item type so the client can
    render tasks, achievements, courses, holidays and ideas directly without
    re-grouping the records itself. All other fields are inherited unchanged.
    """

    items = serializers.SerializerMethodField()

    def get_items(self, report):
        grouped = {item_type: [] for item_type in ReportItemType.values}
        for item in report.items.all():
            grouped[item.item_type].append(
                {
                    "id": item.id,
                    "item_type": item.item_type,
                    "content": item.content,
                }
            )
        return grouped
