import os
import json
import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe_devkit.utils.file_utils import get_report_path, write_file, write_json, ensure_init_py
from frappe_devkit.utils.validators import validate_module_name


@frappe.whitelist()
def scaffold_report(app_name, module_name, report_name, report_type, ref_doctype,
    is_standard="Yes", add_total_row=0, columns=None, filters=None, joins=None,
    roles=None, extra_where="", order_by="", group_by="", having="",
    limit_rows=0, overwrite=False):
    """
    Scaffold a Frappe Report.
    report_type : 'Script Report', 'Query Report'
    joins       : list of {type, table, alias, on} dicts
    extra_where : raw SQL fragments appended to WHERE
    order_by    : ORDER BY clause override
    group_by    : GROUP BY clause
    having      : HAVING clause
    limit_rows  : LIMIT rows (0 = no limit)
    """
    validate_module_name(module_name)
    if isinstance(columns, str):  columns = json.loads(columns) if columns else []
    if isinstance(filters, str):  filters = json.loads(filters) if filters else []
    if isinstance(joins, str):    joins   = json.loads(joins)   if joins   else []
    if isinstance(roles, str):    roles   = json.loads(roles)   if roles   else []
    columns = columns or []; filters = filters or []; joins = joins or []
    extra_where = (extra_where or "").strip()
    order_by    = (order_by    or "").strip()
    group_by    = (group_by    or "").strip()
    having      = (having      or "").strip()
    limit_rows  = int(limit_rows) if limit_rows else 0
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

    qopts = dict(extra_where=extra_where, order_by=order_by,
                 group_by=group_by, having=having, limit_rows=limit_rows)

    files_created = []
    if write_json(json_path, rp_json, overwrite=overwrite): files_created.append(json_path)
    if write_file(js_path, _generate_report_js(report_name, filters), overwrite=overwrite): files_created.append(js_path)

    if report_type == "Script Report":
        if write_file(py_path, _generate_script_report_py(ref_doctype, columns, filters, joins, qopts), overwrite=overwrite):
            files_created.append(py_path)
    elif report_type == "Query Report":
        if write_file(py_path, _generate_query_report_py(ref_doctype, columns, joins, qopts), overwrite=overwrite):
            files_created.append(py_path)

    _log_scaffold(report_name, app_name, module_name, rp_path)
    return {"status": "success", "message": f"Report '{report_name}' scaffolded at {rp_path}", "files": files_created}


# ─────────────────────────────────────────────────────────────
#  Low-level SQL helpers
# ─────────────────────────────────────────────────────────────

def _build_join_sql(joins):
    """Return indented SQL JOIN lines."""
    lines = []
    for j in joins:
        table   = j.get("table", "").strip()
        alias   = (j.get("alias", "") or table.lower().replace(" ", "_")).strip()
        on_cond = j.get("on", "").strip()
        jtype   = j.get("type", "LEFT").strip().upper()
        if table and on_cond:
            lines.append(f"\t\t{jtype} JOIN `tab{table}` {alias} ON {on_cond}")
    return "\n".join(lines)


def _detect_primary_date_field(filters):
    """
    Guess which table field from_date/to_date should map to.
    Checks filter fieldnames for clues; falls back to posting_date.
    """
    fns = {f.get("fieldname", "") for f in filters}
    for candidate in ("posting_date", "transaction_date", "attendance_date",
                      "expense_date", "creation_date"):
        if candidate in fns:
            return candidate
    return "posting_date"


# ─────────────────────────────────────────────────────────────
#  Column block builder  (Python get_columns() body)
# ─────────────────────────────────────────────────────────────

def _build_columns_py(columns, ref_doctype):
    """
    Build the list body for get_columns().
    Each entry has an inline comment showing label, fieldtype, source alias.
    """
    if not columns:
        return (
            f'\t\t# {ref_doctype} — name\n'
            f'\t\t{{"label": _("Name"), "fieldname": "name", "fieldtype": "Link",'
            f' "options": "{ref_doctype}", "width": 180}}'
        )

    entries = []
    for c in columns:
        label = c.get("label", "")
        fn    = c.get("fieldname", "")
        ft    = c.get("fieldtype", "Data")
        w     = c.get("width", 120)
        op    = c.get("options", "")
        al    = c.get("align", "")
        ta    = (c.get("table_alias", "") or "t").strip()

        # Comment
        hint = ""
        if ft == "Link" and op:        hint = f" → {op}"
        elif ft == "Dynamic Link":     hint = " (Dynamic Link)"
        if ta != "t":                  hint += f"  [alias: {ta}]"
        comment = f"\t\t# {label}{hint}"

        # Dict
        parts = [
            f'"label": _("{label}")',
            f'"fieldname": "{fn}"',
            f'"fieldtype": "{ft}"',
            f'"width": {w}',
        ]
        if op: parts.append(f'"options": "{op}"')
        if al: parts.append(f'"align": "{al}"')

        entries.append(f"{comment}\n\t\t{{" + ", ".join(parts) + "}")

    return ",\n\n".join(entries)


