"""
Advanced builder APIs for Frappe DevKit Studio.
Provides: module scaffold, workspace, dashboard chart,
number card, notification, role/permission matrix,
server script, auto-email report, data import template,
doctype inspector, app health check, fixture diff.
"""
import os
import re
import json
import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe_devkit.utils.file_utils import (
    get_app_path, get_module_path, write_file, write_json,
    read_json, read_file, ensure_init_py
)


def _ensure_fixtures_in_hooks(app_name, dt, filters=None):
    """Ensure a fixtures entry for dt exists in the app's hooks.py."""
    app_path = get_app_path(app_name)
    hooks_candidates = [
        os.path.join(app_path, app_name, "hooks.py"),
        os.path.join(app_path, "hooks.py"),
    ]
    hooks_path = None
    for p in hooks_candidates:
        if os.path.exists(p):
            hooks_path = p
            break
    if not hooks_path:
        return

    content = read_file(hooks_path)
    # Build the entry string to check/add
    if filters:
        entry = json.dumps({"dt": dt, "filters": filters})
    else:
        entry = f'"{dt}"'

    if entry in content:
        return  # Already registered

    if "fixtures" not in content:
        content += f"\nfixtures = [\n    {entry}\n]\n"
    else:
        # Add inside existing fixtures list
        content = re.sub(
            r'(fixtures\s*=\s*\[)',
            lambda m: m.group(0) + f"\n    {entry},",
            content, count=1
        )
    write_file(hooks_path, content, overwrite=True)


