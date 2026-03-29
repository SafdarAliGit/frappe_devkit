"""
Site Manager API for Frappe DevKit Studio.
Covers: new-site, backup, restore, drop-site, set-admin-password,
        set-config, get-config, enable/disable maintenance mode,
        migrate, clear-cache, scheduler, console, site info.
"""
import os, json, subprocess, tempfile, frappe
from frappe.utils import now_datetime
try:
    import pymysql as _mysql_driver
except ImportError:
    _mysql_driver = None


def _get_installed_apps(cfg):
    """Query tabInstalled Application from the site's DB. Falls back to apps.txt."""
    db_name = cfg.get("db_name")
    db_pass = cfg.get("db_password")
    db_host = cfg.get("db_host", "localhost")
    db_port = int(cfg.get("db_port", 3306))

    # Primary: query via pymysql
    if _mysql_driver and db_name and db_pass:
        try:
            conn = _mysql_driver.connect(
                host=db_host, port=db_port,
                user=db_name, password=db_pass, db=db_name,
                connect_timeout=3
            )
            with conn.cursor() as cur:
                cur.execute("SELECT app_name FROM `tabInstalled Application` ORDER BY idx")
                rows = cur.fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception:
            pass

    # Fallback: subprocess mysql with db credentials
    if db_name and db_pass:
        try:
            r = subprocess.run(
                ["mysql", "-u", db_name, f"-p{db_pass}",
                 "-h", db_host, f"-P{db_port}",
                 db_name, "-se",
                 "SELECT app_name FROM `tabInstalled Application` ORDER BY idx"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                return [l.strip() for l in r.stdout.splitlines() if l.strip()]
        except Exception:
            pass

    # Last resort: apps.txt
    return []


# ─── helpers ──────────────────────────────────────────────────────────────────
def _bench():
    return frappe.utils.get_bench_path()

def _sites():
    return os.path.join(_bench(), "sites")

def _python():
    return os.path.join(_bench(), "env", "bin", "python")

def _read_txt(path):
    if not os.path.exists(path): return []
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]

def _run(cmd, cwd=None, timeout=300):
    """Run a bench command, return {returncode, stdout, stderr}."""
    r = subprocess.run(
        cmd, cwd=cwd or _bench(),
        capture_output=True, text=True, timeout=timeout
    )
    return {"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}

def _ok(msg, **kw):
    return {"status": "success", "message": msg, **kw}

def _err(msg, **kw):
    return {"status": "error", "message": msg, **kw}

def _result(msg, r):
    """Convert subprocess result to API response."""
    if r["returncode"] == 0:
        return _ok(msg, stdout=r["stdout"], stderr=r["stderr"])
    return _err(f"Command failed: {msg}", stdout=r["stdout"], stderr=r["stderr"])


# ─── site listing & info ──────────────────────────────────────────────────────
@frappe.whitelist()
def list_sites():
    """List all sites in the bench with detailed info."""
    sites_path = _sites()
    result = []
    if not os.path.exists(sites_path):
        return _ok("No sites found", sites=[])

    for name in sorted(os.listdir(sites_path)):
        site_path = os.path.join(sites_path, name)
        cfg_path  = os.path.join(site_path, "site_config.json")
        if not os.path.isdir(site_path) or not os.path.exists(cfg_path):
            continue

        try:
            with open(cfg_path) as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

        installed = _get_installed_apps(cfg)

        # Check maintenance mode — Frappe uses maintenance_mode in site_config
        maintenance = bool(cfg.get("maintenance_mode", 0))

        # Backup list
        backup_path = os.path.join(site_path, "private", "backups")
        backups = []
        if os.path.isdir(backup_path):
            backups = sorted(
                [f for f in os.listdir(backup_path) if f.endswith(".sql.gz") or f.endswith(".tar")],
                reverse=True
            )[:5]

        result.append({
            "site"        : name,
            "db_name"     : cfg.get("db_name", ""),
            "db_host"     : cfg.get("db_host", "localhost"),
            "db_type"     : cfg.get("db_type", "mariadb"),
            "installed"   : installed,
            "app_count"   : len(installed),
            "maintenance" : maintenance,
            "recent_backups": backups,
            "site_config" : {k: v for k, v in cfg.items()
                             if k not in ("db_password", "redis_cache", "redis_queue", "redis_socketio")},
        })

    return _ok(f"{len(result)} site(s) found", sites=result)


@frappe.whitelist()
def get_site_info(site):
    """Get full info for a single site."""
    site_path = os.path.join(_sites(), site)
    cfg_path  = os.path.join(site_path, "site_config.json")

    if not os.path.exists(site_path):
        return _err(f"Site '{site}' not found")

    try:
        with open(cfg_path) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}

    installed = _read_txt(os.path.join(site_path, "apps.txt"))

    # Disk usage
    disk = {}
    try:
        r = subprocess.run(["du", "-sh", site_path], capture_output=True, text=True)
        disk["total"] = r.stdout.split()[0] if r.returncode == 0 else "?"
        for sub in ["private/backups", "public/files", "private/files"]:
            sp = os.path.join(site_path, sub)
            if os.path.isdir(sp):
                r2 = subprocess.run(["du", "-sh", sp], capture_output=True, text=True)
                disk[sub] = r2.stdout.split()[0] if r2.returncode == 0 else "?"
    except Exception:
        pass

    # Scheduler status
    sched = {}
    try:
        r = _run(["bench", "--site", site, "scheduler", "status"])
        sched["status"] = r["stdout"].strip() or r["stderr"].strip()
    except Exception:
        sched["status"] = "unknown"

    return _ok(f"Site info for '{site}'", info={
        "site"         : site,
        "installed_apps": installed,
        "config"       : {k: v for k, v in cfg.items()
                          if k not in ("db_password",)},
        "disk"         : disk,
        "scheduler"    : sched,
    })


# ─── create site ──────────────────────────────────────────────────────────────
@frappe.whitelist()
def create_site(site, db_name="", db_password="", admin_password="",
                apps=None, db_type="mariadb", no_mariadb_socket=0):
    """
    Create a new Frappe site.
    bench new-site <site> [--db-name ...] [--admin-password ...]
    """
    if isinstance(apps, str):
        apps = json.loads(apps) if apps else []
    apps = apps or []

    cmd = ["bench", "new-site", site]
    if admin_password:
        cmd += ["--admin-password", admin_password]
    if db_name:
        cmd += ["--db-name", db_name]
    if db_password:
        cmd += ["--db-root-password", db_password]
    if db_type and db_type != "mariadb":
        cmd += ["--db-type", db_type]
    if int(no_mariadb_socket):
        cmd += ["--no-mariadb-socket"]
    for app in apps:
        cmd += ["--install-app", app]

    try:
        r = _run(cmd, timeout=180)
    except subprocess.TimeoutExpired:
        return _err("Site creation timed out (>3 min)")

    return _result(f"Create site '{site}'", r)


# ─── drop site ────────────────────────────────────────────────────────────────
@frappe.whitelist()
def drop_site(site, force=0, root_password=""):
    """
    Drop a site: bench drop-site <site>
    DESTRUCTIVE — deletes DB and site files.
    """
    if site == frappe.local.site:
        return _err("Cannot drop the currently active site.")

    cmd = ["bench", "drop-site", site, "--force"] if int(force) else ["bench", "drop-site", site]
    if root_password:
        cmd += ["--root-password", root_password]

    try:
        r = _run(cmd, timeout=120)
    except subprocess.TimeoutExpired:
        return _err("Drop site timed out")

    return _result(f"Drop site '{site}'", r)


# ─── backup ───────────────────────────────────────────────────────────────────
@frappe.whitelist()
def backup_site(site, with_files=0, compress=1, backup_path=""):
    """
    Backup a site: bench --site <site> backup [--with-files]
    """
    cmd = ["bench", "--site", site, "backup"]
    if int(with_files):
        cmd.append("--with-files")
    if int(compress):
        cmd.append("--compress")
    if backup_path:
        cmd += ["--backup-path", backup_path]

    try:
        r = _run(cmd, timeout=300)
    except subprocess.TimeoutExpired:
        return _err("Backup timed out")

    return _result(f"Backup site '{site}'", r)


@frappe.whitelist()
def list_backups(site):
    """List available backups for a site."""
    backup_dir = os.path.join(_sites(), site, "private", "backups")
    if not os.path.isdir(backup_dir):
        return _ok("No backups found", backups=[])

    files = []
    for f in sorted(os.listdir(backup_dir), reverse=True):
        fp = os.path.join(backup_dir, f)
        stat = os.stat(fp)
        files.append({
            "name"    : f,
            "size"    : _human_size(stat.st_size),
            "date"    : _fmt_time(stat.st_mtime),
            "path"    : fp,
            "type"    : "database" if "database" in f or f.endswith(".sql.gz") else
                        "files"   if "files" in f else "other",
        })

    return _ok(f"{len(files)} backup(s) found", backups=files)


@frappe.whitelist()
def restore_site(site, backup_file, with_private_files="", with_public_files="",
                 admin_password="", db_root_password="", force=0):
    """
    Restore a site from backup:
    bench --site <site> restore <backup_file>
    """
    cmd = ["bench", "--site", site, "restore", backup_file]
    if with_private_files:
        cmd += ["--with-private-files", with_private_files]
    if with_public_files:
        cmd += ["--with-public-files", with_public_files]
    if admin_password:
        cmd += ["--admin-password", admin_password]
    if db_root_password:
        cmd += ["--db-root-password", db_root_password]
    if int(force):
        cmd.append("--force")

    try:
        r = _run(cmd, timeout=600)
    except subprocess.TimeoutExpired:
        return _err("Restore timed out (>10 min)")

    return _result(f"Restore site '{site}'", r)


# ─── admin password ───────────────────────────────────────────────────────────
@frappe.whitelist()
def set_admin_password(site, new_password):
    """bench --site <site> set-admin-password <password>"""
    if not new_password or len(new_password) < 6:
        return _err("Password must be at least 6 characters")

    r = _run(["bench", "--site", site, "set-admin-password", new_password])
    return _result(f"Set admin password for '{site}'", r)


# ─── site config ──────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_site_config(site):
    """Read site_config.json (excluding db_password)."""
    cfg_path = os.path.join(_sites(), site, "site_config.json")
    if not os.path.exists(cfg_path):
        return _err(f"site_config.json not found for '{site}'")

    with open(cfg_path) as f:
        cfg = json.load(f)

    safe = {k: v for k, v in cfg.items() if k != "db_password"}
    return _ok(f"Config for '{site}'", config=safe)


@frappe.whitelist()
def set_site_config(site, key, value, value_type="string"):
    """bench --site <site> set-config <key> <value>"""
    cmd = ["bench", "--site", site, "set-config"]

    # Convert value based on type
    if value_type == "int":
        cmd += ["-p", key, str(int(value))]
    elif value_type == "bool":
        cmd += ["-p", key, "1" if value in ("1", "true", True) else "0"]
    elif value_type == "json":
        cmd += ["-p", key, value]
    else:
        cmd += [key, str(value)]

    r = _run(cmd)
    return _result(f"Set config '{key}' on '{site}'", r)


@frappe.whitelist()
def remove_site_config(site, key):
    """Remove a key from site_config.json by editing the file directly."""
    cfg_path = os.path.join(_sites(), site, "site_config.json")
    if not os.path.exists(cfg_path):
        frappe.throw(f"site_config.json not found for site '{site}'")
    with open(cfg_path, "r") as f:
        cfg = json.load(f)
    if key not in cfg:
        return _ok(f"Key '{key}' not found in config for '{site}' (nothing to remove)")
    del cfg[key]
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=1)
    return _ok(f"Removed config key '{key}' from '{site}'")


