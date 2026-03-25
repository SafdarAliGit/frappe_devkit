import os
import re
import json
import frappe
from frappe.utils import now_datetime
from frappe_devkit.utils.file_utils import get_app_path, read_file, write_file


def _get_hooks_path(app_name):
    """Find hooks.py — check package level first, then root."""
    pkg_hooks = os.path.join(get_app_path(app_name), app_name, "hooks.py")
    if os.path.exists(pkg_hooks):
        return pkg_hooks
    root_hooks = os.path.join(get_app_path(app_name), "hooks.py")
    if os.path.exists(root_hooks):
        return root_hooks
    return None


@frappe.whitelist()
def add_doc_event(app_name, doctype, event, handler_path):
    """Add a doc_events entry to the target app's hooks.py."""
    hooks_path = _get_hooks_path(app_name)
    if not hooks_path:
        return {"status": "error", "message": f"hooks.py not found for app '{app_name}'"}
    content = read_file(hooks_path)
    if handler_path in content:
        return {"status": "exists", "message": f"Handler '{handler_path}' already registered"}
    if "doc_events" not in content:
        content += f'\ndoc_events = {{\n    "{doctype}": {{\n        "{event}": "{handler_path}"\n    }}\n}}\n'
    else:
        pat = re.compile(r'(["\'])' + re.escape(doctype) + r'\1\s*:\s*\{', re.MULTILINE)
        if pat.search(content):
            content = pat.sub(lambda m: m.group(0) + f'\n        "{event}": "{handler_path}",', content, count=1)
        else:
            content = re.sub(r'(doc_events\s*=\s*\{)', lambda m: m.group(0) + f'\n    "{doctype}": {{\n        "{event}": "{handler_path}"\n    }},', content, count=1)
    write_file(hooks_path, content, overwrite=True)
    return {"status": "success", "message": f"doc_event '{event}' for '{doctype}' added to hooks.py"}


@frappe.whitelist()
def add_scheduler_event(app_name, frequency, handler_path):
    """Add a scheduler_events entry to hooks.py."""
    hooks_path = _get_hooks_path(app_name)
    if not hooks_path:
        return {"status": "error", "message": f"hooks.py not found for app '{app_name}'"}
    content = read_file(hooks_path)
    if handler_path in content:
        return {"status": "exists", "message": "Handler already registered"}
    if "scheduler_events" not in content:
        content += f'\nscheduler_events = {{\n    "{frequency}": [\n        "{handler_path}"\n    ]\n}}\n'
    else:
        pat = re.compile(r'(["\'])' + re.escape(frequency) + r'\1\s*:\s*\[', re.MULTILINE)
        if pat.search(content):
            content = pat.sub(lambda m: m.group(0) + f'\n        "{handler_path}",', content, count=1)
        else:
            content = re.sub(r'(scheduler_events\s*=\s*\{)', lambda m: m.group(0) + f'\n    "{frequency}": ["{handler_path}"],', content, count=1)
    write_file(hooks_path, content, overwrite=True)
    return {"status": "success", "message": f"Scheduler '{frequency}' -> '{handler_path}' added"}


@frappe.whitelist()
def add_fixture_filter(app_name, dt, filters):
    """Add a fixtures entry to hooks.py."""
    if isinstance(filters, str): filters = json.loads(filters)
    hooks_path = _get_hooks_path(app_name)
    if not hooks_path:
        return {"status": "error", "message": f"hooks.py not found for app '{app_name}'"}
    content      = read_file(hooks_path)
    fixture_entry = json.dumps({"dt": dt, "filters": filters})
    if fixture_entry in content:
        return {"status": "exists", "message": "Fixture filter already registered"}
    if "fixtures" not in content:
        content += f"\nfixtures = [\n    {fixture_entry}\n]\n"
    else:
        content = re.sub(r'(fixtures\s*=\s*\[)', lambda m: m.group(0) + f"\n    {fixture_entry},", content, count=1)
    write_file(hooks_path, content, overwrite=True)
    return {"status": "success", "message": f"Fixture filter for '{dt}' added to hooks.py"}


