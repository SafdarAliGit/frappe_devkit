"""
Query Editor API for Frappe DevKit Studio.
Allows executing SQL queries against any bench site's MariaDB database.
Only SELECT queries are allowed by default; write queries require explicit flag.
"""
import os, re, json, frappe


def _bench():
    return frappe.utils.get_bench_path()

def _sites_path():
    return os.path.join(_bench(), "sites")

def _site_cfg(site):
    p = os.path.join(_sites_path(), site, "site_config.json")
    if not os.path.exists(p):
        frappe.throw(f"Site '{site}' not found")
    with open(p) as f:
        return json.load(f)

def _connect(cfg):
    import pymysql
    return pymysql.connect(
        host=cfg.get("db_host", "localhost"),
        port=int(cfg.get("db_port", 3306)),
        user=cfg.get("db_name"),
        password=cfg.get("db_password"),
        db=cfg.get("db_name"),
        charset="utf8mb4",
        connect_timeout=5,
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )

def _is_write(sql):
    first = sql.strip().lstrip(";").split()[0].upper() if sql.strip() else ""
    return first in ("INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER",
                     "CREATE", "REPLACE", "RENAME", "CALL")

def _classify_value(v):
    """Return (display_value, css_class) for a cell value."""
    if v is None:
        return ("NULL", "null-val")
    if isinstance(v, bool):
        return (str(v), "bool-val")
    if isinstance(v, (int, float)):
        return (str(v), "num-val")
    s = str(v)
    if re.match(r'^\d{4}-\d{2}-\d{2}', s):
        return (s, "date-val")
    if s.startswith(('{', '[')) and len(s) > 2:
        return (s, "json-val")
    return (s, "")


@frappe.whitelist()
def execute_query(site, sql, allow_write=0, limit=500):
    """
    Execute a SQL query against the given site's database.
    Returns columns + rows for SELECT, affected_rows for writes.
    """
    sql = (sql or "").strip()
    if not sql:
        frappe.throw("Query is empty")

    allow_write = int(allow_write)
    limit = min(int(limit or 500), 5000)

    write = _is_write(sql)
    if write and not allow_write:
        frappe.throw("Write queries are disabled. Enable 'Allow write' to run INSERT/UPDATE/DELETE.")

    cfg = _site_cfg(site)

    # Inject LIMIT for SELECT queries that don't have one
    sql_upper = re.sub(r'\s+', ' ', sql.upper())
    if not write and 'LIMIT' not in sql_upper:
        sql = sql.rstrip(";") + f" LIMIT {limit}"

    conn = _connect(cfg)
    try:
        with conn.cursor() as cur:
            t0 = frappe.utils.now_datetime()
            cur.execute(sql)
            elapsed_ms = int((frappe.utils.now_datetime() - t0).total_seconds() * 1000)

            if write:
                conn.commit()
                return {
                    "type": "write",
                    "affected_rows": cur.rowcount,
                    "elapsed_ms": elapsed_ms,
                    "sql": sql,
                }

            rows = cur.fetchall()
            columns = [d[0] for d in cur.description] if cur.description else []

            # Classify each value
            classified = []
            for row in rows:
                classified_row = {}
                for col in columns:
                    val = row[col]
                    display, cls = _classify_value(val)
                    classified_row[col] = {"v": display, "c": cls}
                classified.append(classified_row)

            return {
                "type": "select",
                "columns": columns,
                "rows": classified,
                "row_count": len(rows),
                "elapsed_ms": elapsed_ms,
                "sql": sql,
                "truncated": len(rows) >= limit,
            }
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return {
            "type": "error",
            "error": str(e),
            "sql": sql,
        }
    finally:
        conn.close()


@frappe.whitelist()
def get_tables(site):
    """Return list of tables in the site's database."""
    cfg = _site_cfg(site)
    conn = _connect(cfg)
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            rows = cur.fetchall()
        col = list(rows[0].keys())[0] if rows else None
        tables = [r[col] for r in rows] if col else []
        return {"tables": tables}
    finally:
        conn.close()


@frappe.whitelist()
def describe_table(site, table):
    """Return DESCRIBE output for a table."""
    cfg = _site_cfg(site)
    # Sanitize table name
    if not re.match(r'^[\w]+$', table):
        frappe.throw("Invalid table name")
    conn = _connect(cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(f"DESCRIBE `{table}`")
            rows = cur.fetchall()
        return {"columns": rows}
    finally:
        conn.close()


@frappe.whitelist()
def get_columns(site, table):
    """Return column names for a table (used by autocomplete)."""
    table = (table or "").strip().strip("`")
    if not re.match(r'^[\w]+$', table):
        frappe.throw("Invalid table name")
    cfg = _site_cfg(site)
    conn = _connect(cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(f"DESCRIBE `{table}`")
            rows = cur.fetchall()
        return {"columns": [r["Field"] for r in rows], "table": table}
    finally:
        conn.close()


@frappe.whitelist()
def get_frappe_doctypes(site):
    """Return list of DocTypes from tabDocType for autocomplete."""
    cfg = _site_cfg(site)
    conn = _connect(cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, module, issingle FROM `tabDocType` ORDER BY name LIMIT 2000"
            )
            rows = cur.fetchall()
        return {"doctypes": rows}
    finally:
        conn.close()