# ─── maintenance mode ─────────────────────────────────────────────────────────
@frappe.whitelist()
def set_maintenance_mode(site, enable=1):
    """bench --site <site> set-maintenance-mode on|off"""
    mode = "on" if int(enable) else "off"
    r = _run(["bench", "--site", site, "set-maintenance-mode", mode])
    return _result(f"Maintenance mode {mode} for '{site}'", r)


# ─── scheduler ────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scheduler_action(site, action):
    """
    Manage scheduler: enable | disable | resume | suspend | status | run-jobs
    bench --site <site> scheduler <action>
    """
    valid = {"enable", "disable", "resume", "suspend", "status", "run-jobs"}
    if action not in valid:
        return _err(f"Invalid action '{action}'. Valid: {', '.join(sorted(valid))}")

    r = _run(["bench", "--site", site, "scheduler", action])
    return _result(f"Scheduler {action} for '{site}'", r)


# ─── migrate ──────────────────────────────────────────────────────────────────
@frappe.whitelist()
def migrate_site(site, skip_failing=0):
    """bench --site <site> migrate"""
    cmd = ["bench", "--site", site, "migrate"]
    if int(skip_failing):
        cmd.append("--skip-failing")

    try:
        r = _run(cmd, timeout=600)
    except subprocess.TimeoutExpired:
        return _err("Migrate timed out (>10 min)")

    return _result(f"Migrate '{site}'", r)


