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
    naming_rule="By fieldname", autoname="", title_field="",
    search_fields="", sort_field="modified", sort_order="DESC",
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
        "actions": [], "allow_import": 1 if not is_single and not is_child_table else 0,
        "allow_rename": 1 if not is_single and not is_child_table else 0,
        "autoname": autoname, "creation": str(now_datetime()), "doctype": "DocType",
        "document_type": "", "editable_grid": editable_grid, "engine": "InnoDB",
        "field_order": field_order, "fields": built_fields,
        "hide_toolbar": 1 if is_single else 0, "in_create": 0,
        "is_submittable": is_submittable, "issingle": is_single,
        "istable": is_child_table, "is_tree": is_tree, "links": [],
        "max_attachments": 0, "modified": str(now_datetime()),
        "modified_by": "Administrator", "module": module_name,
        "name": doctype_name, "naming_rule": naming_rule,
        "owner": "Administrator", "permissions": default_perms,
        "quick_entry": quick_entry, "search_fields": search_fields,
        "sort_field": sort_field, "sort_order": sort_order, "states": [],
        "title_field": title_field, "track_changes": track_changes,
        "track_seen": track_seen, "track_views": 0,
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
                     "search_index","unique","fetch_if_empty","translatable","collapsible","columns"]:
            if flag in f: field[flag] = int(f[flag])
        for prop in ["default","depends_on","mandatory_depends_on","read_only_depends_on",
                     "description","precision","fetch_from","max_height","collapsible_depends_on","link_filters"]:
            if f.get(prop): field[prop] = f[prop]
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
from frappe.utils import flt, cint, nowdate


class {class_name}(Document):

\tdef autoname(self):
\t\tpass

\tdef before_insert(self):
\t\tpass

\tdef after_insert(self):
\t\tpass

\tdef validate(self):
\t\tpass

\tdef before_save(self):
\t\tpass

\tdef on_update(self):
\t\tpass

\tdef on_trash(self):
\t\tpass

\tdef after_delete(self):
\t\tpass

\tdef on_change(self):
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

frappe.ui.form.on("{doctype_name}", {{

\tsetup: function(frm) {{
{fetch_block}
\t}},

\trefresh: function(frm) {{
\t\tif (frm.is_new()) {{
\t\t\t// new document logic here
\t\t}}
\t}},

\tbefore_save: function(frm) {{
\t}},

\tafter_save: function(frm) {{
\t}},
{submit_block}
{events_block}

}});
"""


def _generate_list_js(doctype_name):
    return f"""// Copyright (c) 2025, Safdar and contributors
// License: MIT

frappe.listview_settings["{doctype_name}"] = {{

\tadd_fields: [],

\tget_indicator: function(doc) {{
\t\tif (doc.status === "Open")      return [__("Open"),      "blue",  "status,=,Open"];
\t\tif (doc.status === "Completed") return [__("Completed"), "green", "status,=,Completed"];
\t\tif (doc.status === "Cancelled") return [__("Cancelled"), "red",   "status,=,Cancelled"];
\t}},

\tonload: function(listview) {{
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