# ─────────────────────────────────────────────────────────────
#  SELECT field list builder (SQL SELECT clause)
# ─────────────────────────────────────────────────────────────

def _build_select_sql(columns):
    """
    Build a SELECT field list with inline SQL comments.
    Format:  alias.fieldname,   -- Label (Type → Options)
    """
    if not columns:
        return "t.*"

    parts = []
    for c in columns:
        fn    = c.get("fieldname", "").strip()
        label = c.get("label", "")
        ft    = c.get("fieldtype", "Data")
        op    = c.get("options", "")
        ta    = (c.get("table_alias", "") or "t").strip()
        if not fn:
            continue

        field_ref = f"{ta}.{fn}"
        # SQL inline comment
        hint = ft
        if ft == "Link" and op:    hint = f"Link → {op}"
        elif ft == "Dynamic Link": hint = "Dynamic Link"
        if ta != "t":              hint += f"  [{ta}]"

        # Pad to column 46 for aligned comments
        line = f"{field_ref},"
        comment = f"-- {label}  ({hint})"
        parts.append(f"{line:<46}{comment}")

    return (",\n\t\t\t").join(parts) if parts else "t.*"


# ─────────────────────────────────────────────────────────────
#  Filter variable extraction (get_data body)
# ─────────────────────────────────────────────────────────────

def _build_filter_vars(filters):
    """
    Extract each filter value from the filters dict.
    Data/text fields get LIKE-wrapped for partial matching.
    """
    if not filters:
        return "\t# No filters defined"

    lines = []
    for f in filters:
        fn    = f.get("fieldname", "").strip()
        ft    = f.get("fieldtype", "Data")
        label = f.get("label", fn.replace("_", " ").title())
        if not fn:
            continue
        if ft in ("Data", "Small Text"):
            lines.append(
                f'\t{fn:<30} = "%%" + (filters.get("{fn}") or "") + "%%" '
                f'if filters.get("{fn}") else None  # {label}'
            )
        else:
            lines.append(f'\t{fn:<30} = filters.get("{fn}")  # {label}')

    return "\n".join(lines) if lines else "\t# No filters defined"


# ─────────────────────────────────────────────────────────────
#  Conditions builder (get_conditions() body)
# ─────────────────────────────────────────────────────────────

def _build_conditions_py(filters):
    """
    Build get_conditions() body.
    Every condition block is emitted in commented form — uncomment what you need.
    Labels and type hints are visible as plain comments above each block.
    Data fields use LIKE; from_date/to_date map to the primary date field.
    """
    if not filters:
        return "\tpass  # add conditions here"

    date_field = _detect_primary_date_field(filters)
    lines = []

    for f in filters:
        fn    = f.get("fieldname", "").strip()
        ft    = f.get("fieldtype", "Data")
        label = f.get("label", fn.replace("_", " ").title())
        op    = f.get("options", "")
        if not fn:
            continue

        # from_date / to_date handled after the loop
        if fn in ("from_date", "to_date"):
            continue

        lines.append("")  # blank line for readability

        if ft == "Link":
            hint = f" → {op}" if op else ""
            lines.append(f"\t# {label}  (Link{hint})")
            lines.append(f'\t# if filters.get("{fn}"):\n\t# \tconditions += " AND t.{fn} = %({fn})s"')

        elif ft == "Select":
            lines.append(f"\t# {label}  (Select)")
            lines.append(f'\t# if filters.get("{fn}"):\n\t# \tconditions += " AND t.{fn} = %({fn})s"')

        elif ft in ("Data", "Small Text"):
            lines.append(f"\t# {label}  (Data — LIKE partial match)")
            lines.append(f'\t# if filters.get("{fn}"):\n\t# \tconditions += " AND t.{fn} LIKE %({fn})s"')

        elif ft in ("Date", "Datetime"):
            lines.append(f"\t# {label}  ({ft})")
            lines.append(f'\t# if filters.get("{fn}"):\n\t# \tconditions += " AND t.{fn} = %({fn})s"')

        elif ft in ("Currency", "Float", "Int", "Percent"):
            lines.append(f"\t# {label}  ({ft})")
            lines.append(f'\t# if filters.get("{fn}"):\n\t# \tconditions += " AND t.{fn} = %({fn})s"')

        elif ft == "Check":
            lines.append(f"\t# {label}  (Check — 0 or 1)")
            lines.append(f'\t# if filters.get("{fn}") not in (None, ""):\n\t# \tconditions += " AND t.{fn} = %({fn})s"')

        else:
            lines.append(f"\t# {label}  ({ft})")
            lines.append(f'\t# if filters.get("{fn}"):\n\t# \tconditions += " AND t.{fn} = %({fn})s"')

    # Date range pair
    has_from = any(f.get("fieldname") == "from_date" for f in filters)
    has_to   = any(f.get("fieldname") == "to_date"   for f in filters)
    if has_from or has_to:
        lines.append(f"\n\t# ── Date range → maps to t.{date_field}")
        if has_from:
            lines.append(f'\t# if filters.get("from_date"):\n\t# \tconditions += " AND t.{date_field} >= %(from_date)s"')
        if has_to:
            lines.append(f'\t# if filters.get("to_date"):\n\t# \tconditions += " AND t.{date_field} <= %(to_date)s"')

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
#  JS filter file
# ─────────────────────────────────────────────────────────────

