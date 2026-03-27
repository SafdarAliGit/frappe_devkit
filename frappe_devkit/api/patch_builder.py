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

    body_lines = execute_body.strip().splitlines() if execute_body and execute_body.strip() else []
    if body_lines:
        indented_body = "\n".join("    " + line for line in body_lines)
    else:
        indented_body = "    # TODO: Add patch logic here"

    patch_content = f"""import frappe


def execute():
    \"\"\"
    Patch: {app_name}.patches.{patch_module}
    {description}

    Runs once during bench migrate. Must be idempotent.
    \"\"\"
{indented_body}

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
    """Scaffold permissions.py with comprehensive commented patterns for all permission scenarios."""
    app_pkg          = os.path.join(get_app_path(app_name), app_name)
    permissions_path = os.path.join(app_pkg, "permissions.py")
    content = f'''"""
{app_name} — permissions.py
================================
Centralised permission logic for all DocTypes in this app.

Register hooks in hooks.py
──────────────────────────
    # Restrict which records appear in List View / reports
    permission_query_conditions = {{
        "Sales Invoice": "{app_name}.permissions.get_permission_query_conditions",
        # "Purchase Order": "{app_name}.permissions.get_po_conditions",
    }}

    # Fine-grained per-document access (read, write, submit, cancel …)
    has_permission = {{
        "Sales Invoice": "{app_name}.permissions.has_permission",
        # "Purchase Order": "{app_name}.permissions.has_po_permission",
    }}

    # Called after a user logs in — useful for session-level guards
    # on_login = "{app_name}.permissions.on_login"

    # Restrict which roles can see each module in the sidebar
    # get_setup_wizard_stages = "{app_name}.permissions.get_setup_wizard_stages"
"""

import frappe


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_user(user=None):
    """Return the active user, defaulting to the session user."""
    return user or frappe.session.user


def _is_system_manager(user=None):
    """True when the user has the System Manager role."""
    return "System Manager" in frappe.get_roles(_get_user(user))


def _has_role(role, user=None):
    """True when the user has a specific role."""
    return role in frappe.get_roles(_get_user(user))


def _get_user_company(user=None):
    """
    Return the company linked to the Employee record for this user.
    Returns None when no Employee record exists.
    """
    # return frappe.db.get_value("Employee", {{"user_id": _get_user(user)}}, "company")
    return None


# ── permission_query_conditions ───────────────────────────────────────────────

def get_permission_query_conditions(user=None):
    """
    Return a raw SQL WHERE clause fragment that Frappe appends to every
    list / report query for this DocType.

    Return "" (empty string) to allow unrestricted access.
    Return a non-empty string to restrict visible rows.

    Register in hooks.py:
        permission_query_conditions = {{
            "Sales Invoice": "{app_name}.permissions.get_permission_query_conditions"
        }}

    ── Common patterns (uncomment as needed) ────────────────────────────────

    # 1. System Manager sees everything
    # if _is_system_manager(user):
    #     return ""

    # 2. Restrict to documents owned by the current user
    # return f"`tabSales Invoice`.`owner` = {{frappe.db.escape(user)}}"

    # 3. Restrict by a company the user belongs to
    # company = _get_user_company(user)
    # if company:
    #     return f"`tabSales Invoice`.`company` = {{frappe.db.escape(company)}}"
    # return "1=0"   # deny all if no company found

    # 4. Restrict by a role — users with the role see all, others see none
    # if _has_role("Sales Manager", user):
    #     return ""
    # return "1=0"

    # 5. Restrict by territory (field on the document)
    # territory = frappe.db.get_value("Employee", {{"user_id": user}}, "territory")
    # if territory:
    #     return f"`tabSales Invoice`.`territory` = {{frappe.db.escape(territory)}}"

    # 6. Restrict by a custom user-linked field (e.g. assigned_to = user)
    # return f"`tabSales Invoice`.`assigned_to` = {{frappe.db.escape(user)}}"

    # 7. Restrict by document status (e.g. show only submitted docs)
    # return "`tabSales Invoice`.`docstatus` = 1"

    # 8. Combine multiple conditions with AND / OR
    # cond = []
    # if _has_role("Sales Manager", user):
    #     return ""
    # cond.append(f"`tabSales Invoice`.`owner` = {{frappe.db.escape(user)}}")
    # company = _get_user_company(user)
    # if company:
    #     cond.append(f"`tabSales Invoice`.`company` = {{frappe.db.escape(company)}}")
    # return " AND ".join(cond) if cond else "1=0"
    """
    if not user:
        user = _get_user()

    # System Manager bypass — sees all records
    if _is_system_manager(user):
        return ""

    # Default: no row-level restriction
    return ""


# ── has_permission ────────────────────────────────────────────────────────────

def has_permission(doc, ptype, user=None):
    """
    Return True to ALLOW the action, False to DENY it.
    Frappe falls back to standard role-based permissions when True is returned.

    ptype values: "read", "write", "create", "delete",
                  "submit", "cancel", "amend", "print",
                  "email", "export", "share", "import"

    Register in hooks.py:
        has_permission = {{
            "Sales Invoice": "{app_name}.permissions.has_permission"
        }}

    ── Common patterns (uncomment as needed) ────────────────────────────────

    # 1. System Manager always allowed
    # if _is_system_manager(user):
    #     return True

    # 2. Owner can do everything; others only read
    # if doc.owner == user:
    #     return True
    # if ptype == "read":
    #     return True
    # return False

    # 3. Role-based: Sales Manager can submit; others cannot
    # if ptype == "submit":
    #     return _has_role("Sales Manager", user)

    # 4. Field-value guard (e.g. block delete if status is Submitted)
    # if ptype == "delete" and doc.docstatus == 1:
    #     return False

    # 5. Linked record ownership (e.g. only the assigned user can write)
    # if ptype in ("write", "submit"):
    #     return doc.get("assigned_to") == user

    # 6. Company-level isolation
    # company = _get_user_company(user)
    # if company and doc.get("company") != company:
    #     return False

    # 7. Lock document after a certain field value
    # if ptype in ("write", "cancel") and doc.get("status") == "Closed":
    #     return False

    # 8. Allow read but block export
    # if ptype == "export":
    #     return _has_role("Data Export User", user)

    # 9. Amend only if user created the original
    # if ptype == "amend":
    #     return doc.owner == user

    # 10. Custom flag on the document itself
    # if ptype == "write" and doc.get("is_locked"):
    #     return False

    # 11. Time-based: block edits after working hours
    # from frappe.utils import now_datetime
    # hour = now_datetime().hour
    # if ptype == "write" and not (8 <= hour < 18):
    #     return False

    # 12. Threshold guard: only accounts team can approve above limit
    # if ptype == "submit" and doc.get("grand_total", 0) > 100000:
    #     return _has_role("Accounts Manager", user)
    """
    if not user:
        user = _get_user()

    # System Manager bypass
    if _is_system_manager(user):
        return True

    # Default: allow — Frappe applies standard role checks on top of this
    return True


# ── on_login (optional) ───────────────────────────────────────────────────────
# Uncomment and register in hooks.py as: on_login = "{app_name}.permissions.on_login"
#
# def on_login(login_manager):
#     user = login_manager.user
#
#     # Block login for inactive employees
#     # emp = frappe.db.get_value("Employee", {{"user_id": user}}, "status")
#     # if emp and emp != "Active":
#     #     frappe.throw("Your employee account is not active.")
#
#     # Enforce 2FA for System Managers (example)
#     # if _is_system_manager(user):
#     #     pass  # add your 2FA logic here
#     pass
'''
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
