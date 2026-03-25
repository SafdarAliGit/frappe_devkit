import os
import json
import subprocess
import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe_devkit.utils.file_utils import write_file, write_json, ensure_init_py
from frappe_devkit.utils.validators import validate_app_name


# ─────────────────────────────────────────────────────────────────
# PATH HELPERS
# ─────────────────────────────────────────────────────────────────
def _bench():
    return frappe.utils.get_bench_path()

def _apps_dir():
    return os.path.join(_bench(), "apps")

def _sites_dir():
    return os.path.join(_bench(), "sites")

def _python():
    return os.path.join(_bench(), "env", "bin", "python")

def _bench_apps_txt():
    """bench/apps.txt — source of truth, read by bench commands."""
    return os.path.join(_bench(), "apps.txt")

def _sites_apps_txt():
    """bench/sites/apps.txt — live list Frappe checks during install-app."""
    return os.path.join(_bench(), "sites", "apps.txt")

def _apps_json():
    """bench/sites/apps.json — app metadata registry."""
    return os.path.join(_bench(), "sites", "apps.json")


# ─────────────────────────────────────────────────────────────────
# READ / WRITE HELPERS
# ─────────────────────────────────────────────────────────────────
def _read_txt(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]

def _write_txt(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(items) + "\n")

def _read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def _write_json_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent="\t")


# ─────────────────────────────────────────────────────────────────
# APPS.TXT — registry helpers
# bench/apps.txt  : read by bench CLI commands (install_app_on_site / register)
# sites/apps.txt  : read by Frappe during install-app; written directly by scaffold
# ─────────────────────────────────────────────────────────────────
def _add_to_bench_apps_txt(app_name):
    """
    Register app in BOTH bench-level registry files:

    1. bench/apps.txt        — source of truth bench reads at startup
    2. bench/sites/apps.txt  — live list Frappe checks during install-app

    Both must be updated. bench regenerates sites/apps.txt from apps.txt,
    but only at startup — not during a running bench install-app call.
    So we write both immediately to avoid any race condition.
    """
    added = False

    for path in [_bench_apps_txt(), _sites_apps_txt()]:
        apps = _read_txt(path)
        if app_name not in apps:
            apps.append(app_name)
            _write_txt(path, apps)
            added = True

    return added

def _remove_from_bench_apps_txt(app_name):
    """Remove app from bench/apps.txt and bench/sites/apps.txt. Returns dict with per-file status."""
    result = {"bench_txt": False, "sites_txt": False}
    for key, path in [("bench_txt", _bench_apps_txt()), ("sites_txt", _sites_apps_txt())]:
        apps = _read_txt(path)
        if app_name in apps:
            apps.remove(app_name)
            _write_txt(path, apps)
            result[key] = True
    return result


# ─────────────────────────────────────────────────────────────────
# APPS.JSON
# ─────────────────────────────────────────────────────────────────
def _add_to_apps_json(app_name, version="0.0.1", app_title="", app_publisher="",
                      app_description="", app_email="", app_license="MIT"):
    path = _apps_json()
    data = _read_json(path)
    data[app_name] = {
        "app_name": app_name,
        "app_title": app_title or app_name,
        "app_publisher": app_publisher,
        "app_description": app_description,
        "app_email": app_email,
        "app_license": app_license,
        "app_version": version,
        "branch": "main",
        "is_repo": False,
        "required": [],
    }
    _write_json_file(path, data)

def _remove_from_apps_json(app_name):
    path = _apps_json()
    data = _read_json(path)
    if app_name in data:
        del data[app_name]
        _write_json_file(path, data)
        return True
    return False


# ─────────────────────────────────────────────────────────────────
# READ HOOKS ATTR DIRECTLY FROM DISK
# ─────────────────────────────────────────────────────────────────
def _hooks_attr(app_name, attr):
    """Read a single attr from hooks.py on disk without importing."""
    import re
    bench_path = _bench()
    candidates = [
        os.path.join(bench_path, "apps", app_name, app_name, "hooks.py"),
        os.path.join(bench_path, "apps", app_name, "hooks.py"),
    ]
    pat = re.compile(r"^" + re.escape(attr) + r'\s*=\s*["\']([^"\']*)["\']', re.MULTILINE)
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    m = pat.search(f.read())
                if m:
                    return m.group(1)
            except Exception:
                pass
    return ""