@frappe.whitelist()
def add_override_doctype_class(app_name, doctype, class_path):
    """Add override_doctype_class entry to hooks.py."""
    hooks_path = _get_hooks_path(app_name)
    if not hooks_path:
        return {"status": "error", "message": f"hooks.py not found for app '{app_name}'"}
    content = read_file(hooks_path)
    if class_path in content:
        return {"status": "exists", "message": "Override already registered"}
    if "override_doctype_class" not in content:
        content += f'\noverride_doctype_class = {{\n    "{doctype}": "{class_path}"\n}}\n'
    else:
        content = re.sub(r'(override_doctype_class\s*=\s*\{)', lambda m: m.group(0) + f'\n    "{doctype}": "{class_path}",', content, count=1)
    write_file(hooks_path, content, overwrite=True)
    return {"status": "success", "message": f"override_doctype_class for '{doctype}' added"}


@frappe.whitelist()
def add_permission_query(app_name, doctype, handler_path):
    """Add permission_query_conditions to hooks.py."""
    hooks_path = _get_hooks_path(app_name)
    if not hooks_path:
        return {"status": "error", "message": f"hooks.py not found for app '{app_name}'"}
    content = read_file(hooks_path)
    if handler_path in content:
        return {"status": "exists", "message": "Already registered"}
    if "permission_query_conditions" not in content:
        content += f'\npermission_query_conditions = {{\n    "{doctype}": "{handler_path}"\n}}\n'
    else:
        content = re.sub(r'(permission_query_conditions\s*=\s*\{)', lambda m: m.group(0) + f'\n    "{doctype}": "{handler_path}",', content, count=1)
    write_file(hooks_path, content, overwrite=True)
    return {"status": "success", "message": f"permission_query_conditions for '{doctype}' added"}


@frappe.whitelist()
def scaffold_override_file(app_name, doctype_name, events=None):
    """Scaffold a Python override file with event function stubs."""
    if isinstance(events, str): events = json.loads(events) if events else []
    events = events or ["validate", "before_save", "on_submit", "on_cancel"]

    app_path      = get_app_path(app_name)
    overrides_dir = os.path.join(app_path, app_name, "overrides")
    os.makedirs(overrides_dir, exist_ok=True)

    init_path = os.path.join(overrides_dir, "__init__.py")
    if not os.path.exists(init_path):
        write_file(init_path, "")

    file_name = doctype_name.lower().replace(" ", "_")
    file_path = os.path.join(overrides_dir, f"{file_name}.py")

    fns = "\n".join([f'''
def {e}(doc, method):
    """
    Hook: {doctype_name} - {e}
    """
    pass
''' for e in events])

    content = f"""import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate
{fns}
"""
    write_file(file_path, content, overwrite=True)
    return {"status": "success", "message": f"Override file scaffolded at {file_path}", "path": file_path}


