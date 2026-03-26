"""
Page Builder API for Frappe DevKit Studio.
Manages: WWW Files, Web Pages (CMS), Desk Pages, Web Templates.
"""
import os, re, json, uuid
import frappe
from frappe.utils import get_bench_path


def _bench():
    return get_bench_path()

def _apps_path():
    return os.path.join(_bench(), "apps")

def _app_root(app):
    if not re.match(r'^[\w\-]+$', app):
        frappe.throw("Invalid app name")
    p = os.path.join(_apps_path(), app)
    if not os.path.isdir(p):
        frappe.throw(f"App '{app}' not found")
    return p

def _safe_join(base, *parts):
    """Join path components under base, blocking directory traversal."""
    full = os.path.realpath(os.path.join(base, *parts))
    base_r = os.path.realpath(base)
    if full != base_r and not full.startswith(base_r + os.sep):
        frappe.throw("Invalid path (traversal detected)")
    return full

def _www_dir(app):
    root = _app_root(app)
    inner = app.replace("-", "_")
    for candidate in [
        os.path.join(root, app, "www"),
        os.path.join(root, inner, "www"),
    ]:
        if os.path.isdir(candidate):
            return candidate
    frappe.throw(f"App '{app}' has no www folder")

_EDITABLE = {'.html', '.py', '.md', '.css', '.js', '.json', '.txt', '.xml', '.jinja2'}


# ─────────────────────────── Apps ─────────────────────────────────────────────

@frappe.whitelist()
def list_apps_with_www():
    """List all apps, flagging those with a www/ folder."""
    result = []
    for name in sorted(os.listdir(_apps_path())):
        if name.startswith('.') or name == '__pycache__':
            continue
        root = os.path.join(_apps_path(), name)
        if not os.path.isdir(root):
            continue
        inner = name.replace("-", "_")
        has_www = os.path.isdir(os.path.join(root, name, "www")) or \
                  os.path.isdir(os.path.join(root, inner, "www"))
        result.append({'app': name, 'has_www': has_www})
    return {'apps': result}


@frappe.whitelist()
def list_app_modules(app):
    """List module directories inside the app package by scanning the filesystem.

    Handles two common Frappe patterns:
    1. App has module subdirectories: {inner}/{module}/page/{page_name}/
    2. App puts pages directly under inner package: {inner}/page/{page_name}/
       In this case the inner package name itself is returned as the module.
    """
    root = _app_root(app)
    inner = app.replace("-", "_")
    pkg_dir = None
    for candidate in [os.path.join(root, inner), os.path.join(root, app)]:
        if os.path.isdir(candidate):
            pkg_dir = candidate
            break
    if not pkg_dir:
        return {'modules': []}

    _MODULE_MARKERS = {'doctype', 'page', 'report', 'workspace', 'module_def',
                       'print_format', 'notification', 'dashboard_chart', 'number_card'}
    _SKIP = {'__pycache__', 'templates', 'www', 'public', 'tests', 'patches', 'node_modules'}

    # Check if inner package itself directly contains module markers
    # (e.g. erptheme/erptheme/page/ exists → inner package IS the module)
    pkg_direct = {e for e in os.listdir(pkg_dir) if os.path.isdir(os.path.join(pkg_dir, e))}
    if pkg_direct & _MODULE_MARKERS:
        return {'modules': [inner]}

    # Otherwise find subdirectories that contain module markers
    modules = []
    for name in sorted(os.listdir(pkg_dir)):
        d = os.path.join(pkg_dir, name)
        if not os.path.isdir(d) or name.startswith('.') or name in _SKIP:
            continue
        subdirs = {e for e in os.listdir(d) if os.path.isdir(os.path.join(d, e))}
        if subdirs & _MODULE_MARKERS:
            modules.append(name)
    return {'modules': modules}


# ─────────────────────────── WWW Files ────────────────────────────────────────

@frappe.whitelist()
def list_www_tree(app):
    """Return flat node list for the www folder tree."""
    www = _www_dir(app)
    nodes = []
    for root, dirs, files in os.walk(www):
        dirs[:] = sorted(
            d for d in dirs
            if not d.startswith('.') and d not in ('__pycache__', 'node_modules')
        )
        rel = os.path.relpath(root, www).replace('\\', '/')
        depth = 0 if rel == '.' else rel.count('/') + 1

        if rel != '.':
            nodes.append({
                'type': 'dir', 'name': os.path.basename(root),
                'path': rel, 'depth': depth,
            })

        for fname in sorted(files):
            if fname.startswith('.') or fname.startswith('__'):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in _EDITABLE:
                continue
            fpath = (rel + '/' + fname) if rel != '.' else fname

            # Companion detection
            companion = None
            base_no_ext = os.path.splitext(fpath)[0]
            if ext == '.html' and os.path.exists(os.path.join(www, base_no_ext + '.py')):
                companion = base_no_ext + '.py'
            elif ext == '.py' and os.path.exists(os.path.join(www, base_no_ext + '.html')):
                companion = base_no_ext + '.html'

            nodes.append({
                'type': 'file', 'name': fname, 'path': fpath,
                'depth': depth, 'ext': ext, 'companion': companion,
            })

    return {'tree': nodes, 'www': www}