def _app_version(app_name):
    return _hooks_attr(app_name, "app_version") or "0.0.1"


# ─────────────────────────────────────────────────────────────────
# MAKE APP IMPORTABLE — write .pth file into site-packages
# ─────────────────────────────────────────────────────────────────
def _make_importable(app_name, app_root):
    """
    Write a .pth file into the bench virtualenv's site-packages.
    This is the most reliable way to make an app importable — it's
    exactly what pip install -e does internally but without needing
    a valid setup.py/pyproject.toml build system.
    """
    python = _python()
    bench_path = _bench()
    messages = []

    # Find site-packages directory
    try:
        r = subprocess.run(
            [python, "-c",
             "import site; pkgs=[p for p in site.getsitepackages() if 'site-packages' in p];"
             "print(pkgs[0] if pkgs else '')"],
            capture_output=True, text=True, cwd=bench_path
        )
        site_packages = r.stdout.strip()
        if site_packages and os.path.isdir(site_packages):
            pth_path = os.path.join(site_packages, f"{app_name}.pth")
            with open(pth_path, "w") as f:
                f.write(app_root + "\n")
            messages.append(f"wrote {app_name}.pth → {pth_path}")
        else:
            messages.append(f"site-packages not found: {r.stderr[:100]}")
    except Exception as e:
        messages.append(f"pth error: {e}")

    # Verify import works
    try:
        check = subprocess.run(
            [python, "-c", f"import {app_name}"],
            capture_output=True, text=True, cwd=bench_path
        )
        if check.returncode == 0:
            messages.append("import verified ✓")
        else:
            messages.append(f"import check failed: {check.stderr[:100]}")
    except Exception as e:
        messages.append(f"import check error: {e}")

    return " | ".join(messages)


