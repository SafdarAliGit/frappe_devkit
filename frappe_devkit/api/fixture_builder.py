import os
import json
import subprocess
import frappe
from frappe.utils import now_datetime
from frappe_devkit.utils.file_utils import get_app_path, write_json, read_json, write_file, get_module_path


@frappe.whitelist()
def scaffold_custom_field(app_name, dt, fieldname, fieldtype, label,
    options="", insert_after="", default="", reqd=0, bold=0,
    read_only=0, hidden=0, in_list_view=0, in_standard_filter=0,
    in_global_search=0, no_copy=0, allow_on_submit=0, print_hide=0,
    report_hide=0, search_index=0, unique=0, depends_on="",
    mandatory_depends_on="", read_only_depends_on="", description="",
    fetch_from="", fetch_if_empty=0, translatable=0,
    precision="", length=0, columns=0):
    """Add a Custom Field to fixtures/custom_field.json."""
    app_path     = get_app_path(app_name)
    fixtures_dir = os.path.join(app_path, app_name, "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)
    fixture_path = os.path.join(fixtures_dir, "custom_field.json")
    existing     = read_json(fixture_path)

    record = {"doctype": "Custom Field", "name": f"{dt}-{fieldname}",
               "dt": dt, "fieldname": fieldname, "fieldtype": fieldtype, "label": label}

    if insert_after:            record["insert_after"]          = insert_after
    if options:                 record["options"]               = options
    if default:                 record["default"]               = default
    if int(reqd):               record["reqd"]                  = 1
    if int(bold):               record["bold"]                  = 1
    if int(read_only):          record["read_only"]             = 1
    if int(hidden):             record["hidden"]                = 1
    if int(in_list_view):       record["in_list_view"]          = 1
    if int(in_standard_filter): record["in_standard_filter"]    = 1
    if int(in_global_search):   record["in_global_search"]      = 1
    if int(no_copy):            record["no_copy"]               = 1
    if int(allow_on_submit):    record["allow_on_submit"]       = 1
    if int(print_hide):         record["print_hide"]            = 1
    if int(report_hide):        record["report_hide"]           = 1
    if int(search_index):       record["search_index"]          = 1
    if int(unique):             record["unique"]                = 1
    if int(fetch_if_empty):     record["fetch_if_empty"]        = 1
    if int(translatable):       record["translatable"]          = 1
    if depends_on:              record["depends_on"]            = depends_on
    if mandatory_depends_on:    record["mandatory_depends_on"]  = mandatory_depends_on
    if read_only_depends_on:    record["read_only_depends_on"]  = read_only_depends_on
    if description:             record["description"]           = description
    if fetch_from:              record["fetch_from"]            = fetch_from
    if precision:               record["precision"]             = precision
    if int(length):             record["length"]                = int(length)
    if int(columns):            record["columns"]               = int(columns)

    existing = [e for e in existing if e.get("name") != record["name"]]
    existing.append(record)
    write_json(fixture_path, existing, overwrite=True)
    _log("Custom Field", f"{dt}-{fieldname}", app_name, fixture_path)
    return {"status": "success", "message": f"Custom field '{fieldname}' added to fixtures for '{dt}'", "path": fixture_path}


@frappe.whitelist()
def scaffold_property_setter(app_name, dt, property_name, value,
    fieldname="", property_type="Data", doctype_or_field="DocField"):
    """Add a Property Setter to fixtures/property_setter.json."""
    app_path     = get_app_path(app_name)
    fixtures_dir = os.path.join(app_path, app_name, "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)
    fixture_path = os.path.join(fixtures_dir, "property_setter.json")
    existing     = read_json(fixture_path)
    record_name  = f"{dt}-{fieldname}-{property_name}" if fieldname else f"{dt}-main-{property_name}"
    record = {
        "doctype": "Property Setter", "name": record_name, "doc_type": dt,
        "field_name": fieldname, "property": property_name,
        "property_type": property_type, "value": str(value),
        "doctype_or_field": doctype_or_field, "is_system_generated": 0,
    }
    existing = [e for e in existing if e.get("name") != record_name]
    existing.append(record)
    write_json(fixture_path, existing, overwrite=True)
    _log("Property Setter", record_name, app_name, fixture_path)
    return {"status": "success", "message": f"Property Setter '{record_name}' added", "path": fixture_path}


@frappe.whitelist()
def scaffold_client_script(app_name, dt, script, script_type="Client", enabled=1, view="Form"):
    """Add a Client Script to fixtures/client_script.json."""
    app_path     = get_app_path(app_name)
    fixtures_dir = os.path.join(app_path, app_name, "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)
    fixture_path = os.path.join(fixtures_dir, "client_script.json")
    existing     = read_json(fixture_path)
    record_name  = f"{dt}-{view.lower()}-script"
    record = {"doctype": "Client Script", "name": record_name, "dt": dt,
               "script_type": script_type, "script": script, "enabled": int(enabled), "view": view}
    existing = [e for e in existing if e.get("name") != record_name]
    existing.append(record)
    write_json(fixture_path, existing, overwrite=True)
    return {"status": "success", "message": f"Client Script for '{dt}' added", "path": fixture_path}


@frappe.whitelist()
def scaffold_print_format(app_name, module_name, print_format_name, dt, html="", css="", standard="Yes"):
    """Scaffold a Print Format HTML + JSON."""
    module_path    = get_module_path(app_name, module_name)
    pf_folder_name = print_format_name.lower().replace(" ", "_")
    pf_dir         = os.path.join(module_path, "print_format", pf_folder_name)
    os.makedirs(pf_dir, exist_ok=True)
    html_path = os.path.join(pf_dir, f"{pf_folder_name}.html")
    json_path = os.path.join(pf_dir, f"{pf_folder_name}.json")
    default_html = html or f"""{{% from "templates/includes/print/macros.html" import render_field %}}
<div class="print-format">
    <h2>{{{{ doc.name }}}}</h2>
    <table class="table table-bordered">
        <thead><tr><th>Item</th><th>Qty</th><th>Rate</th><th>Amount</th></tr></thead>
        <tbody>
        {{%- for row in doc.items -%}}
            <tr><td>{{{{ row.item_code }}}}</td><td>{{{{ row.qty }}}}</td><td>{{{{ row.rate }}}}</td><td>{{{{ row.amount }}}}</td></tr>
        {{%- endfor -%}}
        </tbody>
    </table>
    <div class="text-right"><strong>Grand Total: {{{{ doc.grand_total }}}}</strong></div>
</div>"""
    pf_json = {"doctype": "Print Format", "name": print_format_name, "doc_type": dt,
                "module": module_name, "standard": standard, "custom_format": 0,
                "print_format_type": "Jinja", "html": default_html, "css": css, "disabled": 0}
    write_file(html_path, default_html, overwrite=True)
    write_json(json_path, pf_json, overwrite=True)
    return {"status": "success", "message": f"Print Format '{print_format_name}' scaffolded", "files": [html_path, json_path]}


@frappe.whitelist()
def export_fixtures(app_name):
    """Run bench export-fixtures for the given app."""
    bench_path = frappe.utils.get_bench_path()
    site       = frappe.local.site
    result = subprocess.run(["bench", "--site", site, "export-fixtures", "--app", app_name],
                             cwd=bench_path, capture_output=True, text=True)
    return {"status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout, "stderr": result.stderr}


@frappe.whitelist()
def run_migrate(site=None):
    """Run bench migrate."""
    bench_path = frappe.utils.get_bench_path()
    site       = site or frappe.local.site
    result = subprocess.run(["bench", "--site", site, "migrate"],
                             cwd=bench_path, capture_output=True, text=True)
    return {"status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout, "stderr": result.stderr}


@frappe.whitelist()
def clear_cache(site=None):
    """Run bench clear-cache."""
    bench_path = frappe.utils.get_bench_path()
    site       = site or frappe.local.site
    result = subprocess.run(["bench", "--site", site, "clear-cache"],
                             cwd=bench_path, capture_output=True, text=True)
    return {"status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout, "stderr": result.stderr}


def _log(action, name, app, path):
    try:
        _valid_actions = [
            "App", "DocType", "Report", "Module", "Workspace",
            "Custom Field", "Property Setter", "Client Script",
            "Hook", "Override", "Patch", "Print Format",
            "Server Script", "Notification", "Dashboard Chart",
            "Number Card", "Role Permission",
        ]
        log = frappe.new_doc("DevKit Scaffold Log")
        log.action = action if action in _valid_actions else "Custom Field"
        log.reference = name; log.app_name = app; log.module = ""
        log.file_path = path; log.scaffolded_on = str(now_datetime())
        log.insert(ignore_permissions=True); frappe.db.commit()
    except Exception:
        pass