# ─── clear cache ──────────────────────────────────────────────────────────────
@frappe.whitelist()
def clear_site_cache(site):
    """bench --site <site> clear-cache"""
    r = _run(["bench", "--site", site, "clear-cache"])
    return _result(f"Clear cache for '{site}'", r)


@frappe.whitelist()
def clear_website_cache(site):
    """bench --site <site> clear-website-cache"""
    r = _run(["bench", "--site", site, "clear-website-cache"])
    return _result(f"Clear website cache for '{site}'", r)


# ─── use (set default site) ───────────────────────────────────────────────────
@frappe.whitelist()
def use_site(site):
    """bench use <site>  — set as default site"""
    r = _run(["bench", "use", site])
    return _result(f"Set default site to '{site}'", r)


# ─── reinstall ────────────────────────────────────────────────────────────────
@frappe.whitelist()
def reinstall_site(site, admin_password="", mariadb_root_password=""):
    """
    bench --site <site> reinstall
    DESTRUCTIVE — drops all tables and reinstalls.
    """
    if site == frappe.local.site and not admin_password:
        return _err("Provide admin password for safety when reinstalling current site")

    cmd = ["bench", "--site", site, "reinstall", "--yes"]
    if admin_password:
        cmd += ["--admin-password", admin_password]
    if mariadb_root_password:
        cmd += ["--mariadb-root-password", mariadb_root_password]

    try:
        r = _run(cmd, timeout=300)
    except subprocess.TimeoutExpired:
        return _err("Reinstall timed out")

    return _result(f"Reinstall '{site}'", r)