# ─────────────────────────────────────────────────────────────────
# SCAFFOLD APP
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def scaffold_app(app_name, app_title, app_publisher, app_description,
    app_email="", app_license="MIT", app_version="0.0.1",
    required_apps=None, overwrite=False):
    """
    Scaffold a complete Frappe app and register it properly:
    1. Create all app files under bench/apps/<app_name>/
    2. Write .pth file so Python can import it
    3. Add to bench/sites/apps.txt (so Frappe can find it during install-app)
    4. Add to bench/sites/apps.json (metadata)
    """
    validate_app_name(app_name)
    if isinstance(required_apps, str):
        required_apps = json.loads(required_apps) if required_apps else []
    required_apps = required_apps or ["frappe"]

    bench_path = _bench()
    app_root   = os.path.join(bench_path, "apps", app_name)
    app_pkg    = os.path.join(app_root, app_name)
    module_dir = os.path.join(app_pkg, app_name)

    for d in [app_root, app_pkg, module_dir,
              os.path.join(module_dir, "doctype"),
              os.path.join(module_dir, "report"),
              os.path.join(module_dir, "print_format"),
              os.path.join(module_dir, "page"),
              os.path.join(module_dir, "workspace"),
              os.path.join(app_pkg, "fixtures"),
              os.path.join(app_pkg, "overrides"),
              os.path.join(app_pkg, "tests")]:
        os.makedirs(d, exist_ok=True)

    ensure_init_py(app_pkg)
    ensure_init_py(module_dir)
    ensure_init_py(os.path.join(app_pkg, "overrides"))
    ensure_init_py(os.path.join(module_dir, "doctype"))
    ensure_init_py(os.path.join(module_dir, "report"))
    ensure_init_py(os.path.join(module_dir, "print_format"))
    ensure_init_py(os.path.join(module_dir, "page"))
    ensure_init_py(os.path.join(module_dir, "workspace"))
    ensure_init_py(os.path.join(app_pkg, "tests"))

    req = json.dumps(required_apps)

    hooks = (
        f'app_name        = "{app_name}"\n'
        f'app_title       = "{app_title}"\n'
        f'app_publisher   = "{app_publisher}"\n'
        f'app_description = "{app_description}"\n'
        f'app_email       = "{app_email}"\n'
        f'app_license     = "{app_license}"\n'
        f'app_version     = "{app_version}"\n\n'
        f'required_apps = {req}\n\n'
        f'after_install    = "{app_name}.setup.after_install"\n'
        f'before_uninstall = "{app_name}.setup.before_uninstall"\n\n'
        f'# doc_events = {{\n'
        f'#     "Sales Invoice": {{\n'
        f'#         "validate": "{app_name}.overrides.sales_invoice.validate"\n'
        f'#     }}\n'
        f'# }}\n\n'
        f'# scheduler_events = {{\n'
        f'#     "daily" : ["{app_name}.tasks.daily"],\n'
        f'# }}\n\n'
        f'fixtures = [\n'
        f'    {{"dt": "Module Def", "filters": [["app_name", "=", "{app_name}"]]}},\n'
        f']\n'
    )

    files = {
        os.path.join(app_root, "setup.py")          : (
            f'from setuptools import setup, find_packages\n'
            f'setup(name="{app_name}", version="{app_version}",\n'
            f'    description="{app_description}", author="{app_publisher}",\n'
            f'    author_email="{app_email}", license="{app_license}",\n'
            f'    packages=find_packages(), zip_safe=False,\n'
            f'    include_package_data=True, install_requires=["frappe"])\n'
        ),
        os.path.join(app_root, "pyproject.toml")    : (
            f'[build-system]\nrequires = ["flit_core >=3.4,<4"]\n'
            f'build-backend = "flit_core.buildapi"\n\n'
            f'[project]\nname = "{app_name}"\nversion = "{app_version}"\n'
        ),
        os.path.join(app_root, "requirements.txt")  : "frappe\n",
        os.path.join(app_root, "MANIFEST.in")       : (
            f"include {app_name}/*/*/*.json\ninclude {app_name}/*/*/*/*.json\n"
            f"include {app_name}/*/*/*.js\ninclude {app_name}/fixtures/*.json\n"
        ),
        os.path.join(app_root, "README.md")         : f"# {app_title}\n\n{app_description}\n",
        os.path.join(app_root, "license.txt")       : f"{app_license} License\nCopyright (c) 2025 {app_publisher}\n",
        os.path.join(app_pkg,  "hooks.py")          : hooks,
        os.path.join(app_pkg,  "__init__.py")       : f'__version__ = "{app_version}"\n',
        os.path.join(app_pkg,  "setup.py")          : (
            f'import frappe\n\ndef after_install():\n\tfrappe.db.commit()\n\t'
            f'print("{app_name} installed.")\n\ndef before_uninstall():\n\tpass\n'
        ),
        os.path.join(app_pkg,  "modules.txt")       : f"{app_name}\n",
        os.path.join(app_pkg,  "patches.txt")       : "# Add patches here\n",
    }

    module_def = [{
        "doctype": "Module Def",
        "name": app_name,
        "module_name": app_name,
        "app_name": app_name,
        "restrict_to_domain": "",
    }]

    created = []
    for path, content in files.items():
        if write_file(path, content, overwrite=overwrite):
            created.append(path)

    module_def_path = os.path.join(app_pkg, "fixtures", "module_def.json")
    if write_json(module_def_path, module_def, overwrite=overwrite):
        created.append(module_def_path)

    # Make importable via .pth file
    importable = _make_importable(app_name, app_root)

    # Register in bench/sites/apps.txt only (not bench/apps.txt)
    apps = _read_txt(_sites_apps_txt())
    if app_name not in apps:
        apps.append(app_name)
        _write_txt(_sites_apps_txt(), apps)

    # Register in bench/sites/apps.json
    _add_to_apps_json(app_name, app_version, app_title, app_publisher,
                      app_description, app_email, app_license)

    _log_scaffold(app_name, app_name, app_root)

    # Verify sites/apps.txt was written
    sites_txt_ok = app_name in _read_txt(_sites_apps_txt())

    return {
        "status"           : "success",
        "message"          : f"App '{app_name}' scaffolded and registered",
        "app_root"         : app_root,
        "importable"       : importable,
        "sites_apps_txt"   : f"{'✓' if sites_txt_ok else '✗'} bench/sites/apps.txt",
        "apps_json"        : "✓ bench/sites/apps.json",
        "next_steps"       : (
            f"bench --site <site> install-app {app_name}\n"
            f"bench --site <site> migrate"
        ),
        "files"            : created,
    }