# ─────────────────────────────────────────────────────────────────
# MODULE SCAFFOLD
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scaffold_module(app_name, module_name):
    """
    Scaffold a new Frappe module folder inside an app.
    Creates:
      <app>/<module_folder>/__init__.py
      <app>/<module_folder>/doctype/__init__.py
      <app>/<module_folder>/report/__init__.py
      <app>/<module_folder>/print_format/__init__.py
      <app>/<module_folder>/page/__init__.py
      Module Def fixture entry
    """
    app_path    = get_app_path(app_name)
    mod_folder  = module_name.lower().replace(" ", "_")
    mod_path    = os.path.join(app_path, app_name, mod_folder)

    dirs = [
        mod_path,
        os.path.join(mod_path, "doctype"),
        os.path.join(mod_path, "report"),
        os.path.join(mod_path, "print_format"),
        os.path.join(mod_path, "page"),
        os.path.join(mod_path, "workspace"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        ensure_init_py(d)

    # Add to modules.txt
    modules_txt = os.path.join(app_path, app_name, "modules.txt")
    existing    = read_file(modules_txt) if os.path.exists(modules_txt) else ""
    if module_name not in existing:
        with open(modules_txt, "a") as f:
            f.write(f"\n{module_name}")

    # Create Module Def fixture
    fixtures_dir = os.path.join(app_path, app_name, "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)
    fixture_path = os.path.join(fixtures_dir, "module_def.json")
    existing_fix = read_json(fixture_path)

    record = {
        "doctype"         : "Module Def",
        "name"            : module_name,
        "module_name"     : module_name,
        "app_name"        : app_name,
        "restrict_to_domain": "",
    }
    existing_fix = [e for e in existing_fix if e.get("name") != module_name]
    existing_fix.append(record)
    write_json(fixture_path, existing_fix, overwrite=True)

    _log_scaffold("Module", module_name, app_name, mod_path)

    # Ensure fixtures is registered in the app's hooks.py
    _ensure_fixtures_in_hooks(app_name, "Module Def", [["app_name", "=", app_name]])

    return {
        "status"  : "success",
        "message" : f"Module '{module_name}' scaffolded at {mod_path}",
        "path"    : mod_path
    }


# ─────────────────────────────────────────────────────────────────
# WORKSPACE SCAFFOLD
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scaffold_workspace(
    app_name, module_name, workspace_name,
    is_standard="Yes", roles=None,
    shortcuts=None, charts=None, number_cards=None
):
    """
    Scaffold a Frappe Desk Workspace JSON fixture.

    shortcuts     : list of {"label","link_to","type","color","icon"}
    charts        : list of {"chart_name"}
    number_cards  : list of {"card_name"}
    """
    if isinstance(roles, str):          roles = json.loads(roles) if roles else []
    if isinstance(shortcuts, str):      shortcuts = json.loads(shortcuts) if shortcuts else []
    if isinstance(charts, str):         charts = json.loads(charts) if charts else []
    if isinstance(number_cards, str):   number_cards = json.loads(number_cards) if number_cards else []

    roles         = roles or []
    shortcuts     = shortcuts or []
    charts        = charts or []
    number_cards  = number_cards or []

    app_path     = get_app_path(app_name)
    mod_folder   = module_name.lower().replace(" ", "_")
    ws_folder    = workspace_name.lower().replace(" ", "_")
    ws_dir       = os.path.join(app_path, app_name, mod_folder, "workspace", ws_folder)
    os.makedirs(ws_dir, exist_ok=True)

    ws_json = {
        "creation"        : str(now_datetime()),
        "doctype"         : "Workspace",
        "for_user"        : "",
        "hide_custom"     : 0,
        "is_hidden"       : 0,
        "label"           : workspace_name,
        "module"          : module_name,
        "name"            : workspace_name,
        "public"          : 1,
        "roles"           : [{"role": r} for r in roles],
        "sequence_id"     : 1,
        "shortcuts"       : [_build_shortcut(s) for s in shortcuts],
        "charts"          : [{"chart_name": c["chart_name"], "label": c.get("label", c["chart_name"])} for c in charts],
        "number_cards"    : [{"card_name": n["card_name"], "label": n.get("label", n["card_name"])} for n in number_cards],
        "content"         : "[]",
        "is_standard"     : is_standard,
    }

    json_path = os.path.join(ws_dir, f"{ws_folder}.json")
    write_json(json_path, ws_json, overwrite=True)

    return {
        "status"  : "success",
        "message" : f"Workspace '{workspace_name}' scaffolded at {ws_dir}",
        "path"    : json_path
    }


def _build_shortcut(s):
    return {
        "label"    : s.get("label", ""),
        "link_to"  : s.get("link_to", ""),
        "type"     : s.get("type", "DocType"),
        "color"    : s.get("color", ""),
        "icon"     : s.get("icon", ""),
        "format"   : "",
        "restrict_to_domain": "",
        "stats_filter": "",
        "url"      : "",
    }


# ─────────────────────────────────────────────────────────────────
# DASHBOARD CHART
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scaffold_dashboard_chart(
    app_name, module_name, chart_name,
    chart_type="Count", doctype="", based_on="",
    value_based_on="", group_by_based_on="", group_by_type="Count",
    filters_json="[]", time_interval="Quarterly",
    timespan="Last Year", color="#7c5cbf",
    visual_type="Bar", is_public=1
):
    """
    Scaffold a Dashboard Chart fixture JSON.

    chart_type: Count | Sum | Average | Group By
    """
    app_path    = get_app_path(app_name)
    fixtures_dir= os.path.join(app_path, app_name, "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)

    fixture_path = os.path.join(fixtures_dir, "dashboard_chart.json")
    existing     = read_json(fixture_path)

    record = {
        "doctype"          : "Dashboard Chart",
        "name"             : chart_name,
        "chart_name"       : chart_name,
        "chart_type"       : chart_type,
        "document_type"    : doctype,
        "based_on"         : based_on,
        "value_based_on"   : value_based_on,
        "group_by_based_on": group_by_based_on,
        "group_by_type"    : group_by_type,
        "filters_json"     : filters_json,
        "time_interval"    : time_interval,
        "timespan"         : timespan,
        "color"            : color,
        "is_public"        : int(is_public),
        "module"           : module_name,
        "type"             : visual_type or "Bar",
        "use_report_chart" : 0,
    }

    existing = [e for e in existing if e.get("name") != chart_name]
    existing.append(record)
    write_json(fixture_path, existing, overwrite=True)

    return {
        "status"  : "success",
        "message" : f"Dashboard Chart '{chart_name}' added to fixtures",
        "path"    : fixture_path
    }


# ─────────────────────────────────────────────────────────────────
# DASHBOARD CHART — BATCH
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scaffold_dashboard_charts_batch(app_name, module_name, charts_json):
    """
    Scaffold multiple Dashboard Charts at once.
    charts_json: list of chart dicts with chart_name, chart_type, doctype, etc.
    """
    if isinstance(charts_json, str):
        charts_json = json.loads(charts_json) if charts_json else []
    charts_json = charts_json or []

    results = []
    for c in charts_json:
        try:
            r = scaffold_dashboard_chart(
                app_name         = app_name,
                module_name      = module_name or c.get("module_name", ""),
                chart_name       = c.get("chart_name", ""),
                chart_type       = c.get("chart_type", "Count"),
                doctype          = c.get("doctype", ""),
                based_on         = c.get("based_on", ""),
                value_based_on   = c.get("value_based_on", ""),
                group_by_based_on= c.get("group_by_based_on", ""),
                group_by_type    = c.get("group_by_type", "Count"),
                filters_json     = c.get("filters_json", "[]"),
                time_interval    = c.get("time_interval", "Monthly"),
                timespan         = c.get("timespan", "Last Year"),
                color            = c.get("color", "#7c5cbf"),
                visual_type      = c.get("visual_type", "Bar"),
            )
            results.append({"name": c.get("chart_name"), "status": r.get("status")})
        except Exception as e:
            results.append({"name": c.get("chart_name"), "status": "error", "message": str(e)})

    ok  = sum(1 for r in results if r["status"] == "success")
    err = sum(1 for r in results if r["status"] != "success")
    return {
        "status" : "success",
        "message": f"{ok} chart(s) scaffolded, {err} error(s)",
        "results": results,
    }


# ─────────────────────────────────────────────────────────────────
# NUMBER CARD
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scaffold_number_card(
    app_name, module_name, card_name,
    doctype="", function="Count",
    aggregate_function_based_on="",
    filters_json="[]", color="#7c5cbf",
    is_public=1
):
    """Scaffold a Number Card fixture JSON."""
    app_path     = get_app_path(app_name)
    fixtures_dir = os.path.join(app_path, app_name, "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)

    fixture_path = os.path.join(fixtures_dir, "number_card.json")
    existing     = read_json(fixture_path)

    record = {
        "doctype"                      : "Number Card",
        "name"                         : card_name,
        "label"                        : card_name,
        "document_type"                : doctype,
        "function"                     : function,
        "aggregate_function_based_on"  : aggregate_function_based_on,
        "filters_json"                 : filters_json,
        "color"                        : color,
        "is_public"                    : int(is_public),
        "module"                       : module_name,
        "show_percentage_stats"        : 1,
        "stats_time_interval"          : "Monthly",
    }

    existing = [e for e in existing if e.get("name") != card_name]
    existing.append(record)
    write_json(fixture_path, existing, overwrite=True)

    return {
        "status"  : "success",
        "message" : f"Number Card '{card_name}' added to fixtures",
        "path"    : fixture_path
    }


# ─────────────────────────────────────────────────────────────────
# NUMBER CARD — BATCH
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scaffold_number_cards_batch(app_name, module_name, cards_json):
    """
    Scaffold multiple Number Cards at once.
    cards_json: list of card dicts with card_name, doctype, function, etc.
    """
    if isinstance(cards_json, str):
        cards_json = json.loads(cards_json) if cards_json else []
    cards_json = cards_json or []

    results = []
    for c in cards_json:
        try:
            r = scaffold_number_card(
                app_name                     = app_name,
                module_name                  = module_name or c.get("module_name", ""),
                card_name                    = c.get("card_name", ""),
                doctype                      = c.get("doctype", ""),
                function                     = c.get("function", "Count"),
                aggregate_function_based_on  = c.get("aggregate_function_based_on", ""),
                filters_json                 = c.get("filters_json", "[]"),
                color                        = c.get("color", "#5c4da8"),
            )
            results.append({"name": c.get("card_name"), "status": r.get("status")})
        except Exception as e:
            results.append({"name": c.get("card_name"), "status": "error", "message": str(e)})

    ok  = sum(1 for r in results if r["status"] == "success")
    err = sum(1 for r in results if r["status"] != "success")
    return {
        "status" : "success",
        "message": f"{ok} card(s) scaffolded, {err} error(s)",
        "results": results,
    }


# ─────────────────────────────────────────────────────────────────
# FIXTURE RECORD LISTING (app-scoped)
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def list_app_fixture_records(app_name, fixture_file):
    """
    Return records stored in an app's fixture JSON file.
    fixture_file: bare filename, e.g. 'dashboard_chart' or 'number_card'
      (with or without .json extension).
    Returns list of dicts from the JSON array, or [] if file doesn't exist.
    """
    name = fixture_file.replace(".json", "")
    path = os.path.join(get_app_path(app_name), app_name, "fixtures", f"{name}.json")
    return read_json(path)


@frappe.whitelist()
def delete_fixture_record(app_name, fixture_file, record_name):
    """
    Remove a record by name from an app's fixture JSON file.
    fixture_file: bare filename, e.g. 'dashboard_chart' (with or without .json).
    """
    name = fixture_file.replace(".json", "")
    path = os.path.join(get_app_path(app_name), app_name, "fixtures", f"{name}.json")
    records = read_json(path)
    updated = [r for r in records if r.get("name") != record_name]
    if len(updated) == len(records):
        frappe.throw(f"Record '{record_name}' not found in {name}.json")
    with open(path, "w") as f:
        json.dump(updated, f, indent="\t", default=str)


# ─────────────────────────────────────────────────────────────────
# SERVER SCRIPT
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scaffold_server_script(
    app_name, script_type, name,
    doctype="", event="",
    reference_doctype="", script=""
):
    """
    Add a Server Script to fixtures/server_script.json.

    script_type: DocType Event | Scheduler Event | API | Permission Query
    event: before_insert, validate, on_submit, etc.
    """
    app_path     = get_app_path(app_name)
    fixtures_dir = os.path.join(app_path, app_name, "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)

    fixture_path = os.path.join(fixtures_dir, "server_script.json")
    existing     = read_json(fixture_path)

    default_scripts = {
        "DocType Event": f"""# {name}
# DocType: {doctype} | Event: {event}

doc.flags.ignore_something = True
""",
        "Scheduler Event": f"""# {name}
# Runs on schedule

import frappe
frappe.db.commit()
""",
        "API": f"""# {name}
# Accessible at: /api/method/{name.lower().replace(" ","_")}

import frappe
frappe.response["message"] = {{"status": "ok"}}
""",
        "Permission Query": f"""# {name}
# Returns SQL condition string

conditions = ""
user = frappe.session.user
# conditions = f"`tab{doctype}`.owner = '{{user}}'"
""",
    }

    record = {
        "doctype"            : "Server Script",
        "name"               : name,
        "script_type"        : script_type,
        "reference_doctype"  : doctype if script_type == "DocType Event" else reference_doctype,
        "doctype_event"      : event if script_type == "DocType Event" else "",
        "script"             : script or default_scripts.get(script_type, ""),
        "disabled"           : 0,
        "allow_guest"        : 0,
    }
    if script_type == "API":
        record["api_method"] = name.lower().replace(" ", "_")

    existing = [e for e in existing if e.get("name") != name]
    existing.append(record)
    write_json(fixture_path, existing, overwrite=True)

    return {
        "status"  : "success",
        "message" : f"Server Script '{name}' added to fixtures",
        "path"    : fixture_path
    }


# ─────────────────────────────────────────────────────────────────
# NOTIFICATION
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scaffold_notification(
    app_name, notification_name, doctype,
    event="New", condition="",
    subject="", message="",
    channel="Email", send_to_all_assignees=0,
    recipients=None
):
    """
    Add a Notification fixture to fixtures/notification.json.

    event: New | Save | Submit | Cancel | Days After | Days Before | Value Change | Method | Custom
    channel: Email | System Notification | Slack | SMS
    """
    if isinstance(recipients, str): recipients = json.loads(recipients) if recipients else []
    recipients = recipients or []

    app_path     = get_app_path(app_name)
    fixtures_dir = os.path.join(app_path, app_name, "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)

    fixture_path = os.path.join(fixtures_dir, "notification.json")
    existing     = read_json(fixture_path)

    default_subject = subject or f"[{doctype}] {{{{ doc.name }}}} - {event}"
    default_message = message or f"""
<h3>{{{{ doc.name }}}}</h3>
<p>A <strong>{doctype}</strong> has been {event.lower()}d.</p>
<table>
  <tr><td><strong>Name:</strong></td><td>{{{{ doc.name }}}}</td></tr>
  <tr><td><strong>Status:</strong></td><td>{{{{ doc.status }}}}</td></tr>
</table>
<p><a href="{{{{ frappe.utils.get_url_to_form("{doctype}", doc.name) }}}}">View Document</a></p>
""".strip()

    record = {
        "doctype"               : "Notification",
        "name"                  : notification_name,
        "subject"               : default_subject,
        "document_type"         : doctype,
        "event"                 : event,
        "condition"             : condition,
        "channel"               : channel,
        "message"               : default_message,
        "send_to_all_assignees" : int(send_to_all_assignees),
        "enabled"               : 1,
        "recipients"            : recipients,
    }

    existing = [e for e in existing if e.get("name") != notification_name]
    existing.append(record)
    write_json(fixture_path, existing, overwrite=True)

    return {
        "status"  : "success",
        "message" : f"Notification '{notification_name}' added to fixtures",
        "path"    : fixture_path
    }


# ─────────────────────────────────────────────────────────────────
# ROLE & PERMISSION MATRIX — read current state
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_doctype_permissions(doctype):
    """Return the current permission matrix for a DocType."""
    try:
        meta = frappe.get_meta(doctype)
        perms = []
        for p in meta.permissions:
            perms.append({
                "role"          : p.role,
                "read"          : p.read,
                "write"         : p.write,
                "create"        : p.create,
                "delete"        : p.delete,
                "submit"        : p.submit,
                "cancel"        : p.cancel,
                "amend"         : p.amend,
                "print"         : p.print,
                "email"         : p.email,
                "export"        : p.export,
                "import"        : p.get("import", 0),
                "share"         : p.share,
                "report"        : p.report,
                "if_owner"      : p.if_owner,
            })
        return {"status": "success", "permissions": perms, "doctype": doctype}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def scaffold_role_permission(app_name, doctype, permissions):
    """
    Add Custom DocPerm records to fixtures/custom_docperm.json.

    permissions: list of {role, read, write, create, delete, submit, cancel, amend, ...}
    """
    if isinstance(permissions, str): permissions = json.loads(permissions)

    app_path     = get_app_path(app_name)
    fixtures_dir = os.path.join(app_path, app_name, "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)

    fixture_path = os.path.join(fixtures_dir, "custom_docperm.json")
    existing     = read_json(fixture_path)

    # Remove all existing perms for this doctype
    existing = [e for e in existing if e.get("parent") != doctype]

    for idx, p in enumerate(permissions):
        existing.append({
            "doctype"  : "Custom DocPerm",
            "name"     : f"{doctype}-{p['role']}-{idx}",
            "parent"   : doctype,
            "parenttype":"DocType",
            "parentfield":"permissions",
            "role"     : p.get("role",""),
            "read"     : int(p.get("read",0)),
            "write"    : int(p.get("write",0)),
            "create"   : int(p.get("create",0)),
            "delete"   : int(p.get("delete",0)),
            "submit"   : int(p.get("submit",0)),
            "cancel"   : int(p.get("cancel",0)),
            "amend"    : int(p.get("amend",0)),
            "print"    : int(p.get("print",0)),
            "email"    : int(p.get("email",0)),
            "export"   : int(p.get("export",0)),
            "share"    : int(p.get("share",0)),
            "report"   : int(p.get("report",0)),
            "if_owner" : int(p.get("if_owner",0)),
        })

    write_json(fixture_path, existing, overwrite=True)
    return {
        "status"  : "success",
        "message" : f"Permissions for '{doctype}' saved to fixtures",
        "path"    : fixture_path
    }


# ─────────────────────────────────────────────────────────────────
# DOCTYPE INSPECTOR
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def inspect_doctype(doctype):
    """
    Return full meta-information about a DocType:
    fields, permissions, links, hooks registered on it, DB table info.
    """
    try:
        meta   = frappe.get_meta(doctype)
        fields = []
        for f in meta.fields:
            fields.append({
                "fieldname"    : f.fieldname,
                "fieldtype"    : f.fieldtype,
                "label"        : f.label,
                "options"      : f.options,
                "reqd"         : f.reqd,
                "in_list_view" : f.in_list_view,
                "read_only"    : f.read_only,
                "hidden"       : f.hidden,
                "is_custom"    : f.get("is_custom_field", 0),
            })

        # Check DB columns
        db_cols = []
        try:
            db_cols = [r[0] for r in frappe.db.sql(
                f"SHOW COLUMNS FROM `tab{doctype}`"
            )]
        except Exception:
            pass

        # Find hooks registered on this doctype
        hooks_info = []
        for app in frappe.get_installed_apps():
            app_hooks = frappe.get_hooks("doc_events", app_name=app) or {}
            if doctype in app_hooks:
                for event, handlers in app_hooks[doctype].items():
                    if isinstance(handlers, str): handlers = [handlers]
                    for h in handlers:
                        hooks_info.append({"app": app, "event": event, "handler": h})

        return {
            "status"      : "success",
            "doctype"     : doctype,
            "is_single"   : meta.issingle,
            "is_child"    : meta.istable,
            "is_submittable": meta.is_submittable,
            "module"      : meta.module,
            "field_count" : len(fields),
            "fields"      : fields,
            "permissions" : [{"role": p.role, "read": p.read, "write": p.write} for p in meta.permissions],
            "db_columns"  : db_cols,
            "hooks"       : hooks_info,
            "links"       : [{"link_doctype": l.link_doctype, "link_fieldname": l.link_fieldname} for l in (meta.links or [])],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─────────────────────────────────────────────────────────────────
# APP HEALTH CHECK
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def app_health_check(app_name):
    """
    Run a health/sanity check on a Frappe app and return findings:
    - hooks.py exists and is valid
    - modules.txt entries match actual folders
    - fixtures/ JSON files are valid JSON
    - patches.txt entries exist as Python files
    - No syntax errors in Python files (py_compile)
    """
    import py_compile, traceback

    app_path = get_app_path(app_name)
    app_pkg  = os.path.join(app_path, app_name)
    results  = {"ok": [], "warn": [], "error": []}

    def ok(msg):   results["ok"].append(msg)
    def warn(msg): results["warn"].append(msg)
    def err(msg):  results["error"].append(msg)

    # 1. hooks.py
    hooks_path = os.path.join(app_pkg, "hooks.py")
    if os.path.exists(hooks_path):
        ok("hooks.py found inside package")
        try:
            py_compile.compile(hooks_path, doraise=True)
            ok("hooks.py syntax valid")
        except py_compile.PyCompileError as e:
            err(f"hooks.py syntax error: {e}")
    else:
        err("hooks.py NOT found inside package folder — Frappe will fail to load")

    # 2. modules.txt
    modules_txt = os.path.join(app_pkg, "modules.txt")
    if os.path.exists(modules_txt):
        with open(modules_txt) as f:
            modules = [l.strip() for l in f.readlines() if l.strip()]
        ok(f"modules.txt has {len(modules)} module(s): {', '.join(modules)}")
        for m in modules:
            m_folder = m.lower().replace(" ", "_")
            m_path   = os.path.join(app_pkg, m_folder)
            if os.path.isdir(m_path):
                ok(f"Module folder '{m_folder}/' exists")
            else:
                err(f"Module folder '{m_folder}/' NOT found — listed in modules.txt but missing on disk")
    else:
        warn("modules.txt not found")

    # 3. fixtures JSON
    fixtures_dir = os.path.join(app_pkg, "fixtures")
    if os.path.isdir(fixtures_dir):
        for fn in os.listdir(fixtures_dir):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(fixtures_dir, fn)) as f:
                        json.load(f)
                    ok(f"fixtures/{fn} is valid JSON ({len(json.load(open(os.path.join(fixtures_dir,fn))))} records)")
                except json.JSONDecodeError as e:
                    err(f"fixtures/{fn} is INVALID JSON: {e}")
    else:
        warn("No fixtures/ directory found")

    # 4. patches.txt
    patches_txt = os.path.join(app_pkg, "patches.txt")
    if os.path.exists(patches_txt):
        with open(patches_txt) as f:
            patches = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#")]
        for patch_line in patches:
            parts    = patch_line.split(".")
            rel_path = os.path.join(*parts[1:-1]) + ".py" if len(parts) > 2 else parts[-1] + ".py"
            full     = os.path.join(app_pkg, rel_path)
            if os.path.exists(full):
                ok(f"Patch file exists: {rel_path}")
            else:
                warn(f"Patch file missing: {rel_path} (registered in patches.txt)")

    # 5. Python syntax check on all .py files in overrides/
    overrides_dir = os.path.join(app_pkg, "overrides")
    if os.path.isdir(overrides_dir):
        for fn in os.listdir(overrides_dir):
            if fn.endswith(".py") and fn != "__init__.py":
                fp = os.path.join(overrides_dir, fn)
                try:
                    py_compile.compile(fp, doraise=True)
                    ok(f"overrides/{fn} syntax OK")
                except py_compile.PyCompileError as e:
                    err(f"overrides/{fn} syntax error: {e}")

    summary = f"✓ {len(results['ok'])} OK   ⚠ {len(results['warn'])} warnings   ✗ {len(results['error'])} errors"
    return {"status": "success", "summary": summary, "results": results}


# ─────────────────────────────────────────────────────────────────
# FIXTURE DIFF — what's in DB vs what's in fixture file
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def fixture_diff(app_name, doctype):
    """
    Compare fixture JSON file records with current DB records.
    Returns: only_in_file, only_in_db, in_both
    """
    app_path     = get_app_path(app_name)
    fixtures_dir = os.path.join(app_path, app_name, "fixtures")
    fn           = doctype.lower().replace(" ", "_") + ".json"
    fixture_path = os.path.join(fixtures_dir, fn)

    if not os.path.exists(fixture_path):
        return {"status": "error", "message": f"Fixture file not found: {fn}"}

    file_records  = read_json(fixture_path)
    file_names    = {r.get("name") for r in file_records if r.get("name")}

    try:
        db_names = {r[0] for r in frappe.db.sql(
            f"SELECT name FROM `tab{doctype}`"
        )}
    except Exception as e:
        return {"status": "error", "message": f"Could not query {doctype}: {e}"}

    only_in_file = sorted(file_names - db_names)
    only_in_db   = sorted(db_names - file_names)
    in_both      = sorted(file_names & db_names)

    return {
        "status"       : "success",
        "doctype"      : doctype,
        "fixture_file" : fixture_path,
        "only_in_file" : only_in_file,
        "only_in_db"   : only_in_db,
        "in_both"      : in_both,
        "summary"      : f"{len(in_both)} synced, {len(only_in_file)} only in file, {len(only_in_db)} only in DB"
    }


# ─────────────────────────────────────────────────────────────────
# INSTALLED APPS INFO
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_installed_apps_info():
    """Return list of installed apps with version and module counts."""
    apps = []
    for app in frappe.get_installed_apps():
        try:
            ver   = frappe.get_attr(f"{app}.__version__") or ""
        except Exception:
            ver   = ""
        try:
            mods  = frappe.db.count("Module Def", {"app_name": app})
        except Exception:
            mods  = 0
        try:
            dts   = frappe.db.count("DocType", {"module": ["in", [
                m.module_name for m in frappe.get_all("Module Def", filters={"app_name": app}, fields=["module_name"])
            ]]})
        except Exception:
            dts   = 0
        apps.append({"app": app, "version": ver, "modules": mods, "doctypes": dts})
    return {"status": "success", "apps": apps}


# ─────────────────────────────────────────────────────────────────
# GET ALL ROLES
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_all_roles():
    """Return list of all roles in the system."""
    roles = frappe.get_all("Role", fields=["name", "role_name", "disabled"],
                           filters={"disabled": 0}, order_by="name")
    return {"status": "success", "roles": [r.name for r in roles]}


# ─────────────────────────────────────────────────────────────────
# BULK CUSTOM FIELDS
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scaffold_bulk_custom_fields(app_name, fields_json):
    """
    Add multiple custom fields at once.
    fields_json: list of field dicts each with {dt, fieldname, fieldtype, label, ...}
    """
    if isinstance(fields_json, str): fields_json = json.loads(fields_json)

    from frappe_devkit.api.fixture_builder import scaffold_custom_field

    results = []
    for f in fields_json:
        try:
            r = scaffold_custom_field(
                app_name   = app_name,
                dt         = f.get("dt",""),
                fieldname  = f.get("fieldname",""),
                fieldtype  = f.get("fieldtype","Data"),
                label      = f.get("label",""),
                options    = f.get("options",""),
                insert_after = f.get("insert_after",""),
                reqd       = f.get("reqd",0),
                in_list_view = f.get("in_list_view",0),
            )
            results.append({"field": f.get("fieldname"), "status": r.get("status")})
        except Exception as e:
            results.append({"field": f.get("fieldname"), "status": "error", "message": str(e)})

    ok_count  = sum(1 for r in results if r["status"] == "success")
    err_count = sum(1 for r in results if r["status"] != "success")

    return {
        "status"  : "success",
        "message" : f"{ok_count} fields added, {err_count} errors",
        "results" : results
    }


def _log_scaffold(action, name, app_name, path, module=""):
    try:
        log = frappe.new_doc("DevKit Scaffold Log")
        log.action = action
        log.reference = name
        log.app_name = app_name
        log.module = module
        log.file_path = path
        log.scaffolded_on = str(now_datetime())
        log.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass
