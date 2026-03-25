import os
import frappe
from frappe.utils import now_datetime
from frappe_devkit.utils.file_utils import get_app_path, write_file, read_file


@frappe.whitelist()
def scaffold_patch(app_name, patch_module, description="", execute_body=""):
    """Scaffold a Frappe patch file and register it in patches.txt."""
    app_path    = get_app_path(app_name)
    app_pkg     = os.path.join(app_path, app_name)
    patches_dir = os.path.join(app_pkg, "patches")

    parts      = patch_module.split(".")
    patch_file = parts[-1]
    sub_dirs   = parts[:-1]

    patch_dir  = os.path.join(patches_dir, *sub_dirs) if sub_dirs else patches_dir
    os.makedirs(patch_dir, exist_ok=True)

    current = patches_dir
    os.makedirs(current, exist_ok=True)
    _ensure_init(current)
    for d in sub_dirs:
        current = os.path.join(current, d)
        os.makedirs(current, exist_ok=True)
        _ensure_init(current)

    patch_path  = os.path.join(patch_dir, f"{patch_file}.py")
    patches_txt = os.path.join(app_pkg, "patches.txt")

    patch_content = f"""import frappe


def execute():
    \"\"\"
    Patch: {app_name}.patches.{patch_module}
    {description}

    Runs once during bench migrate. Must be idempotent.
    \"\"\"
    # TODO: Add patch logic here

    frappe.db.commit()
"""

    write_file(patch_path, patch_content, overwrite=True)

    patch_line   = f"{app_name}.patches.{patch_module}.execute"
    patches_text = read_file(patches_txt) if os.path.exists(patches_txt) else ""
    if patch_line not in patches_text:
        with open(patches_txt, "a") as f:
            f.write(f"\n{patch_line}")

    _log("Patch", patch_module, app_name, patch_path)
    return {"status": "success", "message": f"Patch '{patch_module}' scaffolded at {patch_path}",
            "path": patch_path, "patches_txt": patches_txt}


@frappe.whitelist()
def scaffold_tasks_file(app_name):
    """Scaffold tasks.py with all scheduler frequency stubs."""
    app_pkg    = os.path.join(get_app_path(app_name), app_name)
    tasks_path = os.path.join(app_pkg, "tasks.py")
    content = """import frappe


def all():
    \"\"\"Every scheduler tick (~1 min). Keep very light.\"\"\"
    pass


def daily():
    \"\"\"Once per day.\"\"\"
    pass


def hourly():
    \"\"\"Once per hour.\"\"\"
    pass


def weekly():
    \"\"\"Once per week.\"\"\"
    pass


def monthly():
    \"\"\"Once per month.\"\"\"
    pass


def daily_long():
    \"\"\"Once per day — long-running worker.\"\"\"
    pass


def hourly_long():
    \"\"\"Once per hour — long-running worker.\"\"\"
    pass
"""
    write_file(tasks_path, content, overwrite=True)
    return {"status": "success", "message": f"tasks.py scaffolded at {tasks_path}", "path": tasks_path}


@frappe.whitelist()
def scaffold_permissions_file(app_name):
    """Scaffold permissions.py with query conditions and has_permission stubs."""
    app_pkg          = os.path.join(get_app_path(app_name), app_name)
    permissions_path = os.path.join(app_pkg, "permissions.py")
    content = f"""import frappe


def get_permission_query_conditions(user=None):
    \"\"\"
    Returns SQL WHERE condition string to restrict list view records.
    Register in hooks.py:
        permission_query_conditions = {{
            "DocType": "{app_name}.permissions.get_permission_query_conditions"
        }}
    \"\"\"
    if not user:
        user = frappe.session.user
    return ""


def has_permission(doc, ptype, user=None):
    \"\"\"
    Returns True/False for per-document access.
    Register in hooks.py:
        has_permission = {{
            "DocType": "{app_name}.permissions.has_permission"
        }}
    \"\"\"
    if not user:
        user = frappe.session.user
    return True
"""
    write_file(permissions_path, content, overwrite=True)
    return {"status": "success", "message": f"permissions.py scaffolded at {permissions_path}", "path": permissions_path}


def _ensure_init(directory):
    init_path = os.path.join(directory, "__init__.py")
    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write("")


def _log(action, name, app, path):
    try:
        log = frappe.new_doc("DevKit Scaffold Log")
        log.action = action; log.reference = name; log.app_name = app
        log.module = ""; log.file_path = path
        log.scaffolded_on = str(now_datetime())
        log.insert(ignore_permissions=True); frappe.db.commit()
    except Exception:
        pass
