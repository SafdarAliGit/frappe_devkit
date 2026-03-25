import os
import json
import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe_devkit.utils.file_utils import get_report_path, write_file, write_json, ensure_init_py
from frappe_devkit.utils.validators import validate_module_name


@frappe.whitelist()
def scaffold_report(app_name, module_name, report_name, report_type, ref_doctype,
    is_standard="Yes", add_total_row=0, columns=None, filters=None, roles=None, overwrite=False):
    """
    Scaffold a Frappe Report.
    report_type: 'Script Report', 'Query Report', 'Report Builder'
    """
    validate_module_name(module_name)
    if isinstance(columns, str): columns = json.loads(columns) if columns else []
    if isinstance(filters, str): filters = json.loads(filters) if filters else []
    if isinstance(roles, str):   roles   = json.loads(roles) if roles else []
    columns = columns or []; filters = filters or []
    default_roles = roles or [{"role": "System Manager"}, {"role": "All"}]

    rp_path   = get_report_path(app_name, module_name, report_name)
    os.makedirs(rp_path, exist_ok=True)
    ensure_init_py(rp_path)

    rp_folder = report_name.lower().replace(" ", "_")
    json_path = os.path.join(rp_path, f"{rp_folder}.json")
    py_path   = os.path.join(rp_path, f"{rp_folder}.py")
    js_path   = os.path.join(rp_path, f"{rp_folder}.js")

    rp_json = {
        "add_total_row": int(add_total_row), "columns": [], "creation": str(now_datetime()),
        "disabled": 0, "docstatus": 0, "doctype": "Report", "filters": [],
        "is_standard": is_standard, "module": module_name, "name": report_name,
        "owner": "Administrator", "ref_doctype": ref_doctype,
        "report_type": report_type, "roles": default_roles,
    }

    files_created = []
    if write_json(json_path, rp_json, overwrite=overwrite): files_created.append(json_path)
    if write_file(js_path, _generate_report_js(report_name, filters), overwrite=overwrite): files_created.append(js_path)

    if report_type == "Script Report":
        if write_file(py_path, _generate_script_report_py(ref_doctype, columns, filters), overwrite=overwrite):
            files_created.append(py_path)
    elif report_type == "Query Report":
        if write_file(py_path, _generate_query_report_py(ref_doctype, columns), overwrite=overwrite):
            files_created.append(py_path)

    _log_scaffold(report_name, app_name, module_name, rp_path)
    return {"status": "success", "message": f"Report '{report_name}' scaffolded at {rp_path}", "files": files_created}


def _generate_report_js(report_name, filters):
    filter_lines = []
    for f in filters:
        fn = f.get("fieldname",""); label = f.get("label", fn.replace("_"," ").title())
        ft = f.get("fieldtype","Data"); options = f.get("options","")
        reqd = int(f.get("reqd",0)); default = f.get("default","")
        parts = [f'"fieldname": "{fn}"', f'"label": __("{label}")', f'"fieldtype": "{ft}"']
        if options: parts.append(f'"options": "{options}"')
        if reqd:    parts.append(f'"reqd": {reqd}')
        if default: parts.append(f'"default": "{default}"')
        filter_lines.append("\t\t{ " + ", ".join(parts) + " }")
    filters_block = ",\n".join(filter_lines)
    return f"""// Copyright (c) 2025, Safdar and contributors
// License: MIT

frappe.query_reports["{report_name}"] = {{
\t"filters": [
{filters_block}
\t],

\tformatter: function(value, row, column, data, default_formatter) {{
\t\tvalue = default_formatter(value, row, column, data);
\t\treturn value;
\t}},

\tonload: function(report) {{
\t\t// report.set_filter_value("company", frappe.defaults.get_default("company"));
\t}}
}};
"""


def _generate_script_report_py(ref_doctype, columns, filters):
    col_lines = []
    for c in columns:
        parts = [f'"label": _("{c.get("label","")}")', f'"fieldname": "{c.get("fieldname","")}"',
                 f'"fieldtype": "{c.get("fieldtype","Data")}"', f'"width": {c.get("width",120)}']
        if c.get("options"): parts.append(f'"options": "{c["options"]}"')
        col_lines.append("\t\t{ " + ", ".join(parts) + " }")
    columns_block = ",\n".join(col_lines)
    filter_vars = "\n".join([f'\t{f.get("fieldname","")} = filters.get("{f.get("fieldname","")}")' for f in filters if f.get("fieldname")]) or "\tpass"
    return f"""import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, nowdate


def execute(filters=None):
\tfilters = filters or {{}}
\tcolumns = get_columns()
\tdata    = get_data(filters)
\treturn columns, data


def get_columns():
\treturn [
{columns_block}
\t]


def get_data(filters):
{filter_vars}

\tconditions = get_conditions(filters)

\tdata = frappe.db.sql(\"\"\"
\t\tSELECT
\t\t\tt.name,
\t\t\tt.modified
\t\tFROM
\t\t\t`tab{ref_doctype}` t
\t\tWHERE
\t\t\tt.docstatus < 2
\t\t\t{{conditions}}
\t\tORDER BY
\t\t\tt.modified DESC
\t\"\"\".format(conditions=conditions), filters, as_dict=1)

\treturn data


def get_conditions(filters):
\tconditions = ""
\t# Example: if filters.get("company"): conditions += " AND t.company = %(company)s"
\treturn conditions
"""


def _generate_query_report_py(ref_doctype, columns):
    col_lines = []
    for c in columns:
        parts = [f'"label": _("{c.get("label","")}")', f'"fieldname": "{c.get("fieldname","")}"',
                 f'"fieldtype": "{c.get("fieldtype","Data")}"', f'"width": {c.get("width",120)}']
        if c.get("options"): parts.append(f'"options": "{c["options"]}"')
        col_lines.append("\t\t{ " + ", ".join(parts) + " }")
    columns_block = ",\n".join(col_lines)
    return f"""import frappe
from frappe import _


def execute(filters=None):
\tfilters = filters or {{}}
\treturn get_columns(), get_data(filters)


def get_columns():
\treturn [
{columns_block}
\t]


def get_data(filters):
\treturn frappe.db.sql(\"\"\"
\t\tSELECT t.name, t.modified
\t\tFROM `tab{ref_doctype}` t
\t\tWHERE t.docstatus < 2
\t\tORDER BY t.modified DESC
\t\"\"\", filters, as_dict=1)
"""


def _log_scaffold(name, app, module, path):
    try:
        log = frappe.new_doc("DevKit Scaffold Log")
        log.action = "Report"; log.reference = name; log.app_name = app
        log.module = module; log.file_path = path
        log.scaffolded_on = str(now_datetime())
        log.insert(ignore_permissions=True); frappe.db.commit()
    except Exception:
        pass