# ─────────────────────────────────────────────────────────────────
# LIST SITES
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_bench_sites():
    """Return all sites with their installed apps list."""
    sites_path = _sites_dir()
    sites = []
    if not os.path.exists(sites_path):
        return {"status": "success", "sites": []}

    for item in sorted(os.listdir(sites_path)):
        site_path = os.path.join(sites_path, item)
        if os.path.isdir(site_path) and os.path.exists(os.path.join(site_path, "site_config.json")):
            installed = _read_txt(os.path.join(site_path, "apps.txt"))
            sites.append({"site": item, "installed": installed, "app_count": len(installed)})

    return {"status": "success", "sites": sites}


# ─────────────────────────────────────────────────────────────────
# LIST BENCH APPS
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_bench_apps():
    """Return all apps in bench/apps/ with accurate metadata from hooks.py."""
    bench_path   = _bench()
    apps_dir     = _apps_dir()
    apps_json    = _read_json(_apps_json())

    # bench/apps.txt — present only for apps registered via install/register (not scaffold)
    bench_registered = set(_read_txt(_bench_apps_txt()))
    # sites/apps.txt — written by both scaffold and bench; canonical registration check
    sites_registered = set(_read_txt(_sites_apps_txt()))

    # Build site install map: {app: [site1, site2, ...]}
    site_installs = {}
    sites_path = _sites_dir()
    if os.path.exists(sites_path):
        for site in os.listdir(sites_path):
            for a in _read_txt(os.path.join(sites_path, site, "apps.txt")):
                site_installs.setdefault(a, []).append(site)

    result = []
    if not os.path.exists(apps_dir):
        return {"status": "success", "apps": []}

    for item in sorted(os.listdir(apps_dir)):
        item_path = os.path.join(apps_dir, item)
        if not os.path.isdir(item_path):
            continue
        if not os.path.exists(os.path.join(item_path, item, "hooks.py")):
            continue

        version     = _hooks_attr(item, "app_version") or "—"
        title       = _hooks_attr(item, "app_title")   or item
        publisher   = _hooks_attr(item, "app_publisher") or "—"
        description = _hooks_attr(item, "app_description") or ""
        license_    = _hooks_attr(item, "app_license") or "—"

        installed_on = site_installs.get(item, [])

        result.append({
            "app"             : item,
            "version"         : version,
            "title"           : title,
            "publisher"       : publisher,
            "description"     : description,
            "license"         : license_,
            "in_bench_txt"    : item in bench_registered,
            "in_sites_txt"    : item in sites_registered,
            "in_apps_json"    : item in apps_json,
            "installed_on"    : installed_on,
            "install_count"   : len(installed_on),
        })

    return {"status": "success", "apps": result}


# ─────────────────────────────────────────────────────────────────
# INSTALL APP ON SITE
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def install_app_on_site(app_name, site, force=0):
    """
    Install an app on a site using: bench --site <site> install-app <app>

    Pre-flight steps:
    1. Verify app folder and hooks.py exist
    2. Make app importable via .pth file
    3. Add to bench/apps.txt (bench regenerates sites/apps.txt from this)
    4. Add to sites/apps.json
    5. Run bench install-app
    """
    bench_path = _bench()
    app_root   = os.path.join(bench_path, "apps", app_name)
    pkg_hooks  = os.path.join(app_root, app_name, "hooks.py")

    # Step 1: verify
    if not os.path.exists(app_root):
        return {"status": "error", "message": f"App folder not found: {app_root}"}
    if not os.path.exists(pkg_hooks):
        return {"status": "error", "message": f"hooks.py missing: {pkg_hooks}"}

    # Step 2: make importable
    importable = _make_importable(app_name, app_root)

    # Step 3: add to BOTH bench/apps.txt and bench/sites/apps.txt
    bench_txt_added = _add_to_bench_apps_txt(app_name)
    # Verify both were written
    bench_ok = app_name in _read_txt(_bench_apps_txt())
    sites_ok = app_name in _read_txt(_sites_apps_txt())

    # Step 4: add to apps.json
    if app_name not in _read_json(_apps_json()):
        _add_to_apps_json(app_name, _app_version(app_name))

    # Step 5: run bench install-app
    cmd = ["bench", "--site", site, "install-app", app_name]
    if int(force):
        cmd.append("--force")

    result = subprocess.run(cmd, cwd=bench_path, capture_output=True, text=True)
    success = result.returncode == 0

    return {
        "status"      : "success" if success else "error",
        "message"     : f"App '{app_name}' {'installed on' if success else 'failed on'} site '{site}'",
        "importable"  : importable,
        "bench_apps_txt"  : f"{'✓' if bench_ok else '✗'} bench/apps.txt",
        "sites_apps_txt"  : f"{'✓' if sites_ok else '✗'} bench/sites/apps.txt",
        "stdout"      : result.stdout,
        "stderr"      : result.stderr,
    }


