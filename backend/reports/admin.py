from django.contrib import admin

from .models import Employee, MonthlyReport, Project, ReportItem


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at", "updated_at")
    search_fields = ("name", "email")
    ordering = ("name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "business_group", "created_at", "updated_at")
    search_fields = ("name", "business_group")
    list_filter = ("business_group",)
    ordering = ("business_group", "name")


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "employee_name",
        "project_name",
        "business_group",
        "month",
        "year",
        "created_at",
    )
    list_filter = ("year", "month", "business_group")
    search_fields = ("employee_name", "project_name", "summary")
    date_hierarchy = "created_at"
    ordering = ("-year", "-month")


@admin.register(ReportItem)
class ReportItemAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "item_type", "content", "created_at")
    list_filter = ("item_type",)
    search_fields = ("content", "report__employee_name")
    autocomplete_fields = ("report",)
    ordering = ("id",)
