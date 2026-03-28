import os
import json
import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe_devkit.utils.file_utils import get_doctype_path, write_file, write_json, ensure_init_py
from frappe_devkit.utils.validators import validate_doctype_name, validate_module_name

LAYOUT_FIELDTYPES = ("Section Break", "Column Break", "Tab Break", "Fold", "Heading", "HTML")


@frappe.whitelist()
def scaffold_doctype(app_name, module_name, doctype_name, fields,
    is_child_table=0, is_submittable=0, is_single=0, is_tree=0,
    quick_entry=0, editable_grid=1, track_changes=1, track_seen=0,
    track_views=0, allow_copy=0, allow_auto_repeat=0,
    allow_events_in_timeline=0, show_preview_popup=0,
    has_web_view=0, in_create=0,
    allow_import=None, allow_rename=None,
    naming_rule="By fieldname", autoname="", title_field="",
    search_fields="", sort_field="modified", sort_order="DESC",
    document_type="", icon="", description="", max_attachments=0, color="",
    permissions=None, overwrite=False):
    """
    Scaffold a complete Frappe DocType.

    Fields dict keys: fieldname, fieldtype, label, options, default, reqd, bold,
    in_list_view, in_standard_filter, in_global_search, no_copy, allow_on_submit,
    read_only, hidden, print_hide, report_hide, search_index, unique, depends_on,
    mandatory_depends_on, read_only_depends_on, description, precision, length,
    fetch_from, fetch_if_empty, translatable, max_height, collapsible,
    collapsible_depends_on, columns, link_filters
    """
    validate_doctype_name(doctype_name)
    validate_module_name(module_name)

    if isinstance(fields, str): fields = json.loads(fields)
    if isinstance(permissions, str): permissions = json.loads(permissions) if permissions else None

    is_child_table = int(is_child_table); is_submittable = int(is_submittable)
    is_single = int(is_single); is_tree = int(is_tree)
    quick_entry = int(quick_entry); editable_grid = int(editable_grid)
    track_changes = int(track_changes); track_seen = int(track_seen)
    track_views = int(track_views); allow_copy = int(allow_copy)
    allow_auto_repeat = int(allow_auto_repeat)
    allow_events_in_timeline = int(allow_events_in_timeline)
    show_preview_popup = int(show_preview_popup)
    has_web_view = int(has_web_view); in_create = int(in_create)
    max_attachments = int(max_attachments or 0)

    # allow_import / allow_rename: use caller value if provided, else default based on type
    _allow_import = int(allow_import) if allow_import is not None else (1 if not is_single and not is_child_table else 0)
    _allow_rename = int(allow_rename) if allow_rename is not None else (1 if not is_single and not is_child_table else 0)

    dt_path = get_doctype_path(app_name, module_name, doctype_name)
    os.makedirs(dt_path, exist_ok=True)
    ensure_init_py(dt_path)

    dt_folder_name = doctype_name.lower().replace(" ", "_")
    json_path      = os.path.join(dt_path, f"{dt_folder_name}.json")
    py_path        = os.path.join(dt_path, f"{dt_folder_name}.py")
    js_path        = os.path.join(dt_path, f"{dt_folder_name}.js")
    list_js_path   = os.path.join(dt_path, f"{dt_folder_name}_list.js")

    built_fields  = _build_fields(fields)
    field_order   = [f["fieldname"] for f in built_fields if f.get("fieldname")]
    default_perms = permissions or _default_permissions(is_submittable)

    dt_json = {
        "actions": [],
        "allow_copy": allow_copy,
        "allow_import": _allow_import,
        "allow_rename": _allow_rename,
        "allow_auto_repeat": allow_auto_repeat,
        "allow_events_in_timeline": allow_events_in_timeline,
        "autoname": autoname,
        "color": color or "",
        "creation": str(now_datetime()),
        "description": description or "",
        "doctype": "DocType",
        "document_type": document_type or "",
        "editable_grid": editable_grid,
        "engine": "InnoDB",
        "field_order": field_order,
        "fields": built_fields,
        "has_web_view": has_web_view,
        "hide_toolbar": 1 if is_single else 0,
        "icon": icon or "",
        "in_create": in_create,
        "is_submittable": is_submittable,
        "issingle": is_single,
        "istable": is_child_table,
        "is_tree": is_tree,
        "links": [],
        "max_attachments": max_attachments,
        "modified": str(now_datetime()),
        "modified_by": "Administrator",
        "module": module_name,
        "name": doctype_name,
        "naming_rule": naming_rule,
        "owner": "Administrator",
        "permissions": default_perms,
        "quick_entry": quick_entry,
        "search_fields": search_fields,
        "show_preview_popup": show_preview_popup,
        "sort_field": sort_field,
        "sort_order": sort_order,
        "states": [],
        "title_field": title_field,
        "track_changes": track_changes,
        "track_seen": track_seen,
        "track_views": track_views,
    }
    if is_tree:
        dt_json["nsm_parent_field"] = "parent_" + dt_folder_name

    files_created = []
    if write_json(json_path, dt_json, overwrite=overwrite): files_created.append(json_path)
    if write_file(py_path, _generate_controller_py(doctype_name, is_submittable, is_child_table, is_tree), overwrite=overwrite): files_created.append(py_path)
    if write_file(js_path, _generate_controller_js(doctype_name, is_submittable, is_child_table, built_fields), overwrite=overwrite): files_created.append(js_path)
    if not is_child_table and not is_single:
        if write_file(list_js_path, _generate_list_js(doctype_name), overwrite=overwrite): files_created.append(list_js_path)

    _log_scaffold("DocType", doctype_name, app_name, module_name, dt_path)
    return {"status": "success", "message": f"DocType '{doctype_name}' scaffolded at {dt_path}", "files": files_created}


def _build_fields(fields):
    built = []
    layout_counters = {}
    for idx, f in enumerate(fields):
        fieldtype = f.get("fieldtype", "Data")
        fieldname = f.get("fieldname", "")
        if not fieldname and fieldtype in LAYOUT_FIELDTYPES:
            key = fieldtype.lower().replace(" ", "_")
            layout_counters[key] = layout_counters.get(key, 0) + 1
            fieldname = f"{key}_{layout_counters[key]}"
        field = {
            "fieldname": fieldname,
            "fieldtype": fieldtype,
            "label": f.get("label", fieldname.replace("_", " ").title() if fieldname else ""),
            "idx": idx + 1
        }
        if f.get("options") is not None: field["options"] = f["options"]
        for flag in ["reqd","bold","in_list_view","in_standard_filter","in_global_search",
                     "no_copy","allow_on_submit","read_only","hidden","print_hide","report_hide",
                     "search_index","unique","fetch_if_empty","translatable","collapsible","columns",
                     "ignore_user_permissions","allow_in_quick_entry","remember_last_selected_value",
                     "ignore_xss_filter","in_preview"]:
            if flag in f: field[flag] = int(f[flag])
        for prop in ["default","depends_on","mandatory_depends_on","read_only_depends_on",
                     "hidden_depends_on","description","precision","width","fetch_from",
                     "max_height","collapsible_depends_on","link_filters"]:
            if f.get(prop): field[prop] = f[prop]
        if f.get("permlevel") is not None and int(f.get("permlevel",0)) > 0:
            field["permlevel"] = int(f["permlevel"])
        if f.get("length"): field["length"] = int(f["length"])
        built.append(field)
    return built


def _default_permissions(is_submittable):
    base = [
        {"create":1,"delete":1,"email":1,"export":1,"permlevel":0,"print":1,"read":1,"report":1,"role":"System Manager","share":1,"write":1},
        {"create":1,"delete":0,"email":1,"export":1,"permlevel":0,"print":1,"read":1,"report":1,"role":"All","share":1,"write":1}
    ]
    if is_submittable: base[0].update({"submit":1,"cancel":1,"amend":1})
    return base


def _generate_controller_py(doctype_name, is_submittable, is_child_table, is_tree):
    class_name = "".join(w.title() for w in doctype_name.split(" "))
    submit_block = ""
    if is_submittable:
        submit_block = """
\tdef before_submit(self):
\t\tpass

\tdef on_submit(self):
\t\tpass

\tdef before_cancel(self):
\t\tpass

\tdef on_cancel(self):
\t\tpass

\tdef on_update_after_submit(self):
\t\tpass
"""
    tree_block = "\n\tdef validate_one_word_name(self):\n\t\tpass\n" if is_tree else ""
    return f"""import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, nowdate, getdate, now_datetime


# ════════════════════════════════════════════════════════════════════════════════
# {doctype_name} — Controller
# ════════════════════════════════════════════════════════════════════════════════
# LIFECYCLE ORDER (happy path, no submit):
#   before_insert → validate → after_insert → before_save → on_update
#
# VALIDATION PATTERNS:
#   self.validate_unique_value()           # raises if duplicate
#   frappe.throw(_("Error msg"))           # raise with translated message
#   frappe.msgprint(_("Info msg"))         # non-blocking message
#   self.flags.ignore_validate = True      # skip validate in code
#
# FIELD ACCESS:
#   self.field_name                        # read/write any field
#   self.get("field_name")                 # safe get (returns None if missing)
#   self.set("field_name", value)          # safe set
#   self.db_get("field_name")             # read directly from DB (avoids local cache)
#
# CHILD TABLE ROWS:
#   for row in self.items: row.amount = row.qty * row.rate
#   self.append("items", {{"item_code": "ITEM-001", "qty": 1}})
#   self.set("items", [])  # clear all rows
#
# COMMON UTILITIES:
#   frappe.db.get_value("DocType", name, "field")
#   frappe.db.set_value("DocType", name, "field", value)
#   frappe.get_doc("DocType", name)
#   frappe.publish_realtime("event", payload, user=frappe.session.user)
# ════════════════════════════════════════════════════════════════════════════════


class {class_name}(Document):

\tdef autoname(self):
\t\t# Called before the document is named. Override to set self.name manually.
\t\t# Example: self.name = frappe.generate_hash(length=10)
\t\t# Example: self.name = f"{{self.series}}-{{getdate().year}}-{{self.customer[:4].upper()}}"
\t\tpass

\tdef before_insert(self):
\t\t# Called before the record is inserted for the first time.
\t\t# Good for setting computed defaults.
\t\t# Example: self.posting_date = nowdate()
\t\t# Example: self.status = "Draft"
\t\tpass

\tdef after_insert(self):
\t\t# Called after successful INSERT. Use for side-effects like sending notifications.
\t\t# Example: frappe.sendmail(recipients=[self.email], subject="Created", message="...")
\t\t# Example: frappe.publish_realtime("{doctype_name.lower().replace(' ','_')}_created",
\t\t#              {{"name": self.name}}, user=frappe.session.user)
\t\tpass

\tdef validate(self):
\t\t# Called before every save (insert + update). Add business rule checks here.
\t\t#
\t\t# ── Required field check ────────────────────────────────────────────────
\t\t# if not self.customer:
\t\t#     frappe.throw(_("Customer is required"), title=_("Validation Error"))
\t\t#
\t\t# ── Date validation ─────────────────────────────────────────────────────
\t\t# if self.end_date and self.start_date and getdate(self.end_date) < getdate(self.start_date):
\t\t#     frappe.throw(_("End Date cannot be before Start Date"))
\t\t#
\t\t# ── Unique value check ───────────────────────────────────────────────────
\t\t# existing = frappe.db.get_value("{doctype_name}", {{"email": self.email, "name": ["!=", self.name or ""]}})
\t\t# if existing:
\t\t#     frappe.throw(_("Email {{0}} is already used in {{1}}").format(self.email, existing))
\t\t#
\t\t# ── Child table aggregation ──────────────────────────────────────────────
\t\t# self.total_amount = sum(flt(row.amount) for row in self.get("items") or [])
\t\tpass

\tdef before_save(self):
\t\t# Called just before the database write (after validate).
\t\t# Use for final computed fields or audit fields.
\t\t# Example: self.last_modified_by = frappe.session.user
\t\tpass

\tdef on_update(self):
\t\t# Called after every successful save.
\t\t# Avoid heavy operations here — prefer after_insert for first-time logic.
\t\t# Example: frappe.db.set_value("Related DocType", self.ref, "status", self.status)
\t\tpass

\tdef on_trash(self):
\t\t# Called before the document is deleted. Raise an error to prevent deletion.
\t\t# Example:
\t\t# if frappe.db.count("Child DocType", {{"parent": self.name}}):
\t\t#     frappe.throw(_("Cannot delete — has linked records"))
\t\tpass

\tdef after_delete(self):
\t\t# Called after deletion. Clean up related records here.
\t\t# Example: frappe.db.delete("Log Entry", {{"ref_name": self.name}})
\t\tpass

\tdef on_change(self):
\t\t# Called whenever any field changes (even via set_value without a full save).
\t\t# Use sparingly — prefer validate or on_update for most logic.
\t\tpass
{submit_block}{tree_block}
"""


def _generate_controller_js(doctype_name, is_submittable, is_child_table, built_fields):
    fetch_lines = []
    field_events = []
    for f in built_fields:
        fieldname = f.get("fieldname", "")
        fieldtype = f.get("fieldtype", "")
        fetch_from = f.get("fetch_from", "")
        if fetch_from and "." in fetch_from:
            link_field, fetched = fetch_from.split(".", 1)
            fetch_lines.append(f'\t\tfrm.add_fetch("{link_field}", "{fetched}", "{fieldname}");')
        if fieldtype == "Link" and fieldname:
            field_events.append(f"""
\t{fieldname}: function(frm) {{
\t\t// triggered when {fieldname} changes
\t}},""")
    fetch_block = "\n".join(fetch_lines)
    events_block = "".join(field_events)
    submit_block = """
\ton_submit: function(frm) {
\t\t// called after submit
\t},

\ton_cancel: function(frm) {
\t\t// called after cancel
\t},
""" if is_submittable else ""
    return f"""// Copyright (c) 2025, Safdar and contributors
// License: MIT

// ════════════════════════════════════════════════════════════════════════════
// {doctype_name} — Client-side Form Controller
// ════════════════════════════════════════════════════════════════════════════
// COMMON PATTERNS:
//   frm.set_value("field", value)         — set a field value
//   frm.get_field("field").df.hidden = 1; frm.refresh_field("field")  — hide a field
//   frm.toggle_reqd("field", true)        — make a field required dynamically
//   frm.add_custom_button(__("Label"), fn) — add button to header
//   frm.set_indicator_formatter("field", fn) — color list view cells
//
// CALLING BACKEND:
//   frappe.call({{
//     method: "app.module.doctype.{doctype_name.lower().replace(' ','_')}.{doctype_name.lower().replace(' ','_')}.my_function",
//     args: {{ name: frm.doc.name }},
//     callback: r => {{ frm.reload_doc(); frappe.show_alert("Done", "green"); }}
//   }});
//
// CHILD TABLE:
//   frm.doc.items.forEach(row => {{ row.amount = row.qty * row.rate; }});
//   frm.refresh_field("items");
//   frappe.model.set_value(row.doctype, row.name, "field", value);
// ════════════════════════════════════════════════════════════════════════════

frappe.ui.form.on("{doctype_name}", {{

\tsetup: function(frm) {{
\t\t// Runs once when the form is first created in memory (before data loads).
\t\t// Use for add_fetch, custom filters on Link fields, and one-time setup.
{fetch_block}
\t\t// ── Custom Link field filter ──────────────────────────────────────────
\t\t// frm.set_query("item_code", function() {{
\t\t//   return {{ filters: {{ "disabled": 0, "is_stock_item": 1 }} }};
\t\t// }});
\t\t// ── Child table link filter ───────────────────────────────────────────
\t\t// frm.set_query("item_code", "items", function(doc, cdt, cdn) {{
\t\t//   return {{ filters: {{ "item_group": doc.category }} }};
\t\t// }});
\t}},

\trefresh: function(frm) {{
\t\t// Runs every time the form is rendered (load, save, submit, etc.)
\t\tif (frm.is_new()) {{
\t\t\t// First render of a new unsaved document
\t\t\t// frm.set_value("posting_date", frappe.datetime.get_today());
\t\t\t// frm.set_value("status", "Draft");
\t\t}}
\t\t// ── Show/hide fields based on state ───────────────────────────────────
\t\t// frm.toggle_display("section_files", frm.doc.status === "Open");
\t\t// ── Custom action buttons ─────────────────────────────────────────────
\t\t// if (!frm.is_new() && frm.doc.docstatus === 1) {{
\t\t//   frm.add_custom_button(__("Generate Report"), function() {{
\t\t//     frappe.call({{ method: "...", args: {{ name: frm.doc.name }},
\t\t//       callback: r => window.open(r.message.url) }});
\t\t//   }}, __("Actions"));
\t\t// }}
\t}},

\tbefore_save: function(frm) {{
\t\t// Client-side validation before the save request is sent.
\t\t// Throw to prevent saving:
\t\t// if (!frm.doc.customer) {{ frappe.throw(__("Customer is required")); }}
\t}},

\tafter_save: function(frm) {{
\t\t// Runs after a successful save response from the server.
\t\t// frappe.show_alert({{ message: __("Saved"), indicator: "green" }}, 3);
\t}},
{submit_block}
{events_block}

}});
"""


def _generate_list_js(doctype_name):
    return f"""// Copyright (c) 2025, Safdar and contributors
// License: MIT

// ════════════════════════════════════════════════════════════════════════════
// {doctype_name} — List View Settings
// ════════════════════════════════════════════════════════════════════════════
// HOW TO EXTEND:
//   add_fields  — extra fields fetched for each row (use in get_indicator / formatters)
//   get_indicator — returns [label, color, filter_string] to colorise status cells
//   formatters  — custom cell renderers: {{ fieldname: (value, df, doc) => html }}
//   button      — adds a button column: {{ show: (doc) => bool, get_label: () => str,
//                   action: (doc) => void, perm: "write" }}
//   onload      — fires once when the list loads; use to add filter shortcuts
//   refresh     — fires on every list refresh
// ════════════════════════════════════════════════════════════════════════════

frappe.listview_settings["{doctype_name}"] = {{

\t// Fetch extra fields not shown as columns but needed for indicators/formatters
\tadd_fields: [],
\t// add_fields: ["status", "grand_total", "customer"],

\t// Return a [label, color, quick-filter] tuple to show a coloured status pill.
\t// Colors: red, green, blue, orange, yellow, gray, darkgrey, purple, pink, cyan
\tget_indicator: function(doc) {{
\t\tif (doc.status === "Open")      return [__("Open"),      "blue",  "status,=,Open"];
\t\tif (doc.status === "Completed") return [__("Completed"), "green", "status,=,Completed"];
\t\tif (doc.status === "Cancelled") return [__("Cancelled"), "red",   "status,=,Cancelled"];
\t\tif (doc.docstatus === 1)        return [__("Submitted"), "blue",  "docstatus,=,1"];
\t}},

\t// ── Custom cell formatters ─────────────────────────────────────────────
\t// formatters: {{
\t//   grand_total: (value, df, doc) =>
\t//     `<span style="color:${{doc.outstanding_amount > 0 ? '#dc2626' : '#059669'}}">
\t//        ${{frappe.format(value, df)}}</span>`,
\t// }},

\t// ── Row-level action button ────────────────────────────────────────────
\t// button: {{
\t//   show: (doc) => doc.status === "Open",
\t//   get_label: () => __("Approve"),
\t//   action: (doc) => {{
\t//     frappe.call({{ method: "...", args: {{ name: doc.name }},
\t//       callback: () => cur_list.refresh() }});
\t//   }},
\t//   perm: "write",
\t// }},

\tonload: function(listview) {{
\t\t// Add sidebar filter shortcuts
\t\t// listview.filter_area.add([["status", "=", "Open"]]);
\t}},

\trefresh: function(listview) {{
\t\t// Runs on every list refresh — add custom header buttons here
\t\t// listview.page.add_inner_button(__("Export All"), () => {{ ... }});
\t}},

}};
"""


def _log_scaffold(action, name, app, module, path):
    try:
        log = frappe.new_doc("DevKit Scaffold Log")
        log.action = action; log.reference = name; log.app_name = app
        log.module = module; log.file_path = path
        log.scaffolded_on = str(now_datetime())
        log.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass
