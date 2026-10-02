from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Employee(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=255)
    business_group = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["business_group", "name"]

    def __str__(self):
        return self.name


class MonthlyReport(models.Model):
    employee_name = models.CharField(max_length=255)
    project_name = models.CharField(max_length=255)
    business_group = models.CharField(max_length=255)
    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    year = models.PositiveIntegerField(validators=[MinValueValidator(1970)])
    summary = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee_name", "project_name", "business_group", "month", "year"],
                name="unique_monthly_report_names_per_month_year",
            ),
            models.CheckConstraint(
                condition=Q(month__gte=1, month__lte=12),
                name="month_between_1_and_12",
            ),
        ]

    def __str__(self):
        return f"{self.employee_name} - {self.project_name} - {self.year}/{self.month:02d}"


class ReportItemType(models.TextChoices):
    TASK = "TASK", "Task"
    ACHIEVEMENT = "ACHIEVEMENT", "Achievement"
    COURSE = "COURSE", "Course"
    HOLIDAY = "HOLIDAY", "Holiday"
    IDEA = "IDEA", "Idea"


class ReportItem(models.Model):
    report = models.ForeignKey(
        MonthlyReport,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_type = models.CharField(max_length=20, choices=ReportItemType.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.get_item_type_display()}: {self.content[:50]}"