def _generate_report_js(report_name, filters):
    """
    Generate the .js filter file.
    Each filter has an inline comment showing its purpose.
    """
    filter_lines = []
    for f in filters:
        fn      = f.get("fieldname", "")
        label   = f.get("label", fn.replace("_", " ").title())
        ft      = f.get("fieldtype", "Data")
        options = f.get("options", "")
        reqd    = int(f.get("reqd", 0))
        default = f.get("default", "")

        # Comment above each filter
        req_note = "required" if reqd else "optional"
        type_note = ft
        if ft == "Link" and options:  type_note = f"Link → {options}"
        elif ft == "Select":          type_note = "Select"
        filter_lines.append(f"\t\t// ── {label}  ({req_note} | {type_note})")

        # Dict
        parts = [f'"fieldname": "{fn}"', f'"label": __("{label}")', f'"fieldtype": "{ft}"']
        if options: parts.append(f'"options": "{options}"')
        if reqd:    parts.append(f'"reqd": {reqd}')
        if default: parts.append(f'"default": "{default}"')
        filter_lines.append("\t\t{ " + ", ".join(parts) + " },")

    filters_block = "\n".join(filter_lines)

    return f"""// Copyright (c) {now_datetime().year}, DevKit and contributors
// License: MIT

frappe.query_reports["{report_name}"] = {{
\t"filters": [
{filters_block}
\t],

\t// ── Formatter: colour cells, add icons, bold key rows etc.
\tformatter: function(value, row, column, data, default_formatter) {{
\t\tvalue = default_formatter(value, row, column, data);
\t\t// Example: highlight negative values in red
\t\t// if (column.fieldname === "outstanding_amount" && data && data.outstanding_amount < 0)
\t\t//\t return "<span style='color:red'>" + value + "</span>";
\t\treturn value;
\t}},

\t// ── Onload: set default filter values
\tonload: function(report) {{
\t\t// report.set_filter_value("company", frappe.defaults.get_default("company"));
\t\t// report.set_filter_value("from_date", frappe.datetime.month_start());
\t\t// report.set_filter_value("to_date",   frappe.datetime.month_end());
\t}}
}};
"""


# ─────────────────────────────────────────────────────────────
#  Script Report Python stub
# ─────────────────────────────────────────────────────────────

