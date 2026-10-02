import re


def sanitize_text(value):
    if not value:
        return value

    value = str(value)

    # Email addresses
    value = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[EMAIL]",
        value,
    )

    # Phone numbers
    value = re.sub(
        r"\b(?:\+?\d[\d\s().-]{8,}\d)\b",
        "[PHONE]",
        value,
    )

    return value


def sanitize_report_data(report_data):
    sanitized = dict(report_data)

    fields = [
        "employee_name",
        "project_name",
        "business_group",
    ]

    for field in fields:
        if field in sanitized:
            sanitized[field] = sanitize_text(
                sanitized[field]
            )

    list_fields = [
        "tasks",
        "achievements",
        "courses",
        "planned_holidays",
        "ideas",
    ]

    for field in list_fields:
        if field in sanitized and sanitized[field]:
            sanitized[field] = [
                sanitize_text(item)
                for item in sanitized[field]
            ]

    return sanitized