# ─────────────────────────────────────────────────────────────────────────────
# JS OVERRIDE SCAFFOLDING
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def scaffold_doctype_js_override(
    app_name,
    module_name,
    doctype_name,
    events=None,
    link_fields=None,
    child_tables=None,
    include_list_view=1,
    overwrite=False
):
    """
    Scaffold a custom DocType JS override file inside an app's module/doctype/ folder.

    This creates a proper <doctype>.js (and optionally <doctype>_list.js) that
    overrides the standard ERPNext/Frappe behaviour for that DocType.

    Frappe loads JS files from ALL installed apps for the same DocType, so placing
    a <doctype>.js inside your app's module/doctype/<doctype>/ folder is the correct
    way to extend or override client-side behaviour without patching core.

    Parameters
    ----------
    app_name        : str   App name e.g. 'my_app'
    module_name     : str   Module name e.g. 'my_app' or 'Accounts'
    doctype_name    : str   DocType to override e.g. 'Sales Invoice'
    events          : list  frappe.ui.form.on events to stub
                            e.g. ['refresh', 'validate', 'before_save', 'on_submit']
    link_fields     : list  Link field names — each gets an onchange stub
                            e.g. ['customer', 'item_code', 'company']
    child_tables    : list  Child table info for child row event stubs
                            e.g. [{'table_field': 'items', 'trigger_field': 'item_code',
                                   'child_doctype': 'Sales Invoice Item'}]
    include_list_view: int  1 = also scaffold <doctype>_list.js
    overwrite       : bool  Overwrite existing files

    How Frappe loads JS overrides
    -----------------------------
    Frappe bundles ALL <doctype>.js files from ALL installed apps.
    Each frappe.ui.form.on() call ADDS to existing handlers — it does NOT replace them.
    So your override JS runs IN ADDITION to the standard ERPNext JS.

    To run your code AFTER the standard refresh:
        refresh: function(frm) {
            // This runs after erpnext's refresh
            frm.add_custom_button(__('My Action'), () => { ... });
        }

    To run BEFORE (e.g. to change a field before standard logic):
        before_save: function(frm) {
            frm.doc.my_field = 'value';
        }
    """
    from frappe_devkit.utils.file_utils import get_doctype_path, write_file, ensure_init_py
    from frappe_devkit.utils.validators import validate_doctype_name, validate_module_name
    import os

    validate_doctype_name(doctype_name)
    validate_module_name(module_name)

    if isinstance(events, str):
        events = json.loads(events) if events else []
    if isinstance(link_fields, str):
        link_fields = json.loads(link_fields) if link_fields else []
    if isinstance(child_tables, str):
        child_tables = json.loads(child_tables) if child_tables else []

    events       = events       or ["refresh", "validate", "before_save"]
    link_fields  = link_fields  or []
    child_tables = child_tables or []

    dt_path = get_doctype_path(app_name, module_name, doctype_name)
    os.makedirs(dt_path, exist_ok=True)
    ensure_init_py(dt_path)

    dt_folder = doctype_name.lower().replace(" ", "_")
    js_path      = os.path.join(dt_path, f"{dt_folder}.js")
    list_js_path = os.path.join(dt_path, f"{dt_folder}_list.js")

    js_content   = _generate_js_override(doctype_name, events, link_fields, child_tables)
    files_created = []

    if write_file(js_path, js_content, overwrite=overwrite):
        files_created.append(js_path)

    if int(include_list_view):
        list_js_content = _generate_list_js_override(doctype_name)
        if write_file(list_js_path, list_js_content, overwrite=overwrite):
            files_created.append(list_js_path)

    _log_js_scaffold(doctype_name, app_name, module_name, dt_path)

    return {
        "status"  : "success",
        "message" : f"JS override for '{doctype_name}' scaffolded at {dt_path}",
        "files"   : files_created,
        "note"    : (
            f"Frappe will automatically bundle {dt_folder}.js alongside ERPNext's own JS. "
            f"Run: bench build --app {app_name} after changes."
        )
    }