@frappe.whitelist()
def get_www_file(app, path):
    www = _www_dir(app)
    full = _safe_join(www, path)
    if not os.path.isfile(full):
        frappe.throw(f"File not found: {path}")
    with open(full, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    return {
        'content': content, 'path': path,
        'ext': os.path.splitext(path)[1].lower(),
    }


@frappe.whitelist()
def save_www_file(app, path, content):
    www = _www_dir(app)
    full = _safe_join(www, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    return {'saved': True, 'path': path}


@frappe.whitelist()
def create_www_page(app, route, create_py=1):
    """Create a new www page (.html + optional .py)."""
    www = _www_dir(app)
    # Preserve the user's name — only strip surrounding slashes/spaces and block path traversal
    route = route.strip('/').strip()
    if not route or re.search(r'\.\.', route):
        frappe.throw("Invalid file name")

    # If user didn't include an extension, default to .html
    base, ext = os.path.splitext(route)
    if not ext:
        html_path = _safe_join(www, route + '.html')
        py_path   = _safe_join(www, route + '.py')
        route_key = route
    else:
        html_path = _safe_join(www, route)
        py_path   = _safe_join(www, base + '.py')
        route_key = route

    if os.path.exists(html_path):
        frappe.throw(f"File '{os.path.basename(html_path)}' already exists")

    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    leaf = os.path.splitext(os.path.basename(route_key))[0]
    title = leaf.replace('-', ' ').replace('_', ' ').title()
    css_class = leaf.replace('_', '-')

    html_body = (
        '{% extends "templates/web.html" %}\n\n'
        '{% block title %}{{ title }}{% endblock %}\n\n'
        '{% block head_include %}\n'
        f'<link rel="stylesheet" href="/assets/{app}/css/{css_class}.css">\n'
        '{% endblock %}\n\n'
        '{% block page_content %}\n'
        f'<div class="{css_class}-wrapper container my-5">\n'
        '    <h1>{{ title }}</h1>\n'
        '    <div class="row">\n'
        '        <div class="col-md-8">\n'
        '            <!-- Your content here -->\n'
        '        </div>\n'
        '    </div>\n'
        '</div>\n'
        '{% endblock %}\n\n'
        '{% block script %}\n'
        '<script>\n'
        '    // Page scripts\n'
        '</script>\n'
        '{% endblock %}\n'
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_body)

    created = [os.path.relpath(html_path, www)]

    if int(create_py):
        py_body = (
            'import frappe\n\n'
            'no_cache = 1\n\n\n'
            'def get_context(context):\n'
            f'    context.title = "{title}"\n'
            '    # context.records = frappe.get_all("DocType", fields=["name"])\n'
            '    return context\n'
        )
        with open(py_path, 'w', encoding='utf-8') as f:
            f.write(py_body)
        created.append(os.path.relpath(py_path, www))

    html_rel = os.path.relpath(html_path, www)
    return {'created': created, 'route': route_key, 'path': html_rel}


@frappe.whitelist()
def delete_www_file(app, path):
    www = _www_dir(app)
    full = _safe_join(www, path)
    if not os.path.isfile(full):
        frappe.throw(f"File not found: {path}")
    os.remove(full)
    return {'deleted': path}


# ─────────────────────────── Web Pages (CMS) ──────────────────────────────────

def _site_cfg(site):
    p = os.path.join(_bench(), "sites", site, "site_config.json")
    if not os.path.exists(p):
        frappe.throw(f"Site '{site}' not found")
    with open(p) as f:
        return json.load(f)

def _db(site):
    import pymysql
    cfg = _site_cfg(site)
    return pymysql.connect(
        host=cfg.get("db_host", "localhost"),
        port=int(cfg.get("db_port", 3306)),
        user=cfg.get("db_name"), password=cfg.get("db_password"),
        db=cfg.get("db_name"), charset="utf8mb4",
        connect_timeout=5, autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )

def _ser(v):
    return v.isoformat() if hasattr(v, 'isoformat') else v


@frappe.whitelist()
def list_web_pages(site):
    conn = _db(site)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, title, route, published, content_type,
                       DATE_FORMAT(modified,'%Y-%m-%d %H:%i') AS modified,
                       meta_description
                FROM `tabWeb Page`
                ORDER BY modified DESC
            """)
            return {'pages': cur.fetchall()}
    finally:
        conn.close()


@frappe.whitelist()
def get_web_page(site, name):
    conn = _db(site)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM `tabWeb Page` WHERE name=%s", (name,))
            page = cur.fetchone()
            if not page:
                frappe.throw(f"Web Page '{name}' not found")
            cur.execute("""
                SELECT idx, web_template, web_template_values, css_class,
                       section_id, add_container, hide_block, add_shade,
                       add_top_padding, add_bottom_padding
                FROM `tabWeb Page Block`
                WHERE parent=%s AND parentfield='page_blocks'
                ORDER BY idx
            """, (name,))
            page['page_blocks'] = cur.fetchall()
        for k in list(page.keys()):
            page[k] = _ser(page[k])
        return {'page': page}
    finally:
        conn.close()


@frappe.whitelist()
def save_web_page(site, name, data):
    """Save web page fields. `data` is a JSON-encoded dict of fields to update."""
    d = json.loads(data) if isinstance(data, str) else data
    allowed = {
        'title', 'route', 'published', 'content_type',
        'main_section', 'main_section_md', 'main_section_html',
        'css', 'javascript', 'context_script', 'insert_style',
        'meta_title', 'meta_description', 'meta_image',
        'show_title', 'full_width', 'header', 'breadcrumbs',
    }
    sets = {k: v for k, v in d.items() if k in allowed}
    if not sets:
        return {'saved': True}
    conn = _db(site)
    try:
        cols = ', '.join(f'`{k}`=%s' for k in sets)
        vals = list(sets.values()) + [name]
        with conn.cursor() as cur:
            cur.execute(f"UPDATE `tabWeb Page` SET {cols}, modified=NOW() WHERE name=%s", vals)
        return {'saved': True}
    finally:
        conn.close()


@frappe.whitelist()
def create_web_page(site, title, route, content_type='HTML'):
    name = re.sub(r'[^\w\-]', '-', title.lower()).strip('-') or uuid.uuid4().hex[:8]
    conn = _db(site)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM `tabWeb Page` WHERE name=%s", (name,))
            if cur.fetchone():
                name = name + '-' + uuid.uuid4().hex[:5]
            cur.execute("""
                INSERT INTO `tabWeb Page`
                (name, title, route, published, content_type, show_title,
                 docstatus, creation, modified, modified_by, owner, idx)
                VALUES (%s,%s,%s,0,%s,1,0,NOW(),NOW(),'Administrator','Administrator',0)
            """, (name, title, route.strip('/'), content_type))
        return {'name': name, 'created': True}
    finally:
        conn.close()


@frappe.whitelist()
def delete_web_page(site, name):
    conn = _db(site)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM `tabWeb Page Block` WHERE parent=%s", (name,))
            cur.execute("DELETE FROM `tabWeb Page` WHERE name=%s", (name,))
        return {'deleted': True}
    finally:
        conn.close()


@frappe.whitelist()
def toggle_published(site, name, published):
    conn = _db(site)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE `tabWeb Page` SET published=%s, modified=NOW() WHERE name=%s",
                (int(published), name)
            )
        return {'published': int(published)}
    finally:
        conn.close()


@frappe.whitelist()
def get_site_url(site):
    """Return the base URL of a site for preview links."""
    cfg = _site_cfg(site)
    url = cfg.get('host_name') or f'http://{site}'
    if not url.startswith('http'):
        url = 'http://' + url
    return {'url': url.rstrip('/')}


# ─────────────────────────── Desk Pages ───────────────────────────────────────

def _find_page_dirs(app):
    root = _app_root(app)
    pages = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', 'node_modules', '.git', 'dist')]
        if os.path.basename(dirpath) == 'page':
            for page_name in sorted(d for d in dirs if not d.startswith('.')):
                pdir = os.path.join(dirpath, page_name)
                pfiles = sorted(
                    f for f in os.listdir(pdir)
                    if not f.startswith('.') and os.path.isfile(os.path.join(pdir, f))
                )
                # Include files from templates/ subfolder as "templates/{name}"
                tpl_dir = os.path.join(pdir, 'templates')
                if os.path.isdir(tpl_dir):
                    for tf in sorted(os.listdir(tpl_dir)):
                        if not tf.startswith('.') and os.path.isfile(os.path.join(tpl_dir, tf)):
                            pfiles.append('templates/' + tf)
                rel = os.path.relpath(pdir, root).replace('\\', '/')
                pages.append({
                    'name': page_name,
                    'path': rel,
                    'files': pfiles,
                    'module': os.path.relpath(os.path.dirname(dirpath), root).replace('\\', '/'),
                })
    return pages


@frappe.whitelist()
def list_desk_pages(app):
    return {'pages': _find_page_dirs(app)}


@frappe.whitelist()
def get_desk_page_file(app, rel_page_path, filename):
    root = _app_root(app)
    full = _safe_join(root, rel_page_path, filename)
    if not os.path.isfile(full):
        frappe.throw(f"File '{filename}' not found")
    with open(full, 'r', encoding='utf-8', errors='replace') as f:
        return {'content': f.read(), 'filename': filename,
                'ext': os.path.splitext(filename)[1].lower()}


@frappe.whitelist()
def save_desk_page_file(app, rel_page_path, filename, content):
    root = _app_root(app)
    full = _safe_join(root, rel_page_path, filename)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    return {'saved': True}


@frappe.whitelist()
def update_desk_page_meta(app, rel_page_path, title, roles=None):
    """Update the title and roles in a desk page's .json definition file."""
    root = _app_root(app)
    page_dir = _safe_join(root, rel_page_path)
    if not os.path.isdir(page_dir):
        frappe.throw(f"Page directory not found: {rel_page_path}")

    page_name = os.path.basename(page_dir)
    json_file = _safe_join(page_dir, page_name + ".json")
    if not os.path.isfile(json_file):
        frappe.throw(f"Page definition file '{page_name}.json' not found")

    with open(json_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    meta['title'] = title

    if roles is not None:
        parsed_roles = json.loads(roles) if isinstance(roles, str) else roles
        meta['roles'] = [
            {"doctype": "Has Role", "role": r.strip()}
            for r in parsed_roles if r.strip()
        ]

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=1)

    return {'updated': True, 'title': title}


@frappe.whitelist()
def get_desk_page_meta(app, rel_page_path):
    """Return parsed metadata from a desk page's .json definition file."""
    root = _app_root(app)
    page_dir = _safe_join(root, rel_page_path)
    page_name = os.path.basename(page_dir)
    json_file = _safe_join(page_dir, page_name + ".json")
    if not os.path.isfile(json_file):
        frappe.throw(f"Page definition file '{page_name}.json' not found")
    with open(json_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    roles = [r.get('role', '') for r in meta.get('roles', []) if r.get('role')]
    return {'title': meta.get('title', page_name), 'roles': roles, 'module': meta.get('module', '')}


@frappe.whitelist()
def delete_desk_page(app, rel_page_path):
    """Delete all files in a desk page directory and remove the directory."""
    import shutil
    root = _app_root(app)
    page_dir = _safe_join(root, rel_page_path)
    if not os.path.isdir(page_dir):
        frappe.throw(f"Page directory not found: {rel_page_path}")
    shutil.rmtree(page_dir)
    return {'deleted': True, 'path': rel_page_path}


# ─────────────────────────── Web Templates ────────────────────────────────────

@frappe.whitelist()
def create_desk_page(app, module, page_name, title):
    """Create a new Frappe desk page with boilerplate files in {module}/page/{page_name}/."""
    root = _app_root(app)
    if not re.match(r'^[\w\s\-\.]+$', module):
        frappe.throw("Invalid module name")
    if not re.match(r'^[\w\-]+$', page_name):
        frappe.throw("Invalid page name (letters, numbers, hyphens only)")

    inner = app.replace("-", "_")
    mod_snake = module.lower().replace(" ", "_").replace("-", "_")

    mod_dir = None
    for candidate in [
        os.path.join(root, inner, mod_snake),
        os.path.join(root, app,   mod_snake),
        os.path.join(root, inner, module),
    ]:
        if os.path.isdir(candidate):
            mod_dir = candidate
            break

    if not mod_dir:
        mod_dir = os.path.join(root, inner, mod_snake)
        os.makedirs(mod_dir, exist_ok=True)

    page_dir = _safe_join(root, os.path.relpath(mod_dir, root), "page", page_name)
    if os.path.exists(page_dir):
        frappe.throw(f"Desk page '{page_name}' already exists")
    os.makedirs(page_dir)

    # templates/ subfolder
    tpl_dir = os.path.join(page_dir, "templates")
    os.makedirs(tpl_dir, exist_ok=True)

    # relative template path used in render_template (from app inner package root)
    rel_from_inner = os.path.relpath(page_dir, os.path.join(root, inner)).replace("\\", "/")
    tpl_path = f"{inner}/{rel_from_inner}/templates/{page_name}.html"

    # Python module path from apps/ (sys.path root): {app}.{path_from_app_root}.{page_name}
    rel_from_root = os.path.relpath(page_dir, root).replace("\\", "/")

    fn_name = page_name.replace("-", "_")

    # .json
    page_meta = {
        "doctype": "Page", "name": page_name, "page_name": page_name,
        "title": title, "module": module,
        "roles": [{"doctype": "Has Role", "role": "System Manager"}],
    }
    with open(os.path.join(page_dir, page_name + ".json"), "w") as f:
        json.dump(page_meta, f, indent=1)

    # .py
    py_body = (
        f"import frappe\n\n\n"
        f"@frappe.whitelist()\n"
        f"def get_{fn_name}():\n"
        f"    context = {{\n"
        f"        # \"records\": frappe.get_all(\"DocType\", fields=[\"name\"])\n"
        f"    }}\n"
        f"    html = frappe.render_template(\"{tpl_path}\", context)\n"
        f"    return html\n"
    )
    with open(os.path.join(page_dir, page_name + ".py"), "w") as f:
        f.write(py_body)

    # .js
    method_path = f"{app}.{rel_from_root.replace('/', '.')}.{fn_name}.get_{fn_name}"
    js_body = (
        f'frappe.pages["{page_name}"].on_page_load = function(wrapper) {{\n'
        f'\tvar page = frappe.ui.make_app_page({{\n'
        f'\t\tparent: wrapper,\n'
        f'\t\ttitle: "{title}"\n'
        f'\t}});\n\n'
        f'\tfrappe.call({{\n'
        f'\t\tmethod: "{method_path}",\n'
        f'\t\tcallback: function(r) {{\n'
        f'\t\t\t$(page.main).html(r.message);\n'
        f'\t\t}}\n'
        f'\t}});\n'
        f'}};\n'
    )
    with open(os.path.join(page_dir, page_name + ".js"), "w") as f:
        f.write(js_body)

    # .html (Frappe page-level wrapper, usually left minimal)
    with open(os.path.join(page_dir, page_name + ".html"), "w") as f:
        f.write(f"<!-- Page wrapper for {title} -->\n")

    # templates/{page_name}.html
    tpl_body = (
        f"<div class=\"{page_name}-wrapper\">\n"
        f"\t<h3>{title}</h3>\n"
        f"\t{{# Add your HTML here. Context variables are available as template variables. #}}\n"
        f"</div>\n"
    )
    with open(os.path.join(tpl_dir, page_name + ".html"), "w") as f:
        f.write(tpl_body)

    return {
        "created": True,
        "path": os.path.relpath(page_dir, root).replace("\\", "/"),
        "page_name": page_name,
    }


@frappe.whitelist()
def list_web_templates():
    """List all Frappe web templates available in the bench."""
    templates = []
    for app_name in sorted(os.listdir(_apps_path())):
        ap = os.path.join(_apps_path(), app_name)
        if not os.path.isdir(ap):
            continue
        for dirpath, dirs, _ in os.walk(ap):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', 'node_modules', '.git')]
            if os.path.basename(dirpath) == 'web_template':
                for tpl in sorted(os.listdir(dirpath)):
                    tdir = os.path.join(dirpath, tpl)
                    if not os.path.isdir(tdir):
                        continue
                    jf = os.path.join(tdir, tpl + '.json')
                    if not os.path.isfile(jf):
                        continue
                    try:
                        with open(jf) as f:
                            meta = json.load(f)
                    except Exception:
                        continue
                    templates.append({
                        'name': tpl,
                        'title': meta.get('title', tpl.replace('_', ' ').title()),
                        'app': app_name,
                        'fields': [
                            {
                                'fieldname': fd.get('fieldname'),
                                'label': fd.get('label') or fd.get('fieldname', '').replace('_', ' ').title(),
                                'fieldtype': fd.get('fieldtype', 'Data'),
                                'default': fd.get('default', ''),
                                'options': fd.get('options', ''),
                            }
                            for fd in meta.get('fields', [])
                            if fd.get('fieldtype') not in ('Section Break', 'Column Break', 'Tab Break')
                               and fd.get('fieldname')
                        ],
                    })
    return {'templates': templates}