def _generate_script_report_py(ref_doctype, columns, filters, joins=None, qopts=None):
    joins  = joins  or []
    qopts  = qopts  or {}

    extra_where = qopts.get("extra_where", "").strip()
    order_by    = qopts.get("order_by",    "").strip()
    group_by    = qopts.get("group_by",    "").strip()
    having      = qopts.get("having",      "").strip()
    limit_rows  = int(qopts.get("limit_rows", 0) or 0)

    columns_block   = _build_columns_py(columns, ref_doctype)
    filter_vars     = _build_filter_vars(filters)
    join_sql        = _build_join_sql(joins)
    join_block      = ("\n" + join_sql) if join_sql else ""
    select_sql      = _build_select_sql(columns)
    conditions_body = _build_conditions_py(filters)

    # Join alias summary
    join_note = ""
    if joins:
        aliases = [j.get("alias") or j.get("table", "").lower().replace(" ", "_") for j in joins if j.get("table")]
        join_note = "\n\t# Joined table aliases: " + ", ".join(aliases) + "\n"

    # Optional SQL clauses
    extra_where_block = f"\n\t\t\t\t{extra_where}"    if extra_where else ""
    group_block       = f"\n\t\tGROUP BY\n\t\t\t{group_by}"  if group_by  else ""
    having_block      = f"\n\t\tHAVING\n\t\t\t{having}"      if having    else ""
    order_block       = f"\n\t\tORDER BY\n\t\t\t{order_by}"  if order_by  else "\n\t\tORDER BY\n\t\t\tt.modified DESC"
    limit_block       = f"\n\t\tLIMIT {limit_rows}"           if limit_rows else ""

    return f"""import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, nowdate


def execute(filters=None):
\tfilters = filters or {{}}
\tcolumns = get_columns()
\tdata    = get_data(filters)
\treturn columns, data


# ── Columns ─────────────────────────────────────────────────
# Remove, reorder, or edit any entry below.
# fieldtype options: Data, Link, Currency, Float, Int, Date,
#   Datetime, Select, Check, Percent, Dynamic Link, Small Text
def get_columns():
\treturn [

{columns_block}

\t]


# ── Data ─────────────────────────────────────────────────────
def get_data(filters):
\t# ── Extract filter values ──────────────────────────────────
{filter_vars}

\tconditions = get_conditions(filters)
{join_note}
\tdata = frappe.db.sql(\"\"\"
\t\tSELECT
\t\t\t{select_sql}
\t\tFROM
\t\t\t`tab{ref_doctype}` t{join_block}
\t\tWHERE
\t\t\tt.docstatus < 2
\t\t\t{{conditions}}{extra_where_block}{group_block}{having_block}{order_block}{limit_block}
\t\"\"\".format(conditions=conditions), filters, as_dict=1)

\treturn data


# ── Conditions ───────────────────────────────────────────────
# All condition blocks are commented out — uncomment the ones you need.
# Each block maps one filter to a SQL fragment appended to WHERE.
def get_conditions(filters):
\tconditions = ""
{conditions_body}

\treturn conditions
"""


# ─────────────────────────────────────────────────────────────
#  Query Report Python stub
# ─────────────────────────────────────────────────────────────

def _generate_query_report_py(ref_doctype, columns, joins=None, qopts=None):
    joins  = joins  or []
    qopts  = qopts  or {}

    extra_where = qopts.get("extra_where", "").strip()
    order_by    = qopts.get("order_by",    "").strip()
    group_by    = qopts.get("group_by",    "").strip()
    having      = qopts.get("having",      "").strip()
    limit_rows  = int(qopts.get("limit_rows", 0) or 0)

    columns_block = _build_columns_py(columns, ref_doctype)
    join_sql      = _build_join_sql(joins)
    join_block    = ("\n" + join_sql) if join_sql else ""
    select_sql    = _build_select_sql(columns)

    extra_where_block = f"\n\t\t\t\t{extra_where}"    if extra_where else ""
    group_block       = f"\n\t\tGROUP BY\n\t\t\t{group_by}"  if group_by  else ""
    having_block      = f"\n\t\tHAVING\n\t\t\t{having}"      if having    else ""
    order_block       = f"\n\t\tORDER BY\n\t\t\t{order_by}"  if order_by  else "\n\t\tORDER BY\n\t\t\tt.modified DESC"
    limit_block       = f"\n\t\tLIMIT {limit_rows}"           if limit_rows else ""

    return f"""import frappe
from frappe import _


def execute(filters=None):
\tfilters = filters or {{}}
\treturn get_columns(), get_data(filters)


# ── Columns ─────────────────────────────────────────────────
# Remove, reorder, or edit any entry below.
def get_columns():
\treturn [

{columns_block}

\t]


# ── Data ─────────────────────────────────────────────────────
def get_data(filters):
\treturn frappe.db.sql(\"\"\"
\t\tSELECT
\t\t\t{select_sql}
\t\tFROM
\t\t\t`tab{ref_doctype}` t{join_block}
\t\tWHERE
\t\t\tt.docstatus < 2{extra_where_block}{group_block}{having_block}{order_block}{limit_block}
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