def _generate_js_override(doctype_name, events, link_fields, child_tables):
    """Generate the full JS override file content."""

    # ── main form events ──────────────────────────────────────────────────
    all_events = list(events)

    # Add link field onchange events
    for lf in link_fields:
        if lf not in all_events:
            all_events.append(f"__link__{lf}")

    event_blocks = []

    for ev in all_events:
        if ev.startswith("__link__"):
            field = ev[8:]
            event_blocks.append(f"""
\t{field}: function(frm) {{
\t\t// Triggered when '{field}' changes
\t\tif (!frm.doc.{field}) return;

\t\t// Example: fetch field value from linked doc
\t\t// frappe.db.get_value("{field.replace("_"," ").title()}", frm.doc.{field}, "field_name", (r) => {{
\t\t// \tif (r) frappe.model.set_value(frm.doctype, frm.docname, "target_field", r.field_name);
\t\t// }});
\t}},""")
            continue

        if ev == "setup":
            event_blocks.append(f"""
\tsetup: function(frm) {{
\t\t// Called once when form is first initialised
\t\t// Use for: frm.add_fetch(), setting query filters, custom formatters

\t\t// Example: restrict a Link field to specific values
\t\t// frm.set_query("warehouse", () => ({{ filters: {{ company: frm.doc.company }} }}));
\t}},""")

        elif ev == "refresh":
            event_blocks.append(f"""
\trefresh: function(frm) {{
\t\t// Called on every form load, reload and after save
\t\t// This runs IN ADDITION to ERPNext's standard refresh

\t\tif (frm.is_new()) {{
\t\t\t// Logic for new documents only
\t\t}}

\t\tif (frm.doc.docstatus === 1) {{
\t\t\t// Add custom buttons for submitted documents
\t\t\t// frm.add_custom_button(__("My Action"), () => {{ ... }}, __("Actions"));
\t\t}}

\t\tif (frm.doc.docstatus === 0) {{
\t\t\t// Logic for draft documents
\t\t}}
\t}},""")

        elif ev == "validate":
            event_blocks.append(f"""
\tvalidate: function(frm) {{
\t\t// Called before save — return false to cancel save
\t\t// This runs IN ADDITION to ERPNext's validate

\t\t// Example: custom validation
\t\t// if (!frm.doc.my_field) {{
\t\t// \tfrappe.throw(__("My Field is required"));
\t\t// }}
\t}},""")

        elif ev == "before_save":
            event_blocks.append(f"""
\tbefore_save: function(frm) {{
\t\t// Called just before save, after validate
\t\t// Use to set calculated field values before DB write
\t}},""")

        elif ev == "after_save":
            event_blocks.append(f"""
\tafter_save: function(frm) {{
\t\t// Called after document is saved successfully
\t}},""")

        elif ev == "on_submit":
            event_blocks.append(f"""
\ton_submit: function(frm) {{
\t\t// Called after document is submitted
\t\t// Use for: creating linked documents, sending emails, updating status
\t}},""")

        elif ev == "before_submit":
            event_blocks.append(f"""
\tbefore_submit: function(frm) {{
\t\t// Called just before submit — return false to cancel
\t\t// Use for: pre-submit validation that can't be done in validate
\t}},""")

        elif ev == "on_cancel":
            event_blocks.append(f"""
\ton_cancel: function(frm) {{
\t\t// Called after document is cancelled
\t}},""")

        elif ev == "before_cancel":
            event_blocks.append(f"""
\tbefore_cancel: function(frm) {{
\t\t// Called just before cancel — return false to prevent cancellation
\t}},""")

        elif ev == "before_load":
            event_blocks.append(f"""
\tbefore_load: function(frm) {{
\t\t// Called before the form is loaded/rendered
\t}},""")

        elif ev == "onload":
            event_blocks.append(f"""
\tonload: function(frm) {{
\t\t// Called once when the form is first loaded (not on refresh)
\t\t// Use for: one-time setup, loading custom data
\t}},""")

        elif ev == "onload_post_render":
            event_blocks.append(f"""
\tonload_post_render: function(frm) {{
\t\t// Called after form is fully rendered — safe to access DOM elements
\t}},""")

        elif ev == "after_cancel":
            event_blocks.append(f"""
\tafter_cancel: function(frm) {{
\t\t// Called after cancel completes
\t}},""")

        elif ev == "timeline_refresh":
            event_blocks.append(f"""
\ttimeline_refresh: function(frm) {{
\t\t// Called when the timeline/activity log refreshes
\t}},""")

        else:
            event_blocks.append(f"""
\t{ev}: function(frm) {{
\t\t// {ev}
\t}},""")

    events_str = "\n".join(event_blocks)

    # ── child table event blocks ──────────────────────────────────────────
    child_blocks = ""
    for ct in child_tables:
        table_field    = ct.get("table_field", "items")
        trigger_field  = ct.get("trigger_field", "item_code")
        child_doctype  = ct.get("child_doctype", f"{doctype_name} {table_field.replace('_',' ').title()}")
        extra_triggers = ct.get("extra_triggers", [])

        trigger_fns = [trigger_field] + (extra_triggers if isinstance(extra_triggers, list) else [])
        trigger_fn_strs = []

        for tf in trigger_fns:
            trigger_fn_strs.append(f"""
\t{tf}: function(frm, cdt, cdn) {{
\t\tconst row = locals[cdt][cdn];

\t\t// Example: fetch data when {tf} changes
\t\tif (!row.{tf}) return;

\t\t// frappe.call({{
\t\t// \tmethod: "frappe.client.get_value",
\t\t// \targs: {{ doctype: "{tf.replace("_"," ").title()}", name: row.{tf}, fieldname: "rate" }},
\t\t// \tcallback: (r) => {{
\t\t// \t\tif (r.message) frappe.model.set_value(cdt, cdn, "rate", r.message.rate);
\t\t// \t\tfrm.refresh_field("{table_field}");
\t\t// \t}}
\t\t// }});
\t}},""")

        child_blocks += f"""

// ── Child table: {child_doctype} ─────────────────────────────────────────
frappe.ui.form.on("{child_doctype}", {{
{"".join(trigger_fn_strs)}

\tqty: function(frm, cdt, cdn) {{
\t\tconst row = locals[cdt][cdn];
\t\tfrappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
\t\tfrm.refresh_field("{table_field}");
\t}},

\trate: function(frm, cdt, cdn) {{
\t\tconst row = locals[cdt][cdn];
\t\tfrappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
\t\tfrm.refresh_field("{table_field}");
\t}},
}});"""

    return f"""// Copyright (c) 2025, Safdar and contributors
// License: MIT
//
// JS Override: {doctype_name}
//
// HOW THIS WORKS:
// Frappe bundles ALL <doctype>.js files from ALL installed apps.
// frappe.ui.form.on() ADDS to existing handlers — it does NOT replace ERPNext's own JS.
// Your code runs IN ADDITION to standard ERPNext behaviour.
//
// After editing this file run:
//   bench build --app {doctype_name.lower().replace(" ","_").split("_")[0] or "your_app"}
//   bench --site your-site clear-cache

frappe.ui.form.on("{doctype_name}", {{
{events_str}
}});
{child_blocks}
"""


def _generate_list_js_override(doctype_name):
    """Generate a list view override JS file."""
    return f"""// Copyright (c) 2025, Safdar and contributors
// License: MIT
//
// List View Override: {doctype_name}
//
// frappe.listview_settings is a plain object — assigning to it REPLACES
// any existing settings. If ERPNext has its own listview_settings for this
// DocType, use Object.assign() to extend rather than replace:
//
//   Object.assign(frappe.listview_settings["{doctype_name}"] || {{}}, {{ ... }});
//
// Or wrap in a frappe.after_ajax hook to ensure ERPNext loads first.

frappe.listview_settings["{doctype_name}"] = Object.assign(
\tfrappe.listview_settings["{doctype_name}"] || {{}},
{{
\tadd_fields: [],

\tget_indicator: function(doc) {{
\t\t// Return [label, color, filter_string]
\t\t// Colors: red, green, blue, orange, grey, darkgrey, yellow, lightblue, purple
\t\tconst map = {{
\t\t\t"Draft"      : ["Draft",       "grey",    "status,=,Draft"],
\t\t\t"Open"       : ["Open",        "blue",    "status,=,Open"],
\t\t\t"In Progress": ["In Progress", "orange",  "status,=,In Progress"],
\t\t\t"Completed"  : ["Completed",   "green",   "status,=,Completed"],
\t\t\t"Cancelled"  : ["Cancelled",   "red",     "status,=,Cancelled"],
\t\t}};
\t\treturn map[doc.status];
\t}},

\tonload: function(listview) {{
\t\t// Called when list view loads
\t\t// listview.page.add_menu_item(__("My Action"), () => {{ ... }});
\t}},

\tbefore_render: function() {{
\t\t// Called before each list re-render
\t}},

\tformatters: {{
\t\t// Custom column formatters
\t\t// status: function(value, row, column, data) {{
\t\t// \treturn `<span class="indicator-pill ${{data.status === 'Completed' ? 'green' : 'orange'}}">${{value}}</span>`;
\t\t// }},
\t}},

\tbutton: {{
\t\tshow: function(doc) {{
\t\t\treturn doc.docstatus === 0 && doc.status === "Draft";
\t\t}},
\t\tget_label: function() {{
\t\t\treturn __("Open");
\t\t}},
\t\tget_description: function(doc) {{
\t\t\treturn __("Open {{0}}", [doc.name]);
\t\t}},
\t\taction: function(doc) {{
\t\t\tfrappe.set_route("Form", "{doctype_name}", doc.name);
\t\t}}
\t}},
}}
);
"""


def _log_js_scaffold(name, app, module, path):
    try:
        log = frappe.new_doc("DevKit Scaffold Log")
        log.action = "Hook"; log.reference = f"JS: {name}"; log.app_name = app
        log.module = module; log.file_path = path
        log.scaffolded_on = str(now_datetime())
        log.insert(ignore_permissions=True); frappe.db.commit()
    except Exception:
        pass


@frappe.whitelist()
def add_whitelist_override(app_name, original, override):
    """Add an override_whitelisted_methods entry to hooks.py."""
    hooks_path = _get_hooks_path(app_name)
    if not hooks_path:
        return {"status": "error", "message": f"hooks.py not found for app '{app_name}'"}
    content = read_file(hooks_path)
    if override in content:
        return {"status": "exists", "message": "Override already registered"}
    if "override_whitelisted_methods" not in content:
        content += f'\noverride_whitelisted_methods = {{\n    "{original}": "{override}"\n}}\n'
    else:
        content = re.sub(r'(override_whitelisted_methods\s*=\s*\{)',
            lambda m: m.group(0) + f'\n    "{original}": "{override}",', content, count=1)
    write_file(hooks_path, content, overwrite=True)
    return {"status": "success", "message": f"override_whitelisted_methods entry added to hooks.py"}
