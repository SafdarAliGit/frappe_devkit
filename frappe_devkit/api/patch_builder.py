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
        indented_body = "    pass"

    patch_content = f'''import frappe


def execute():
    """
    Patch: {app_name}.patches.{patch_module}
    {description or "Describe what this patch does and why it is needed."}

    Runs once during `bench migrate`. Must be idempotent — safe to run
    multiple times without causing errors or duplicate changes.

    To re-run manually:
        bench --site <site> run-patch {app_name}.patches.{patch_module}
    """

    # ── Pattern 1: Rename / add a field value across existing records ─────────
    # frappe.db.sql("""
    #     UPDATE `tabSales Invoice`
    #     SET custom_new_field = 'Default Value'
    #     WHERE custom_new_field IS NULL OR custom_new_field = ''
    # """)

    # ── Pattern 2: Iterate and update documents (triggers hooks/validation) ───
    # for name in frappe.get_all("Customer", pluck="name"):
    #     doc = frappe.get_doc("Customer", name)
    #     doc.custom_migrated = 1
    #     doc.save(ignore_permissions=True)

    # ── Pattern 3: Idempotent column migration ────────────────────────────────
    # if not frappe.db.has_column("Sales Invoice", "custom_status"):
    #     frappe.db.add_column("Sales Invoice", "custom_status", "varchar(140)")
    #     frappe.db.sql("""
    #         UPDATE `tabSales Invoice` SET custom_status = 'Pending'
    #         WHERE custom_status IS NULL
    #     """)

    # ── Pattern 4: Rename a DocType field (safe idempotent rename) ───────────
    # frappe.rename_field("Sales Invoice", "old_field_name", "new_field_name")

    # ── Pattern 5: Delete orphaned or deprecated records ─────────────────────
    # frappe.db.delete("Old DocType", {{"status": "Deprecated"}})

    # ── Pattern 6: Move data from one field to another ────────────────────────
    # frappe.db.sql("""
    #     UPDATE `tabSales Invoice`
    #     SET new_field = old_field
    #     WHERE new_field IS NULL OR new_field = ''
    # """)

    # ── Pattern 7: Create new configuration records ───────────────────────────
    # if not frappe.db.exists("Payment Terms", "Net 30"):
    #     pt = frappe.new_doc("Payment Terms")
    #     pt.payment_terms_name = "Net 30"
    #     pt.due_date_based_on = "Day(s) after invoice date"
    #     pt.credit_days = 30
    #     pt.insert(ignore_permissions=True)

    # ── Pattern 8: Reload DocType metadata after field changes ────────────────
    # frappe.reload_doctype("Sales Invoice")
    # frappe.clear_cache(doctype="Sales Invoice")

    # ── Pattern 9: Remove deprecated Custom Field ─────────────────────────────
    # if frappe.db.exists("Custom Field", "Sales Invoice-old_custom_field"):
    #     frappe.delete_doc("Custom Field", "Sales Invoice-old_custom_field",
    #                       ignore_permissions=True)

    # ── Pattern 10: Migrate child table rows ──────────────────────────────────
    # frappe.db.sql("""
    #     UPDATE `tabSales Invoice Item`
    #     SET new_child_field = old_child_field
    #     WHERE new_child_field IS NULL
    # """)

{indented_body}

    frappe.db.commit()
'''

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
    """Scaffold tasks.py with all scheduler frequency stubs and commented usage patterns."""
    app_pkg    = os.path.join(get_app_path(app_name), app_name)
    tasks_path = os.path.join(app_pkg, "tasks.py")
    content = f'''"""
{app_name} — tasks.py
{"=" * (len(app_name) + 12)}
Scheduler entry points for all standard Frappe task frequencies.

Register in hooks.py
────────────────────
    scheduler_events = {{
        "all":          ["{app_name}.tasks.all"],
        "daily":        ["{app_name}.tasks.daily"],
        "hourly":       ["{app_name}.tasks.hourly"],
        "weekly":       ["{app_name}.tasks.weekly"],
        "monthly":      ["{app_name}.tasks.monthly"],
        "daily_long":   ["{app_name}.tasks.daily_long"],
        "hourly_long":  ["{app_name}.tasks.hourly_long"],
    }}

Or register individual functions from other modules:
    scheduler_events = {{
        "daily": [
            "{app_name}.tasks.daily",
            "{app_name}.utils.send_daily_digest",
        ],
    }}

Trigger manually during testing:
    bench --site <site> trigger-scheduler-event daily
    bench --site <site> run-tests --module {app_name}.tasks
"""

import frappe


def all():
    """
    Runs every scheduler tick (~1 minute).
    Keep this function extremely fast — it runs on every tick for ALL sites.

    Good for:
    - Checking a flag and immediately delegating to a background job
    - Very lightweight status polls
    - Updating a single in-memory cache key

    BAD — do NOT put here:
    - DB queries over large tables
    - Email sending
    - API calls to external services

    ── Patterns ──────────────────────────────────────────────────────────────
    # Check a queue flag and enqueue real work
    # if frappe.db.get_single_value("My Settings", "run_sync_now"):
    #     frappe.db.set_single_value("My Settings", "run_sync_now", 0)
    #     frappe.enqueue("{app_name}.tasks._do_sync", queue="default")

    # Heartbeat: touch a timestamp so monitoring can detect scheduler death
    # frappe.cache().set_value("scheduler_heartbeat", frappe.utils.now(), expires_in_sec=300)
    """
    pass


def daily():
    """
    Runs once every day (midnight by default).
    Register in hooks.py under scheduler_events["daily"].

    Good for:
    - Sending daily digest emails
    - Recalculating aggregated fields (totals, aging)
    - Archiving or expiring records
    - Syncing data with an external system

    ── Patterns ──────────────────────────────────────────────────────────────
    # Send a daily summary email to all System Managers
    # from {app_name}.utils.emails import send_daily_summary
    # send_daily_summary()

    # Auto-expire overdue records
    # frappe.db.sql("""
    #     UPDATE `tabMy DocType`
    #     SET status = 'Overdue'
    #     WHERE due_date < CURDATE() AND status = 'Open'
    # """)
    # frappe.db.commit()

    # Recalculate a totals field on a Settings doc
    # settings = frappe.get_single("My Settings")
    # settings.total_active_users = frappe.db.count("User", {{"enabled": 1}})
    # settings.save(ignore_permissions=True)

    # Enqueue heavy work to the long queue (does not block default queue)
    # frappe.enqueue("{app_name}.tasks._heavy_daily_job",
    #                queue="long", job_name="daily_heavy_job", deduplicate=True)
    """
    pass


def hourly():
    """
    Runs once every hour.
    Register in hooks.py under scheduler_events["hourly"].

    Good for:
    - Refreshing external API data caches
    - Sending time-sensitive alerts (SLA breach approaching)
    - Clearing stale in-progress flags
    - Triggering a lightweight sync

    ── Patterns ──────────────────────────────────────────────────────────────
    # Send SLA-breach alerts for tickets open > 4 hours
    # breach_threshold = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-4)
    # overdue = frappe.get_all(
    #     "Support Ticket",
    #     filters={{"status": "Open", "creation": ("<", breach_threshold)}},
    #     pluck="name",
    # )
    # for ticket in overdue:
    #     frappe.enqueue(
    #         "{app_name}.utils.send_sla_alert",
    #         ticket_name=ticket, queue="default",
    #     )

    # Clear stale "In Progress" flags older than 2 hours
    # stale_time = frappe.utils.add_to_date(None, hours=-2)
    # frappe.db.sql("""
    #     UPDATE `tabMy DocType`
    #     SET status = 'Pending'
    #     WHERE status = 'In Progress' AND modified < %(stale_time)s
    # """, {{"stale_time": stale_time}})
    # frappe.db.commit()
    """
    pass


def weekly():
    """
    Runs once every week (Sunday midnight by default).
    Register in hooks.py under scheduler_events["weekly"].

    Good for:
    - Sending weekly performance / activity reports
    - Purging old log files or notification records
    - Running weekly data integrity checks

    ── Patterns ──────────────────────────────────────────────────────────────
    # Delete notification logs older than 90 days
    # frappe.db.delete("Notification Log", {{
    #     "creation": ("<", frappe.utils.add_to_date(None, days=-90))
    # }})
    # frappe.db.commit()

    # Send weekly activity report to managers
    # managers = frappe.get_all("User", filters={{"role_profile_name": "Manager"}}, pluck="name")
    # for mgr in managers:
    #     frappe.enqueue(
    #         "{app_name}.utils.send_weekly_report",
    #         user=mgr, queue="default",
    #     )
    """
    pass


def monthly():
    """
    Runs once every month (1st of the month, midnight).
    Register in hooks.py under scheduler_events["monthly"].

    Good for:
    - Generating monthly invoices or statements
    - Archiving old records to a history table
    - Sending monthly summaries to management

    ── Patterns ──────────────────────────────────────────────────────────────
    # Generate monthly usage statement for each customer
    # customers = frappe.get_all("Customer", filters={{"disabled": 0}}, pluck="name")
    # for customer in customers:
    #     frappe.enqueue(
    #         "{app_name}.billing.generate_monthly_statement",
    #         customer=customer, queue="long",
    #     )

    # Archive records older than 1 year
    # cutoff = frappe.utils.add_to_date(None, years=-1)
    # old_records = frappe.get_all(
    #     "My DocType",
    #     filters={{"creation": ("<", cutoff), "status": "Closed"}},
    #     pluck="name",
    # )
    # for name in old_records:
    #     frappe.rename_doc("My DocType", name, f"ARCHIVED-{{name}}", ignore_permissions=True)
    """
    pass


def daily_long():
    """
    Same schedule as `daily()` but dispatched to the **long** worker queue.
    Use this for tasks that may take several minutes to complete.

    The long worker has a higher timeout limit and will not block
    the default queue from processing user-triggered background jobs.

    Good for:
    - Full-table data recalculations
    - Large export file generation
    - Bulk email campaigns
    - Heavy external API syncs

    ── Patterns ──────────────────────────────────────────────────────────────
    # Rebuild a heavy analytics table from raw transactions
    # from {app_name}.analytics import rebuild_monthly_summary
    # rebuild_monthly_summary()

    # Bulk-send a marketing newsletter (thousands of recipients)
    # from {app_name}.campaigns import send_campaign_emails
    # campaign = frappe.db.get_single_value("Campaign Settings", "active_campaign")
    # if campaign:
    #     send_campaign_emails(campaign)
    """
    pass


def hourly_long():
    """
    Same schedule as `hourly()` but dispatched to the **long** worker queue.
    Use for hourly tasks that may run for more than a few seconds.

    Good for:
    - Syncing a large dataset from an external API every hour
    - Processing a batch of pending records
    - Running integrity checks across multiple tables

    ── Patterns ──────────────────────────────────────────────────────────────
    # Process pending webhook deliveries (up to 500 at a time)
    # pending = frappe.get_all(
    #     "Webhook Log",
    #     filters={{"status": "Pending"}},
    #     limit=500,
    #     pluck="name",
    # )
    # for log_name in pending:
    #     frappe.enqueue(
    #         "{app_name}.webhooks.deliver",
    #         log_name=log_name, queue="default",
    #     )

    # Sync inventory levels from an external WMS every hour
    # from {app_name}.integrations.wms import sync_inventory_levels
    # sync_inventory_levels()
    """
    pass
'''
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