# ─── execute script ───────────────────────────────────────────────────────────
@frappe.whitelist()
def execute_script(site, script):
    """
    Run arbitrary Python in the Frappe site context.
    Writes the script to a temp file and runs it with the bench virtualenv
    Python after initializing Frappe — avoids the bench execute limitation
    which only accepts dotted module paths, not free expressions.
    """
    if not script or not script.strip():
        return _err("Script cannot be empty")

    # Safety: block destructive patterns
    blocked = ["os.system", "subprocess", "shutil.rmtree", "__import__",
               "eval(", "exec(", "open(", "os.remove", "drop_site"]
    for b in blocked:
        if b in script:
            return _err(f"Blocked expression: '{b}' not allowed for safety")

    sites_path = _sites()
    wrapper = (
        "import frappe\n"
        f"frappe.init(site={site!r}, sites_path={sites_path!r})\n"
        "frappe.connect()\n"
        "try:\n"
        + "\n".join("    " + line for line in script.splitlines()) + "\n"
        "    frappe.db.commit()\n"
        "except Exception as _e:\n"
        "    print('ERROR:', _e)\n"
        "    raise\n"
        "finally:\n"
        "    frappe.destroy()\n"
    )

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(wrapper)
            tmp = f.name
        r = _run([_python(), tmp], timeout=60)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

    return _result(f"Execute on '{site}'", r)


# ─── common site config keys ──────────────────────────────────────────────────
@frappe.whitelist()
def get_common_config():
    """Read bench/sites/common_site_config.json"""
    path = os.path.join(_sites(), "common_site_config.json")
    if not os.path.exists(path):
        return _ok("No common config found", config={})
    with open(path) as f:
        try:
            cfg = json.load(f)
        except Exception:
            cfg = {}
    safe = {k: v for k, v in cfg.items() if k not in ("db_password",)}
    return _ok("Common site config", config=safe)


# ─── backup download / upload ─────────────────────────────────────────────────
@frappe.whitelist()
def download_backup_file(site, filename):
    """Stream a backup file to the browser as a download."""
    import re as _re
    if not _re.match(r'^[\w\-\.]+$', filename):
        frappe.throw("Invalid filename")
    backup_dir = os.path.join(_sites(), site, "private", "backups")
    full = os.path.join(backup_dir, filename)
    real_full = os.path.realpath(full)
    real_dir  = os.path.realpath(backup_dir)
    if not real_full.startswith(real_dir + os.sep):
        frappe.throw("Invalid path")
    if not os.path.isfile(full):
        frappe.throw(f"Backup file '{filename}' not found")
    with open(full, "rb") as f:
        content = f.read()
    frappe.response["type"]         = "download"
    frappe.response["filename"]     = filename
    frappe.response["filecontent"]  = content
    frappe.response["content_type"] = "application/octet-stream"


@frappe.whitelist()
def clear_restore_lock(site):
    """Remove stale lock files left by crashed restore/new-site operations."""
    locks_dir = os.path.join(_sites(), site, "locks")
    candidates = ["site_restore.lock", "bench_new_site.lock"]
    removed = []
    for name in candidates:
        p = os.path.join(locks_dir, name)
        if os.path.exists(p):
            os.remove(p)
            removed.append(p)
    if removed:
        return _ok(f"Cleared {len(removed)} lock(s) for '{site}'", info={"removed": removed})
    return _ok(f"No stale restore locks found for '{site}' — nothing to clear")


@frappe.whitelist()
def upload_backup_file(site, file_type="database"):
    """Receive an uploaded backup file and save it to the site's backup directory."""
    import re as _re
    backup_dir = os.path.join(_sites(), site, "private", "backups")
    os.makedirs(backup_dir, exist_ok=True)

    uploaded = frappe.request.files.get("file")
    if not uploaded:
        frappe.throw("No file received")

    filename = uploaded.filename
    if not _re.match(r'^[\w\-\.]+$', filename):
        frappe.throw("Invalid filename")

    valid_exts = {
        "database":      (".sql.gz", ".sql"),
        "public_files":  (".tar",),
        "private_files": (".tar",),
    }
    exts = valid_exts.get(file_type, (".sql.gz", ".sql", ".tar"))
    if not any(filename.endswith(e) for e in exts):
        frappe.throw(f"Invalid file extension for type '{file_type}'")

    dest    = os.path.join(backup_dir, filename)
    content = uploaded.read()
    with open(dest, "wb") as f:
        f.write(content)

    return {"uploaded": True, "filename": filename, "size": _human_size(len(content))}


# ─── build & restart ──────────────────────────────────────────────────────────
@frappe.whitelist()
def build_assets(app_name=""):
    """Run bench build, optionally for a specific app."""
    cmd = ["bench", "build"]
    if app_name:
        cmd += ["--app", app_name]
    return _result("Build assets", _run(cmd, timeout=600))


@frappe.whitelist()
def restart_workers():
    """Run bench restart."""
    return _result("Restart workers", _run(["bench", "restart"], timeout=120))


# ─── backup all sites ─────────────────────────────────────────────────────────
@frappe.whitelist()
def backup_all_sites(with_files=0, compress=0):
    """bench backup-all-sites — back up every site in the bench."""
    cmd = ["bench", "backup-all-sites"]
    if int(with_files):
        cmd.append("--with-files")
    if int(compress):
        cmd.append("--compress")
    try:
        r = _run(cmd, timeout=600)
    except subprocess.TimeoutExpired:
        return _err("backup-all-sites timed out (>10 min)")
    return _result("Backup all sites", r)


# ─── partial restore ──────────────────────────────────────────────────────────
@frappe.whitelist()
def partial_restore(site, backup_file, verbose=0):
    """
    bench --site <site> partial-restore <backup_file>
    Restores only the tables included in a partial backup
    (one created with --only or --exclude).
    """
    cmd = ["bench", "--site", site, "partial-restore", backup_file]
    if int(verbose):
        cmd.append("-v")
    try:
        r = _run(cmd, timeout=600)
    except subprocess.TimeoutExpired:
        return _err("Partial restore timed out")
    return _result(f"Partial restore '{site}'", r)


# ─── list installed apps on site ──────────────────────────────────────────────
@frappe.whitelist()
def list_site_apps(site):
    """bench --site <site> list-apps — apps installed on a specific site."""
    r = _run(["bench", "--site", site, "list-apps"])
    apps = [line.strip() for line in r["stdout"].splitlines() if line.strip()]
    return _result(f"Installed apps on '{site}'", r) | {"apps": apps}


# ─── background job management ────────────────────────────────────────────────
@frappe.whitelist()
def show_pending_jobs(site):
    """bench --site <site> show-pending-jobs — list queued background jobs."""
    r = _run(["bench", "--site", site, "show-pending-jobs"])
    return _result(f"Pending jobs for '{site}'", r)


@frappe.whitelist()
def purge_jobs(site):
    """
    bench --site <site> purge-jobs — clear all pending background jobs.
    Use when workers are stuck or after a failed deployment.
    """
    r = _run(["bench", "--site", site, "purge-jobs"])
    return _result(f"Purge jobs for '{site}'", r)


@frappe.whitelist()
def ready_for_migration(site):
    """
    bench --site <site> ready-for-migration
    Checks whether all background jobs have finished — safe to run before migrate.
    """
    r = _run(["bench", "--site", site, "ready-for-migration"])
    return _result(f"Migration readiness check for '{site}'", r)


@frappe.whitelist()
def trigger_scheduler_event(site, event="all"):
    """
    bench --site <site> trigger-scheduler-event <event>
    Force-run a scheduled event now.
    event: all | daily | weekly | monthly | hourly | daily_long | hourly_long
    """
    valid = {"all", "daily", "weekly", "monthly", "hourly", "daily_long", "hourly_long"}
    if event not in valid:
        return _err(f"Invalid event '{event}'. Valid: {', '.join(sorted(valid))}")
    r = _run(["bench", "--site", site, "trigger-scheduler-event", event], timeout=120)
    return _result(f"Trigger scheduler event '{event}' on '{site}'", r)


# ─── search & permissions ─────────────────────────────────────────────────────
@frappe.whitelist()
def rebuild_global_search(site):
    """bench --site <site> rebuild-global-search — rebuild the full-text search index."""
    try:
        r = _run(["bench", "--site", site, "rebuild-global-search"], timeout=300)
    except subprocess.TimeoutExpired:
        return _err("Rebuild global search timed out")
    return _result(f"Rebuild global search for '{site}'", r)


@frappe.whitelist()
def reset_perms(site):
    """
    bench --site <site> reset-perms
    Restore all DocType permissions to their app defaults.
    Use after custom permission changes cause access issues.
    """
    r = _run(["bench", "--site", site, "reset-perms"])
    return _result(f"Reset permissions for '{site}'", r)


# ─── sessions ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def destroy_all_sessions(site):
    """
    bench --site <site> destroy-all-sessions
    Force-log out all active users. Use after a security incident
    or before a major schema change that requires a fresh login.
    """
    r = _run(["bench", "--site", site, "destroy-all-sessions"])
    return _result(f"Destroy all sessions for '{site}'", r)


# ─── patches ──────────────────────────────────────────────────────────────────
@frappe.whitelist()
def run_patch(site, patch_module):
    """
    bench --site <site> run-patch <patch_module>
    Re-run a specific patch by its dotted module path.
    Example: frappe.patches.v14.drop_data_import_legacy
    """
    if not patch_module or "." not in patch_module:
        return _err("patch_module must be a dotted path, e.g. myapp.patches.v1.fix_something")
    r = _run(["bench", "--site", site, "run-patch", patch_module], timeout=180)
    return _result(f"Run patch '{patch_module}' on '{site}'", r)


# ─── user management ──────────────────────────────────────────────────────────
@frappe.whitelist()
def add_system_manager(site, email, first_name="", last_name="", send_welcome_email=0):
    """
    bench --site <site> add-system-manager <email>
    Add a System Manager user. Safe to run when locked out of the site.
    """
    cmd = ["bench", "--site", site, "add-system-manager", email]
    if first_name:
        cmd += ["--first-name", first_name]
    if last_name:
        cmd += ["--last-name", last_name]
    if int(send_welcome_email):
        cmd.append("--send-welcome-email")
    r = _run(cmd)
    return _result(f"Add system manager '{email}' on '{site}'", r)


@frappe.whitelist()
def add_user(site, email, first_name="", last_name="", roles=None, password=""):
    """bench --site <site> add-user <email>"""
    if isinstance(roles, str):
        roles = json.loads(roles) if roles else []
    roles = roles or []

    cmd = ["bench", "--site", site, "add-user", email]
    if first_name:
        cmd += ["--first-name", first_name]
    if last_name:
        cmd += ["--last-name", last_name]
    if password:
        cmd += ["--user-password", password]
    for role in roles:
        cmd += ["--add-role", role]
    r = _run(cmd)
    return _result(f"Add user '{email}' on '{site}'", r)


@frappe.whitelist()
def disable_user(site, email):
    """bench --site <site> disable-user <email>"""
    r = _run(["bench", "--site", site, "disable-user", email])
    return _result(f"Disable user '{email}' on '{site}'", r)


@frappe.whitelist()
def set_password(site, user, password):
    """bench --site <site> set-password <user> <password>"""
    if not password or len(password) < 6:
        return _err("Password must be at least 6 characters")
    r = _run(["bench", "--site", site, "set-password", user, password])
    return _result(f"Set password for '{user}' on '{site}'", r)


# ─── database maintenance ─────────────────────────────────────────────────────
@frappe.whitelist()
def trim_database(site, dry_run=0, output_format="table", no_backup=0):
    """
    bench --site <site> trim-database
    Remove tables with no matching DocType (orphaned after uninstalling apps).
    Always run with dry_run=1 first to preview what will be removed.
    """
    cmd = ["bench", "--site", site, "trim-database"]
    if int(dry_run):
        cmd.append("--dry-run")
    if output_format.lower() == "json":
        cmd += ["--format", "json"]
    if int(no_backup):
        cmd.append("--no-backup")
    try:
        r = _run(cmd, timeout=300)
    except subprocess.TimeoutExpired:
        return _err("trim-database timed out")
    return _result(f"Trim database for '{site}'", r)


@frappe.whitelist()
def trim_tables(site, dry_run=0, output_format="text", no_backup=0):
    """
    bench --site <site> trim-tables
    Remove columns with no matching DocType field (reduces backup size, speeds up queries).
    Always run with dry_run=1 first.
    """
    cmd = ["bench", "--site", site, "trim-tables"]
    if int(dry_run):
        cmd.append("--dry-run")
    if output_format.lower() == "json":
        cmd += ["--format", "json"]
    if int(no_backup):
        cmd.append("--no-backup")
    try:
        r = _run(cmd, timeout=300)
    except subprocess.TimeoutExpired:
        return _err("trim-tables timed out")
    return _result(f"Trim tables for '{site}'", r)


@frappe.whitelist()
def transform_database(site, table="all", engine="", row_format="", failfast=0):
    """
    bench --site <site> transform-database (MariaDB, Frappe v14+)
    Change storage engine or row format for one or all tables.
    engine: InnoDB | MyISAM
    row_format: DYNAMIC | COMPACT | REDUNDANT | COMPRESSED
    """
    cmd = ["bench", "--site", site, "transform-database"]
    if table:
        cmd += ["--table", table]
    if engine:
        cmd += ["--engine", engine]
    if row_format:
        cmd += ["--row_format", row_format]
    if int(failfast):
        cmd.append("--failfast")
    try:
        r = _run(cmd, timeout=600)
    except subprocess.TimeoutExpired:
        return _err("transform-database timed out")
    return _result(f"Transform database for '{site}'", r)


# ─── testing ──────────────────────────────────────────────────────────────────
@frappe.whitelist()
def run_tests(site, app="", module="", test="", parallel=0):
    """
    bench --site <site> run-tests
    Requires allow_tests = 1 in site_config.json.
    Never leave allow_tests enabled on production.
    """
    cmd = ["bench", "--site", site,
           "run-parallel-tests" if int(parallel) else "run-tests"]
    if app:
        cmd += ["--app", app]
    if module:
        cmd += ["--module", module]
    if test:
        cmd += ["--test", test]
    try:
        r = _run(cmd, timeout=600)
    except subprocess.TimeoutExpired:
        return _err("run-tests timed out (>10 min)")
    return _result(f"Run tests on '{site}'", r)


# ─── data import / export ─────────────────────────────────────────────────────
@frappe.whitelist()
def data_import(site, doctype, file_path, submit_after_import=0, overwrite=0):
    """
    bench --site <site> data-import --doctype <dt> --file <file>
    Import records from CSV/XLSX into a DocType.
    """
    cmd = ["bench", "--site", site, "data-import",
           "--doctype", doctype, "--file", file_path]
    if int(submit_after_import):
        cmd.append("--submit-after-import")
    if int(overwrite):
        cmd.append("--overwrite")
    try:
        r = _run(cmd, timeout=300)
    except subprocess.TimeoutExpired:
        return _err("data-import timed out")
    return _result(f"Data import '{doctype}' on '{site}'", r)


@frappe.whitelist()
def export_csv(site, doctype, file_path, all_doctypes=0):
    """
    bench --site <site> export-csv --doctype <dt> --path <file>
    Export a DocType as a CSV template (data import format).
    """
    cmd = ["bench", "--site", site, "export-csv",
           "--doctype", doctype, "--path", file_path]
    if int(all_doctypes):
        cmd.append("--all-doctypes")
    r = _run(cmd, timeout=120)
    return _result(f"Export CSV '{doctype}' on '{site}'", r)


@frappe.whitelist()
def bulk_rename(site, doctype, csv_file):
    """
    bench --site <site> bulk-rename <doctype> <csv_file>
    CSV format: old_name,new_name per row.
    """
    r = _run(["bench", "--site", site, "bulk-rename", doctype, csv_file], timeout=120)
    return _result(f"Bulk rename '{doctype}' on '{site}'", r)


# ─── utils ────────────────────────────────────────────────────────────────────
def _human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def _fmt_time(ts):
    from datetime import datetime
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