# ─────────────────────────────────────────────────────────────────
# UNINSTALL APP FROM SITE
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def uninstall_app_from_site(app_name, site, dry_run=0):
    """Uninstall an app from a site: bench --site <site> uninstall-app <app>"""
    if app_name in ("frappe", "erpnext", "hrms"):
        return {"status": "error", "message": f"Cannot uninstall core app '{app_name}'."}

    bench_path = _bench()
    cmd = ["bench", "--site", site, "uninstall-app", app_name]
    if int(dry_run):
        cmd.append("--dry-run")

    result = subprocess.run(cmd, cwd=bench_path, capture_output=True, text=True)
    return {
        "status" : "success" if result.returncode == 0 else "error",
        "message": f"App '{app_name}' {'(dry-run) ' if int(dry_run) else ''}uninstalled from '{site}'",
        "stdout" : result.stdout,
        "stderr" : result.stderr,
    }


# ─────────────────────────────────────────────────────────────────
# REGISTER EXISTING APP
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def register_existing_app(app_name):
    """Register an already-existing app in bench/apps.txt and apps.json."""
    bench_path = _bench()
    app_root   = os.path.join(bench_path, "apps", app_name)

    if not os.path.exists(app_root):
        return {"status": "error", "message": f"App folder not found: {app_root}"}

    version     = _hooks_attr(app_name, "app_version") or "0.0.1"
    title       = _hooks_attr(app_name, "app_title")   or app_name
    publisher   = _hooks_attr(app_name, "app_publisher") or ""
    description = _hooks_attr(app_name, "app_description") or ""
    license_    = _hooks_attr(app_name, "app_license") or "MIT"

    _add_to_bench_apps_txt(app_name)
    _add_to_apps_json(app_name, version, title, publisher, description, "", license_)
    importable  = _make_importable(app_name, app_root)

    bench_ok = app_name in _read_txt(_bench_apps_txt())
    sites_ok  = app_name in _read_txt(_sites_apps_txt())

    return {
        "status"        : "success",
        "message"       : f"App '{app_name}' v{version} registered",
        "bench_apps_txt": f"{'✓' if bench_ok else '✗'} bench/apps.txt",
        "sites_apps_txt": f"{'✓' if sites_ok else '✗'} bench/sites/apps.txt",
        "importable"    : importable,
        "version"       : version,
    }


# ─────────────────────────────────────────────────────────────────
# REMOVE APP FROM BENCH
# ─────────────────────────────────────────────────────────────────
@frappe.whitelist()
def remove_app_from_bench(app_name, delete_folder=0):
    """Remove app from bench/apps.txt and apps.json. Optionally delete folder."""
    if app_name in ("frappe", "erpnext", "hrms", "frappe_devkit"):
        return {"status": "error", "message": f"Cannot remove core app '{app_name}'."}

    txt_result   = _remove_from_bench_apps_txt(app_name)
    json_removed = _remove_from_apps_json(app_name)
    folder_msg   = ""

    if int(delete_folder):
        import shutil
        app_root = os.path.join(_bench(), "apps", app_name)
        if os.path.exists(app_root):
            shutil.rmtree(app_root)
            folder_msg = f" | folder deleted"

    return {
        "status" : "success",
        "message": (
            f"bench/apps.txt: {'removed' if txt_result['bench_txt'] else 'not found'} | "
            f"sites/apps.txt: {'removed' if txt_result['sites_txt'] else 'not found'} | "
            f"apps.json: {'removed' if json_removed else 'not found'}"
            f"{folder_msg}"
        ),
    }


# ─────────────────────────────────────────────────────────────────
# LOG
# ─────────────────────────────────────────────────────────────────
def _log_scaffold(name, app, path):
    try:
        log = frappe.new_doc("DevKit Scaffold Log")
        log.action = "App"; log.reference = name; log.app_name = app
        log.module = ""; log.file_path = path
        log.scaffolded_on = str(now_datetime())
        log.insert(ignore_permissions=True); frappe.db.commit()
    except Exception:
        pass
