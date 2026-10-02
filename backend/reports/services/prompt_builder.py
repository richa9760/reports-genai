"""Builds prompts for the LLM-driven employee monthly summary feature."""
from llmops.prompt_service import PromptVersionService
from llmops.pii_sanitizer import sanitize_report_data

def _section_lines(section_name, entries):
    if not entries:
        return []
    return [f"{section_name}:"] + [f"- {entry}" for entry in entries]


def build_employee_summary_prompt(report_data):
    """Turn the current unsaved form data into a single LLM prompt."""
    report_data = sanitize_report_data(report_data)
    prompt_version = PromptVersionService.get_active_prompt(
        "employee_summary"
    )

    if not prompt_version:
        raise ValueError(
            "No active prompt configured for employee_summary."
        )

    lines = [prompt_version.prompt_template, ""]
    lines.append(f"Month: {report_data['month']}")
    lines.append(f"Year: {report_data['year']}")
    lines.append(f"Employee Name: {report_data['employee_name']}")
    lines.append(f"Project Name: {report_data['project_name']}")
    lines.append(f"Business Group: {report_data['business_group']}")
    lines.append("")

    sections = [
        ("Tasks Completed", report_data.get("tasks")),
        ("Achievements / Rewards", report_data.get("achievements")),
        ("Courses Taken", report_data.get("courses")),
        ("Planned Holidays", report_data.get("planned_holidays")),
        ("Ideas Submitted", report_data.get("ideas")),
    ]

    for name, entries in sections:
        lines.extend(_section_lines(name, entries))

    return (
    "\n".join(lines).strip(),
    prompt_version.version,
)

def build_employee_summary_prompt_for_version(report_data, version):
    report_data = sanitize_report_data(report_data)
    prompt_version = PromptVersionService.get_prompt(
        "employee_summary",
        version,
    )

    if not prompt_version:
        raise ValueError(
            f"Prompt version {version} not found for employee_summary."
        )

    lines = [prompt_version.prompt_template, ""]

    lines.append(f"Month: {report_data['month']}")
    lines.append(f"Year: {report_data['year']}")
    lines.append(f"Employee Name: {report_data['employee_name']}")
    lines.append(f"Project Name: {report_data['project_name']}")
    lines.append(f"Business Group: {report_data['business_group']}")
    lines.append("")

    sections = [
        ("Tasks Completed", report_data.get("tasks")),
        ("Achievements / Rewards", report_data.get("achievements")),
        ("Courses Taken", report_data.get("courses")),
        ("Planned Holidays", report_data.get("planned_holidays")),
        ("Ideas Submitted", report_data.get("ideas")),
    ]

    for name, entries in sections:
        lines.extend(_section_lines(name, entries))

    return "\n".join(lines).strip(), prompt_version.version