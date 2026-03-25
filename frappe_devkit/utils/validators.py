import re


def validate_app_name(name):
    if not name:
        raise ValueError("App name cannot be empty.")
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        raise ValueError(
            f"Invalid app name '{name}'. "
            "Use lowercase letters, digits, and underscores only. Must start with a letter."
        )
    return name


def validate_doctype_name(name):
    if not name:
        raise ValueError("DocType name cannot be empty.")
    if len(name.strip()) < 3:
        raise ValueError("DocType name must be at least 3 characters.")
    return name.strip()


def validate_fieldname(name):
    if not name:
        raise ValueError("Fieldname cannot be empty.")
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        raise ValueError(
            f"Invalid fieldname '{name}'. "
            "Use lowercase letters, digits, and underscores only."
        )
    return name


def validate_module_name(name):
    if not name:
        raise ValueError("Module name cannot be empty.")
    return name.strip()


def validate_report_type(report_type):
    valid = ["Query Report", "Script Report", "Report Builder", "Custom Report"]
    if report_type not in valid:
        raise ValueError(f"Invalid report_type '{report_type}'. Must be one of: {valid}")
    return report_type
