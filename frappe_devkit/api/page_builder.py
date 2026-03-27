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
def create_www_page(app, route, create_py=1, preset='blank'):
    """Create a new www page (.html + optional .py) from a preset template."""
    www = _www_dir(app)
    route = route.strip('/').strip()
    if not route or re.search(r'\.\.', route):
        frappe.throw("Invalid file name")

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
    leaf      = os.path.splitext(os.path.basename(route_key))[0]
    title     = leaf.replace('-', ' ').replace('_', ' ').title()
    css_class = leaf.replace('_', '-')
    preset    = (preset or 'blank').strip()

    html_body = _www_html_template(preset, title, css_class, app)
    py_body   = _www_py_template(preset, title, app)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_body)

    created = [os.path.relpath(html_path, www)]

    if int(create_py):
        with open(py_path, 'w', encoding='utf-8') as f:
            f.write(py_body)
        created.append(os.path.relpath(py_path, www))

    html_rel = os.path.relpath(html_path, www)
    return {'created': created, 'route': route_key, 'path': html_rel}


def _www_html_template(preset, title, css_class, app):
    """Return boilerplate HTML for a www page based on the chosen preset."""

    # ── SHARED header ────────────────────────────────────────────────────────
    head = (
        '{{% extends "templates/web.html" %}}\n\n'
        '{{% block title %}}{{{{ title }}}}{{% endblock %}}\n\n'
        '{{% block head_include %}}\n'
        '<!-- ── Page-specific CSS ────────────────────────────── -->\n'
        '<style>\n'
        '  /* ── CSS custom properties (change once, apply everywhere) ── */\n'
        '  :root {{\n'
        '    --brand:        #5c4da8;   /* primary brand colour */\n'
        '    --brand-light:  #ede9fe;   /* tinted background */\n'
        '    --accent:       #8b5cf6;   /* hover / highlight */\n'
        '    --text-dark:    #1e1b3a;   /* headings */\n'
        '    --text-muted:   #6b7280;   /* secondary text */\n'
        '    --radius:       10px;\n'
        '    --shadow:       0 4px 20px rgba(92,77,168,.12);\n'
        '  }}\n'
        '  .{css_class}-wrapper {{ font-family: inherit; }}\n'
        '</style>\n'
        '{{% endblock %}}\n\n'
    ).format(css_class=css_class, app=app)

    foot = (
        '\n{{% block script %}}\n'
        '<script>\n'
        '// ── Page JavaScript ──────────────────────────────────────────────\n'
        '// frappe.ready() fires after DOM + Frappe libs are loaded.\n'
        '// Uncomment and extend patterns you need:\n\n'
        '// frappe.ready(function() {{\n'
        '//   // 1. Show a toast notification\n'
        '//   // frappe.show_alert({{ message: "Page loaded", indicator: "green" }}, 3);\n\n'
        '//   // 2. Call a whitelisted Python method\n'
        '//   // frappe.call({{\n'
        '//   //   method: "{app}.api.my_module.my_method",\n'
        '//   //   args: {{ key: "value" }},\n'
        '//   //   callback: r => console.log(r.message)\n'
        '//   // }});\n\n'
        '//   // 3. Handle form submit\n'
        '//   // $("form#{css_class}-form").on("submit", function(e) {{\n'
        '//   //   e.preventDefault();\n'
        '//   //   const data = Object.fromEntries(new FormData(this));\n'
        '//   //   frappe.call({{ method: "...", args: data, callback: r => {{}} }});\n'
        '//   // }});\n\n'
        '//   // 4. Redirect if not logged in\n'
        '//   // if (!frappe.session.user || frappe.session.user === "Guest") {{\n'
        '//   //   window.location.href = "/login?redirect-to=" + window.location.pathname;\n'
        '//   // }}\n'
        '// }});\n'
        '</script>\n'
        '{{% endblock %}}\n'
    ).format(app=app, css_class=css_class)

    # ── PRESET bodies ─────────────────────────────────────────────────────────

    if preset == 'landing':
        body = (
            '{{% block page_content %}}\n'
            '<div class="{css_class}-wrapper">\n\n'
            '  <!-- ══ HERO SECTION ══════════════════════════════════════════ -->\n'
            '  <section class="hero-section py-5" style="background:linear-gradient(135deg,var(--brand) 0%,var(--accent) 100%);color:#fff">\n'
            '    <div class="container py-5 text-center">\n'
            '      <h1 class="display-4 fw-bold">{{{{ title }}}}</h1>\n'
            '      <p class="lead mt-3 opacity-75">Your compelling subtitle goes here — one powerful sentence.</p>\n'
            '      <!-- ── Primary CTA ── -->\n'
            '      <div class="mt-4 d-flex gap-3 justify-content-center flex-wrap">\n'
            '        <a href="#contact" class="btn btn-light btn-lg px-5 fw-semibold" style="color:var(--brand)">Get Started</a>\n'
            '        <a href="#features" class="btn btn-outline-light btn-lg px-5">Learn More</a>\n'
            '      </div>\n'
            '      <!-- Optional hero image / animation placeholder -->\n'
            '      <!-- <img src="/assets/{app}/images/hero.svg" alt="Hero" class="img-fluid mt-5" style="max-height:320px"> -->\n'
            '    </div>\n'
            '  </section>\n\n'
            '  <!-- ══ FEATURES SECTION ════════════════════════════════════════ -->\n'
            '  <section id="features" class="py-5 bg-white">\n'
            '    <div class="container">\n'
            '      <h2 class="text-center fw-bold mb-2" style="color:var(--text-dark)">Why Choose Us</h2>\n'
            '      <p class="text-center text-muted mb-5">Three reasons that set us apart.</p>\n'
            '      <div class="row g-4">\n'
            '        {{% for feature in features %}}\n'
            '        <!-- features list comes from get_context(); see the .py file -->\n'
            '        <div class="col-md-4">\n'
            '          <div class="card h-100 border-0 text-center p-4" style="border-radius:var(--radius);box-shadow:var(--shadow)">\n'
            '            <div style="font-size:2.5rem">{{{{ feature.icon }}}}</div>\n'
            '            <h5 class="fw-bold mt-3" style="color:var(--text-dark)">{{{{ feature.title }}}}</h5>\n'
            '            <p class="text-muted small">{{{{ feature.desc }}}}</p>\n'
            '          </div>\n'
            '        </div>\n'
            '        {{% endfor %}}\n'
            '      </div>\n'
            '    </div>\n'
            '  </section>\n\n'
            '  <!-- ══ STATS BAND ════════════════════════════════════════════ -->\n'
            '  <!-- Uncomment to show stat numbers -->\n'
            '  <!-- <section class="py-4" style="background:var(--brand-light)">\n'
            '    <div class="container">\n'
            '      <div class="row text-center g-4">\n'
            '        <div class="col-6 col-md-3"><div class="display-6 fw-black" style="color:var(--brand)">500+</div><small class="text-muted">Happy Clients</small></div>\n'
            '        <div class="col-6 col-md-3"><div class="display-6 fw-black" style="color:var(--brand)">99%</div><small class="text-muted">Uptime</small></div>\n'
            '        <div class="col-6 col-md-3"><div class="display-6 fw-black" style="color:var(--brand)">24/7</div><small class="text-muted">Support</small></div>\n'
            '        <div class="col-6 col-md-3"><div class="display-6 fw-black" style="color:var(--brand)">10+</div><small class="text-muted">Years Experience</small></div>\n'
            '      </div>\n'
            '    </div>\n'
            '  </section> -->\n\n'
            '  <!-- ══ CONTACT / CTA SECTION ═══════════════════════════════════ -->\n'
            '  <section id="contact" class="py-5">\n'
            '    <div class="container">\n'
            '      <div class="row justify-content-center">\n'
            '        <div class="col-lg-6 text-center">\n'
            '          <h2 class="fw-bold mb-3" style="color:var(--text-dark)">Get In Touch</h2>\n'
            '          <p class="text-muted mb-4">Ready to start? Drop us a message.</p>\n'
            '          <a href="/contact" class="btn btn-lg px-5 fw-semibold" style="background:var(--brand);color:#fff;border-radius:var(--radius)">Contact Us</a>\n'
            '        </div>\n'
            '      </div>\n'
            '    </div>\n'
            '  </section>\n\n'
            '</div>\n'
            '{{% endblock %}}\n'
        ).format(css_class=css_class, app=app)

    elif preset == 'product_detail':
        body = (
            '{{% block page_content %}}\n'
            '<div class="{css_class}-wrapper container my-5">\n\n'
            '  <!-- Product Detail Layout -->\n'
            '  <div class="row g-5">\n\n'
            '    <!-- ── Left: Image Gallery ── -->\n'
            '    <div class="col-lg-5">\n'
            '      <!-- Main image -->\n'
            '      <div class="rounded-3 overflow-hidden mb-3" style="background:#f8f5ff;aspect-ratio:1;display:flex;align-items:center;justify-content:center">\n'
            '        {{% if item.website_image %}}\n'
            '          <img src="{{{{ item.website_image }}}}" alt="{{{{ item.item_name }}}}" class="img-fluid">\n'
            '        {{% else %}}\n'
            '          <span style="font-size:4rem;opacity:.3">📦</span>\n'
            '        {{% endif %}}\n'
            '      </div>\n'
            '      <!-- Thumbnail strip — uncomment when you have multiple images -->\n'
            '      <!-- <div class="d-flex gap-2 flex-wrap">\n'
            '        <img src="..." class="rounded" style="width:72px;height:72px;object-fit:cover;cursor:pointer;border:2px solid var(--brand)">\n'
            '      </div> -->\n'
            '    </div>\n\n'
            '    <!-- ── Right: Details ── -->\n'
            '    <div class="col-lg-7">\n'
            '      <p class="text-muted small mb-1">{{{{ item.item_group }}}}</p>\n'
            '      <h1 class="fw-bold" style="color:var(--text-dark)">{{{{ item.item_name }}}}</h1>\n'
            '      <!-- Price block -->\n'
            '      <div class="my-3">\n'
            '        <span class="fs-3 fw-bold" style="color:var(--brand)">{{{{ frappe.format_value(item.standard_rate, dict(fieldtype="Currency")) }}}}</span>\n'
            '        <!-- <span class="text-muted text-decoration-line-through ms-2 fs-5">Old Price</span> -->\n'
            '      </div>\n'
            '      <!-- Short description -->\n'
            '      <p class="text-muted">{{{{ item.description or "No description available." }}}}</p>\n'
            '      <!-- Add to Cart / Enquiry -->\n'
            '      <div class="d-flex gap-3 mt-4 flex-wrap">\n'
            '        <button class="btn btn-lg fw-semibold px-5" style="background:var(--brand);color:#fff;border-radius:var(--radius)" onclick="addToCart(\'{{{{ item.name }}}}\')">Add to Cart</button>\n'
            '        <a href="/contact?item={{{{ item.name }}}}" class="btn btn-outline-secondary btn-lg px-4">Enquire</a>\n'
            '      </div>\n'
            '      <!-- Spec table -->\n'
            '      <table class="table table-sm mt-4">\n'
            '        <tbody>\n'
            '          <tr><td class="text-muted">SKU</td><td class="fw-semibold">{{{{ item.item_code }}}}</td></tr>\n'
            '          <tr><td class="text-muted">Brand</td><td class="fw-semibold">{{{{ item.brand or "—" }}}}</td></tr>\n'
            '          <tr><td class="text-muted">UOM</td><td class="fw-semibold">{{{{ item.stock_uom }}}}</td></tr>\n'
            '        </tbody>\n'
            '      </table>\n'
            '    </div>\n'
            '  </div>\n\n'
            '  <!-- ── Related Items ── -->\n'
            '  <!-- <div class="mt-5">\n'
            '    <h4 class="fw-bold mb-4">Related Items</h4>\n'
            '    <div class="row g-3">\n'
            '      {{% for rel in related_items %}}\n'
            '      <div class="col-6 col-md-3"><a href="/{{{{ rel.route }}}}">{{{{ rel.item_name }}}}</a></div>\n'
            '      {{% endfor %}}\n'
            '    </div>\n'
            '  </div> -->\n\n'
            '</div>\n'
            '{{% endblock %}}\n'
        ).format(css_class=css_class, app=app)

    elif preset == 'contact_form':
        body = (
            '{{% block page_content %}}\n'
            '<div class="{css_class}-wrapper py-5">\n'
            '  <div class="container">\n'
            '    <div class="row justify-content-center">\n'
            '      <div class="col-lg-7">\n\n'
            '        <!-- ── Header ── -->\n'
            '        <div class="text-center mb-5">\n'
            '          <h1 class="fw-bold" style="color:var(--text-dark)">{{{{ title }}}}</h1>\n'
            '          <p class="text-muted">Fill in the form and we\'ll get back to you.</p>\n'
            '        </div>\n\n'
            '        <!-- ── Contact Form ── -->\n'
            '        <div class="card border-0 p-4 p-md-5" style="border-radius:var(--radius);box-shadow:var(--shadow)">\n'
            '          <form id="{css_class}-form" method="POST" action="/api/method/{app}.www.contact.submit_contact_form" novalidate>\n'
            '            <input type="hidden" name="csrf_token" value="{{{{ frappe.session.csrf_token }}}}">\n'
            '            <div class="row g-3">\n'
            '              <div class="col-md-6">\n'
            '                <label class="form-label fw-semibold">Full Name <span class="text-danger">*</span></label>\n'
            '                <input type="text" name="full_name" class="form-control" placeholder="Your name" required>\n'
            '              </div>\n'
            '              <div class="col-md-6">\n'
            '                <label class="form-label fw-semibold">Email <span class="text-danger">*</span></label>\n'
            '                <input type="email" name="email" class="form-control" placeholder="you@example.com" required>\n'
            '              </div>\n'
            '              <div class="col-12">\n'
            '                <label class="form-label fw-semibold">Phone</label>\n'
            '                <input type="tel" name="phone" class="form-control" placeholder="+1 234 567 8900">\n'
            '              </div>\n'
            '              <div class="col-12">\n'
            '                <label class="form-label fw-semibold">Subject <span class="text-danger">*</span></label>\n'
            '                <input type="text" name="subject" class="form-control" placeholder="How can we help?" required>\n'
            '              </div>\n'
            '              <div class="col-12">\n'
            '                <label class="form-label fw-semibold">Message <span class="text-danger">*</span></label>\n'
            '                <textarea name="message" class="form-control" rows="5" placeholder="Your message…" required></textarea>\n'
            '              </div>\n'
            '              <!-- File attachment — uncomment if needed -->\n'
            '              <!-- <div class="col-12">\n'
            '                <label class="form-label fw-semibold">Attachment</label>\n'
            '                <input type="file" name="attachment" class="form-control">\n'
            '              </div> -->\n'
            '              <div class="col-12 mt-2">\n'
            '                <button type="submit" class="btn btn-lg w-100 fw-semibold" style="background:var(--brand);color:#fff;border-radius:var(--radius)">\n'
            '                  Send Message\n'
            '                </button>\n'
            '              </div>\n'
            '            </div>\n'
            '          </form>\n'
            '          <!-- Success / error alert (shown by JS) -->\n'
            '          <div id="form-alert" class="alert mt-3 d-none"></div>\n'
            '        </div>\n\n'
            '        <!-- ── Contact Info Cards ── -->\n'
            '        <div class="row g-3 mt-4 text-center">\n'
            '          <div class="col-4"><div class="p-3" style="background:var(--brand-light);border-radius:var(--radius)"><div style="font-size:1.5rem">📧</div><small class="text-muted">info@example.com</small></div></div>\n'
            '          <div class="col-4"><div class="p-3" style="background:var(--brand-light);border-radius:var(--radius)"><div style="font-size:1.5rem">📞</div><small class="text-muted">+1 234 567</small></div></div>\n'
            '          <div class="col-4"><div class="p-3" style="background:var(--brand-light);border-radius:var(--radius)"><div style="font-size:1.5rem">📍</div><small class="text-muted">Your City</small></div></div>\n'
            '        </div>\n\n'
            '      </div>\n'
            '    </div>\n'
            '  </div>\n'
            '</div>\n'
            '{{% endblock %}}\n'
        ).format(css_class=css_class, app=app)

    elif preset == 'portal_dashboard':
        body = (
            '{{% block page_content %}}\n'
            '{{% if frappe.session.user == "Guest" %}}\n'
            '  <!-- ── Not logged in ── -->\n'
            '  <div class="container py-5 text-center">\n'
            '    <h2>Please log in to view your dashboard</h2>\n'
            '    <a href="/login?redirect-to={{{{ request.path }}}}" class="btn btn-lg mt-3" style="background:var(--brand);color:#fff">Log In</a>\n'
            '  </div>\n'
            '{{% else %}}\n'
            '<div class="{css_class}-wrapper container-fluid py-4">\n\n'
            '  <!-- ── Page Header ── -->\n'
            '  <div class="d-flex align-items-center justify-content-between mb-4 flex-wrap gap-2">\n'
            '    <div>\n'
            '      <h2 class="fw-bold mb-0" style="color:var(--text-dark)">{{{{ title }}}}</h2>\n'
            '      <p class="text-muted mb-0 small">Welcome, {{{{ frappe.session.user }}}}</p>\n'
            '    </div>\n'
            '    <div class="d-flex gap-2">\n'
            '      <!-- <a href="/new-order" class="btn btn-sm" style="background:var(--brand);color:#fff">+ New Order</a> -->\n'
            '    </div>\n'
            '  </div>\n\n'
            '  <!-- ══ KPI CARDS ════════════════════════════════════════════════ -->\n'
            '  <div class="row g-3 mb-4">\n'
            '    {{% for card in kpi_cards %}}\n'
            '    <div class="col-6 col-md-3">\n'
            '      <div class="card border-0 h-100 p-3" style="border-radius:var(--radius);box-shadow:var(--shadow);border-left:4px solid {{{{ card.color }}}} !important">\n'
            '        <div class="text-muted small">{{{{ card.label }}}}</div>\n'
            '        <div class="fs-3 fw-black mt-1" style="color:{{{{ card.color }}}}">{{{{ card.value }}}}</div>\n'
            '        <!-- <div class="text-success small mt-1">↑ {{{{ card.change }}}} vs last month</div> -->\n'
            '      </div>\n'
            '    </div>\n'
            '    {{% endfor %}}\n'
            '  </div>\n\n'
            '  <!-- ══ RECENT ORDERS TABLE ═══════════════════════════════════════ -->\n'
            '  <div class="card border-0 mb-4" style="border-radius:var(--radius);box-shadow:var(--shadow)">\n'
            '    <div class="card-header bg-white fw-bold py-3" style="border-bottom:1px solid #f0ebff">Recent Orders</div>\n'
            '    <div class="table-responsive">\n'
            '      <table class="table table-hover mb-0">\n'
            '        <thead class="table-light"><tr><th>Order</th><th>Date</th><th>Amount</th><th>Status</th><th></th></tr></thead>\n'
            '        <tbody>\n'
            '          {{% for order in recent_orders %}}\n'
            '          <tr>\n'
            '            <td><a href="/orders/{{{{ order.name }}}}">{{{{ order.name }}}}</a></td>\n'
            '            <td>{{{{ order.transaction_date }}}}</td>\n'
            '            <td>{{{{ frappe.format_value(order.grand_total, dict(fieldtype="Currency")) }}}}</td>\n'
            '            <td><span class="badge" style="background:{{{{ \'#22c55e\' if order.status==\'Completed\' else \'#f59e0b\' }}}}">{{{{ order.status }}}}</span></td>\n'
            '            <td><a href="/orders/{{{{ order.name }}}}" class="btn btn-sm btn-outline-secondary">View</a></td>\n'
            '          </tr>\n'
            '          {{% endfor %}}\n'
            '          {{% if not recent_orders %}}\n'
            '          <tr><td colspan="5" class="text-center text-muted py-4">No orders yet.</td></tr>\n'
            '          {{% endif %}}\n'
            '        </tbody>\n'
            '      </table>\n'
            '    </div>\n'
            '  </div>\n\n'
            '</div>\n'
            '{{% endif %}}\n'
            '{{% endblock %}}\n'
        ).format(css_class=css_class, app=app)

    elif preset == 'list_directory':
        body = (
            '{{% block page_content %}}\n'
            '<div class="{css_class}-wrapper container py-5">\n\n'
            '  <!-- ── Header + Search ── -->\n'
            '  <div class="d-flex align-items-center justify-content-between mb-4 flex-wrap gap-3">\n'
            '    <h1 class="fw-bold mb-0" style="color:var(--text-dark)">{{{{ title }}}}</h1>\n'
            '    <input type="search" id="dir-search" class="form-control" placeholder="Search…" style="max-width:280px">\n'
            '  </div>\n\n'
            '  <!-- ── Filter pills — uncomment and adapt ── -->\n'
            '  <!-- <div class="d-flex gap-2 flex-wrap mb-4">\n'
            '    <button class="btn btn-sm filter-btn active" data-filter="all">All</button>\n'
            '    {{% for cat in categories %}}\n'
            '    <button class="btn btn-sm btn-outline-secondary filter-btn" data-filter="{{{{ cat }}}}">{{{{ cat }}}}</button>\n'
            '    {{% endfor %}}\n'
            '  </div> -->\n\n'
            '  <!-- ── Card Grid ── -->\n'
            '  <div class="row g-4" id="dir-grid">\n'
            '    {{% for item in items %}}\n'
            '    <div class="col-md-6 col-lg-4 dir-card" data-name="{{{{ item.name|lower }}}}">\n'
            '      <div class="card border-0 h-100" style="border-radius:var(--radius);box-shadow:var(--shadow);transition:transform .15s">\n'
            '        <!-- Optional image -->\n'
            '        {{% if item.image %}}\n'
            '        <img src="{{{{ item.image }}}}" class="card-img-top" style="height:180px;object-fit:cover;border-radius:var(--radius) var(--radius) 0 0">\n'
            '        {{% endif %}}\n'
            '        <div class="card-body">\n'
            '          <span class="badge mb-2" style="background:var(--brand-light);color:var(--brand)">{{{{ item.category or "" }}}}</span>\n'
            '          <h5 class="fw-bold" style="color:var(--text-dark)">{{{{ item.title or item.name }}}}</h5>\n'
            '          <p class="text-muted small">{{{{ item.description or "" }}}}</p>\n'
            '          <a href="{{{{ item.route or "#" }}}}" class="btn btn-sm fw-semibold mt-auto" style="background:var(--brand);color:#fff;border-radius:6px">View →</a>\n'
            '        </div>\n'
            '      </div>\n'
            '    </div>\n'
            '    {{% endfor %}}\n'
            '    {{% if not items %}}\n'
            '    <div class="col-12 text-center text-muted py-5">No items found.</div>\n'
            '    {{% endif %}}\n'
            '  </div>\n\n'
            '  <!-- ── Pagination — uncomment when needed ── -->\n'
            '  <!-- <nav class="mt-5"><ul class="pagination justify-content-center">\n'
            '    <li class="page-item {{% if page == 1 %}}disabled{{% endif %}}"><a class="page-link" href="?page={{{{ page-1 }}}}">‹ Prev</a></li>\n'
            '    <li class="page-item {{% if not has_more %}}disabled{{% endif %}}"><a class="page-link" href="?page={{{{ page+1 }}}}">Next ›</a></li>\n'
            '  </ul></nav> -->\n\n'
            '</div>\n'
            '{{% endblock %}}\n'
        ).format(css_class=css_class, app=app)

    elif preset == 'pricing':
        body = (
            '{{% block page_content %}}\n'
            '<div class="{css_class}-wrapper py-5">\n'
            '  <div class="container">\n\n'
            '    <div class="text-center mb-5">\n'
            '      <h1 class="fw-bold" style="color:var(--text-dark)">{{{{ title }}}}</h1>\n'
            '      <p class="text-muted lead">Choose the plan that works best for you.</p>\n'
            '      <!-- Toggle annual/monthly — uncomment if needed -->\n'
            '      <!-- <div class="form-check form-switch d-inline-flex align-items-center gap-2 mt-3">\n'
            '        <input class="form-check-input" type="checkbox" id="billing-toggle">\n'
            '        <label class="form-check-label" for="billing-toggle">Annual billing (save 20%)</label>\n'
            '      </div> -->\n'
            '    </div>\n\n'
            '    <div class="row g-4 justify-content-center">\n'
            '      {{% for plan in plans %}}\n'
            '      <div class="col-md-4">\n'
            '        <div class="card border-0 h-100 text-center p-4 {{% if plan.featured %}}featured-plan{{% endif %}}" style="border-radius:var(--radius);box-shadow:var(--shadow);{{% if plan.featured %}}background:var(--brand);color:#fff;transform:scale(1.04){{% endif %}}">\n'
            '          {{% if plan.featured %}}<div class="badge bg-warning text-dark mb-2 py-1 px-3">Most Popular</div>{{% endif %}}\n'
            '          <h4 class="fw-bold">{{{{ plan.name }}}}</h4>\n'
            '          <div class="my-3"><span class="display-5 fw-black">{{{{ plan.price }}}}</span><span class="opacity-75">/mo</span></div>\n'
            '          <p class="small opacity-75 mb-4">{{{{ plan.description }}}}</p>\n'
            '          <ul class="list-unstyled text-start mb-4">\n'
            '            {{% for feature in plan.features %}}\n'
            '            <li class="mb-2"><span class="me-2">✓</span>{{{{ feature }}}}</li>\n'
            '            {{% endfor %}}\n'
            '          </ul>\n'
            '          <a href="{{{{ plan.cta_link or "/contact" }}}}" class="btn btn-lg w-100 fw-semibold mt-auto" style="{{% if plan.featured %}}background:#fff;color:var(--brand){{% else %}}background:var(--brand);color:#fff{{% endif %}};border-radius:var(--radius)">{{{{ plan.cta or "Get Started" }}}}</a>\n'
            '        </div>\n'
            '      </div>\n'
            '      {{% endfor %}}\n'
            '    </div>\n\n'
            '    <!-- FAQ teaser -->\n'
            '    <!-- <div class="text-center mt-5"><p class="text-muted">Have questions? <a href="/faq">Read our FAQ</a></p></div> -->\n\n'
            '  </div>\n'
            '</div>\n'
            '{{% endblock %}}\n'
        ).format(css_class=css_class, app=app)

    elif preset == 'faq':
        body = (
            '{{% block page_content %}}\n'
            '<div class="{css_class}-wrapper container py-5">\n'
            '  <div class="row justify-content-center">\n'
            '    <div class="col-lg-8">\n\n'
            '      <div class="text-center mb-5">\n'
            '        <h1 class="fw-bold" style="color:var(--text-dark)">{{{{ title }}}}</h1>\n'
            '        <p class="text-muted">Find answers to the most common questions.</p>\n'
            '        <!-- Search faqs -->\n'
            '        <input type="search" id="faq-search" class="form-control mx-auto mt-3" placeholder="Search FAQs…" style="max-width:400px">\n'
            '      </div>\n\n'
            '      <!-- ── Category tabs — uncomment when you have multiple categories ── -->\n'
            '      <!-- <ul class="nav nav-pills justify-content-center mb-4">\n'
            '        {{% for cat in faq_categories %}}\n'
            '        <li class="nav-item"><button class="nav-link" data-cat="{{{{ cat }}}}">{{{{ cat }}}}</button></li>\n'
            '        {{% endfor %}}\n'
            '      </ul> -->\n\n'
            '      <!-- ── Accordion ── -->\n'
            '      <div class="accordion accordion-flush" id="faqAccordion">\n'
            '        {{% for faq in faqs %}}\n'
            '        <div class="accordion-item border-0 mb-2 faq-item" style="border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden" data-question="{{{{ faq.question|lower }}}}">\n'
            '          <h2 class="accordion-header">\n'
            '            <button class="accordion-button collapsed fw-semibold" type="button" data-bs-toggle="collapse" data-bs-target="#faq-{{{{ loop.index }}}}">\n'
            '              {{{{ faq.question }}}}\n'
            '            </button>\n'
            '          </h2>\n'
            '          <div id="faq-{{{{ loop.index }}}}" class="accordion-collapse collapse" data-bs-parent="#faqAccordion">\n'
            '            <div class="accordion-body text-muted">{{{{ faq.answer }}}}</div>\n'
            '          </div>\n'
            '        </div>\n'
            '        {{% endfor %}}\n'
            '        {{% if not faqs %}}\n'
            '        <p class="text-center text-muted py-4">No FAQs published yet.</p>\n'
            '        {{% endif %}}\n'
            '      </div>\n\n'
            '      <!-- CTA at bottom -->\n'
            '      <div class="text-center mt-5 p-4" style="background:var(--brand-light);border-radius:var(--radius)">\n'
            '        <p class="fw-semibold mb-2" style="color:var(--text-dark)">Still have questions?</p>\n'
            '        <a href="/contact" class="btn" style="background:var(--brand);color:#fff">Contact Support</a>\n'
            '      </div>\n\n'
            '    </div>\n'
            '  </div>\n'
            '</div>\n'
            '{{% endblock %}}\n'
        ).format(css_class=css_class, app=app)

    elif preset == 'blog_post':
        body = (
            '{{% block page_content %}}\n'
            '<div class="{css_class}-wrapper container py-5">\n'
            '  <div class="row g-5">\n\n'
            '    <!-- ── Main Article ── -->\n'
            '    <div class="col-lg-8">\n'
            '      <!-- Cover image -->\n'
            '      {{% if cover_image %}}\n'
            '      <img src="{{{{ cover_image }}}}" alt="{{{{ title }}}}" class="img-fluid rounded-3 mb-4 w-100" style="max-height:400px;object-fit:cover">\n'
            '      {{% endif %}}\n'
            '      <!-- Meta -->\n'
            '      <div class="d-flex align-items-center gap-3 mb-3 flex-wrap">\n'
            '        <span class="badge" style="background:var(--brand-light);color:var(--brand)">{{{{ category or "Blog" }}}}</span>\n'
            '        <small class="text-muted">{{{{ published_on }}}}</small>\n'
            '        <small class="text-muted">·</small>\n'
            '        <small class="text-muted">{{{{ read_time or "5" }}}} min read</small>\n'
            '      </div>\n'
            '      <h1 class="fw-bold mb-4" style="color:var(--text-dark)">{{{{ title }}}}</h1>\n'
            '      <!-- Author card -->\n'
            '      <div class="d-flex align-items-center gap-3 mb-4">\n'
            '        <!-- <img src="{{{{ author_image }}}}" alt="{{{{ author }}}}" class="rounded-circle" style="width:44px;height:44px;object-fit:cover"> -->\n'
            '        <div><p class="mb-0 fw-semibold">{{{{ author or "Author Name" }}}}</p><small class="text-muted">{{{{ author_bio or "" }}}}</small></div>\n'
            '      </div>\n'
            '      <hr>\n'
            '      <!-- Content -->\n'
            '      <div class="post-content lh-lg" style="font-size:1.05rem">\n'
            '        {{{{ content }}}}\n'
            '      </div>\n'
            '      <!-- Tags -->\n'
            '      <div class="mt-4 d-flex gap-2 flex-wrap">\n'
            '        {{% for tag in tags %}}\n'
            '        <a href="/blog?tag={{{{ tag }}}}" class="badge text-decoration-none" style="background:var(--brand-light);color:var(--brand)">{{{{ tag }}}}</a>\n'
            '        {{% endfor %}}\n'
            '      </div>\n'
            '      <!-- Share buttons -->\n'
            '      <!-- <div class="mt-4 d-flex gap-3">\n'
            '        <a href="https://twitter.com/intent/tweet?text={{{{ title|urlencode }}}}&url={{{{ request.url|urlencode }}}}" target="_blank" class="btn btn-sm btn-outline-secondary">Twitter</a>\n'
            '        <a href="https://www.linkedin.com/sharing/share-offsite/?url={{{{ request.url|urlencode }}}}" target="_blank" class="btn btn-sm btn-outline-secondary">LinkedIn</a>\n'
            '      </div> -->\n'
            '    </div>\n\n'
            '    <!-- ── Sidebar ── -->\n'
            '    <div class="col-lg-4">\n'
            '      <!-- Recent posts widget -->\n'
            '      <div class="card border-0 p-4 mb-4" style="border-radius:var(--radius);box-shadow:var(--shadow)">\n'
            '        <h5 class="fw-bold mb-3" style="color:var(--text-dark)">Recent Posts</h5>\n'
            '        {{% for post in recent_posts %}}\n'
            '        <div class="mb-3">\n'
            '          <a href="{{{{ post.route }}}}" class="fw-semibold text-decoration-none" style="color:var(--brand)">{{{{ post.title }}}}</a>\n'
            '          <p class="small text-muted mb-0">{{{{ post.published_on }}}}</p>\n'
            '        </div>\n'
            '        {{% endfor %}}\n'
            '      </div>\n'
            '      <!-- Categories widget -->\n'
            '      <!-- <div class="card border-0 p-4" style="border-radius:var(--radius);box-shadow:var(--shadow)">\n'
            '        <h5 class="fw-bold mb-3">Categories</h5>\n'
            '        {{% for cat in all_categories %}}\n'
            '        <a href="/blog?category={{{{ cat }}}}" class="d-block text-muted small py-1">{{{{ cat }}}}</a>\n'
            '        {{% endfor %}}\n'
            '      </div> -->\n'
            '    </div>\n\n'
            '  </div>\n'
            '</div>\n'
            '{{% endblock %}}\n'
        ).format(css_class=css_class, app=app)

    # ── Advanced full-site layout presets (return complete HTML5 documents) ──
    elif preset == 'topnav_multipage':
        return _www_tpl_topnav(css_class, app)
    elif preset == 'leftnav_sidebar':
        return _www_tpl_leftnav(css_class, app)
    elif preset == 'spa_scrollnav':
        return _www_tpl_spa(css_class, app)
    elif preset == 'saas_landing':
        return _www_tpl_saas(css_class, app)
    elif preset == 'agency_portfolio':
        return _www_tpl_agency(css_class, app)
    elif preset == 'docs_leftnav':
        return _www_tpl_docs(css_class, app)

    else:  # blank
        body = (
            '{{% block page_content %}}\n'
            '<div class="{css_class}-wrapper container my-5">\n\n'
            '  <!-- ── Page Header ──────────────────────────────────────────── -->\n'
            '  <div class="mb-5">\n'
            '    <h1 class="fw-bold" style="color:var(--text-dark)">{{{{ title }}}}</h1>\n'
            '    <p class="text-muted lead">Page description goes here.</p>\n'
            '    <hr style="border-color:var(--brand-light)">\n'
            '  </div>\n\n'
            '  <!-- ── Main Content ─────────────────────────────────────────── -->\n'
            '  <div class="row">\n'
            '    <div class="col-lg-8">\n'
            '      <!-- Your HTML here -->\n'
            '      <!-- Loop over Frappe data:\n'
            '      {{% for row in records %}}\n'
            '      <p>{{{{ row.name }}}}</p>\n'
            '      {{% endfor %}}  -->\n'
            '    </div>\n'
            '    <div class="col-lg-4">\n'
            '      <!-- Sidebar -->\n'
            '    </div>\n'
            '  </div>\n\n'
            '</div>\n'
            '{{% endblock %}}\n'
        ).format(css_class=css_class, app=app)

    return head + body + foot


def _www_py_template(preset, title, app):
    """Return boilerplate Python get_context for a www page based on preset."""

    base = f'''import frappe
from frappe import _

# ── Page settings ─────────────────────────────────────────────────────────────
no_cache       = 1      # disable HTTP response cache
# login_required = True   # uncomment to redirect guests to /login
# allow_guest   = True    # uncomment to allow unauthenticated access


def get_context(context):
    """
    Populate the Jinja2 template context.
    Everything added to `context` becomes available as a variable in the .html.

    Common patterns — uncomment as needed:
    ──────────────────────────────────────────────────────────────────────────

    # ── Auth check ──────────────────────────────────────────────────────────
    # if frappe.session.user == "Guest":
    #     frappe.throw(_("You must be logged in."), frappe.PermissionError)

    # ── Title & meta ────────────────────────────────────────────────────────
    # context.metatags = {{
    #     "title":       "{title}",
    #     "description": "Page description for SEO",
    #     "image":       "/assets/{app}/images/og-cover.png",
    #     "keywords":    "keyword1, keyword2",
    # }}

    # ── Pass current user info ───────────────────────────────────────────────
    # context.user       = frappe.session.user
    # context.user_roles = frappe.get_roles()
    # context.full_name  = frappe.db.get_value("User", frappe.session.user, "full_name")

    # ── Fetch a list of records ──────────────────────────────────────────────
    # context.records = frappe.get_all(
    #     "Sales Order",
    #     filters={{"docstatus": 1}},
    #     fields=["name", "customer", "grand_total", "transaction_date"],
    #     order_by="transaction_date desc",
    #     limit=20
    # )

    # ── Fetch a single document ──────────────────────────────────────────────
    # name = frappe.form_dict.get("name")
    # if not name:
    #     frappe.throw(_("Document name is required"), frappe.DoesNotExistError)
    # context.doc = frappe.get_doc("Sales Invoice", name)

    # ── Pagination ───────────────────────────────────────────────────────────
    # PAGE_SIZE = 20
    # context.page = int(frappe.form_dict.get("page") or 1)
    # offset = (context.page - 1) * PAGE_SIZE
    # context.items = frappe.get_all("Item", limit=PAGE_SIZE+1, start=offset, fields=["name","item_name","image"])
    # context.has_more = len(context.items) > PAGE_SIZE
    # context.items = context.items[:PAGE_SIZE]

    # ── URL query params ─────────────────────────────────────────────────────
    # search = frappe.form_dict.get("q", "")
    # context.search = search
    # if search:
    #     context.items = frappe.get_all("Item", filters=[["item_name","like",f"%{{search}}%"]], fields=["name","item_name"])

    # ── Call a whitelisted API internally ────────────────────────────────────
    # context.totals = frappe.call("{app}.api.my_module.get_dashboard_totals")

    # ── Pass system defaults ─────────────────────────────────────────────────
    # context.company  = frappe.defaults.get_global_default("company")
    # context.currency = frappe.defaults.get_global_default("currency")

    # ── Custom 404 / redirect ────────────────────────────────────────────────
    # raise frappe.DoesNotExistError          # shows 404 page
    # frappe.local.flags.redirect_location = "/other-page"
    # raise frappe.Redirect

    """
    context.title = "{title}"
'''

    if preset == 'landing':
        base += '''
    # Features list shown in the hero section
    context.features = [
        {"icon": "⚡", "title": "Fast",     "desc": "Built for speed and reliability."},
        {"icon": "🔒", "title": "Secure",   "desc": "Enterprise-grade security baked in."},
        {"icon": "📈", "title": "Scalable", "desc": "Grows with your business seamlessly."},
    ]
    return context
'''
    elif preset == 'portal_dashboard':
        base += '''
    if frappe.session.user == "Guest":
        return context   # template handles redirect

    # KPI cards
    context.kpi_cards = [
        {"label": "Open Orders",   "value": frappe.db.count("Sales Order",    {"docstatus": 1, "status": "To Deliver and Bill"}), "color": "#5c4da8"},
        {"label": "Unpaid Bills",  "value": frappe.db.count("Sales Invoice",  {"docstatus": 1, "outstanding_amount": [">", 0]}),   "color": "#dc2626"},
        {"label": "Active Tasks",  "value": frappe.db.count("Task",           {"status": "Open"}),                                 "color": "#0369a1"},
        {"label": "Open Issues",   "value": frappe.db.count("Issue",          {"status": "Open"}),                                 "color": "#b45309"},
    ]

    # Recent orders for the logged-in customer
    # Replace with your own query / customer link logic
    # context.recent_orders = frappe.get_all(
    #     "Sales Order",
    #     filters={"docstatus": 1},
    #     fields=["name", "transaction_date", "grand_total", "status"],
    #     order_by="transaction_date desc",
    #     limit=10
    # )
    context.recent_orders = []
    return context
'''
    elif preset == 'list_directory':
        base += '''
    context.items = frappe.get_all(
        "Item",
        filters={"disabled": 0, "show_in_website": 1},
        fields=["name", "item_name", "item_group", "description", "website_image", "route"],
        order_by="item_name asc",
        limit=60,
    )
    # context.categories = list({i["item_group"] for i in context.items})
    return context
'''
    elif preset == 'pricing':
        base += '''
    context.plans = [
        {
            "name": "Starter", "price": "$0", "featured": False,
            "description": "Perfect for individuals and small teams.",
            "features": ["5 users", "10 GB storage", "Basic support"],
            "cta": "Start Free", "cta_link": "/register",
        },
        {
            "name": "Pro", "price": "$29", "featured": True,
            "description": "Everything you need to grow your business.",
            "features": ["Unlimited users", "100 GB storage", "Priority support", "Custom domain"],
            "cta": "Start Trial", "cta_link": "/register?plan=pro",
        },
        {
            "name": "Enterprise", "price": "Custom", "featured": False,
            "description": "Dedicated infrastructure and SLA.",
            "features": ["Unlimited everything", "Dedicated server", "24/7 phone support", "Custom SLA"],
            "cta": "Contact Sales", "cta_link": "/contact",
        },
    ]
    return context
'''
    elif preset == 'faq':
        base += '''
    context.faqs = frappe.get_all(
        "FAQ",   # Replace with your actual DocType name
        filters={"published": 1},
        fields=["question", "answer", "category"],
        order_by="idx asc",
    ) if frappe.db.table_exists("tabFAQ") else [
        {"question": "What is this?",         "answer": "This is a sample answer."},
        {"question": "How do I get started?", "answer": "Register and log in to your account."},
    ]
    return context
'''
    elif preset == 'blog_post':
        base += '''
    # For a blog post you usually pass the route to look up the post:
    # route = frappe.form_dict.get("route") or frappe.local.path
    # context.doc = frappe.get_doc("Blog Post", {"route": route})

    # Recent sidebar posts
    context.recent_posts = frappe.get_all(
        "Blog Post",
        filters={"published": 1},
        fields=["title", "route", "published_on"],
        order_by="published_on desc",
        limit=5,
    ) if frappe.db.table_exists("tabBlog Post") else []
    return context
'''
    elif preset == 'topnav_multipage':
        base += '''
    # ── Nav links (rendered in navbar) ──────────────────────────────────────
    context.nav_links = [
        {"label": "Home",     "href": "/",         "active": True},
        {"label": "About",    "href": "/about"},
        {"label": "Services", "href": "/services", "dropdown": [
            {"label": "Web Design",   "href": "/services/web-design"},
            {"label": "Development",  "href": "/services/development"},
            {"label": "Consulting",   "href": "/services/consulting"},
        ]},
        {"label": "Blog",    "href": "/blog"},
        {"label": "Contact", "href": "/contact"},
    ]
    # ── Hero copy (override in get_context per page) ─────────────────────────
    context.hero_title    = "Build Something"
    context.hero_subtitle = "Extraordinary"
    context.hero_desc     = "Your compelling one-sentence value proposition. Make it clear, bold, and unmissable."
    context.hero_cta      = "Get Started Free"
    context.hero_cta_href = "/contact"
    # ── Feature cards ────────────────────────────────────────────────────────
    context.features = [
        {"icon": "⚡", "title": "Lightning Fast",    "desc": "Sub-second load times, optimised for every device."},
        {"icon": "🎨", "title": "Beautiful Design",   "desc": "Pixel-perfect, responsive across all screen sizes."},
        {"icon": "🔒", "title": "Secure by Default",  "desc": "Enterprise-grade security with zero configuration."},
        {"icon": "📊", "title": "Deep Analytics",     "desc": "Real-time insights into usage and performance."},
        {"icon": "⚙️",  "title": "Easy to Customise", "desc": "Config-driven — no code changes required."},
        {"icon": "🚀", "title": "Deploy Anywhere",    "desc": "Cloud, on-premise, or hybrid — your infrastructure."},
    ]
    # ── Stats row ────────────────────────────────────────────────────────────
    context.stats = [
        {"value": "500+", "label": "Clients"},
        {"value": "10+",  "label": "Years"},
        {"value": "99%",  "label": "Satisfaction"},
    ]
    # ── Testimonials ─────────────────────────────────────────────────────────
    context.testimonials = [
        {"avatar": "AC", "name": "Alice Chen",   "role": "CTO, Acme Corp",     "text": "Best decision we ever made. ROI in under 30 days."},
        {"avatar": "BS", "name": "Bob Smith",    "role": "Founder, StartupXYZ","text": "Incredible support and the product just works. Saved us months."},
        {"avatar": "CD", "name": "Carol Davis",  "role": "VP Ops, BigCo",      "text": "Saved 20 hours a week. Couldn't imagine going back to the old system."},
    ]
    return context
'''
    elif preset == 'leftnav_sidebar':
        base += '''
    # ── Sidebar navigation groups ─────────────────────────────────────────────
    context.sidebar_groups = [
        {"label": "Main", "links": [
            {"icon": "🏠", "label": "Dashboard",  "href": "#",  "active": True},
            {"icon": "📊", "label": "Analytics",  "href": "#analytics"},
            {"icon": "📋", "label": "Reports",    "href": "#reports"},
        ]},
        {"label": "Management", "links": [
            {"icon": "👥", "label": "Users",      "href": "#users"},
            {"icon": "⚙️",  "label": "Settings",  "href": "#settings"},
            {"icon": "🔔", "label": "Notifications","href": "#notifications"},
        ]},
        {"label": "Data", "links": [
            {"icon": "📁", "label": "Documents",  "href": "#documents"},
            {"icon": "🗄️",  "label": "Exports",   "href": "#exports"},
        ]},
    ]
    # ── KPI cards ────────────────────────────────────────────────────────────
    context.kpi_cards = [
        {"icon": "💰", "label": "Total Revenue", "value": "₹ 4,28,500", "change": "+12%",  "up": True,  "color": "#5c4da8"},
        {"icon": "🛒", "label": "Orders Today",  "value": "147",        "change": "+8%",   "up": True,  "color": "#0369a1"},
        {"icon": "👥", "label": "Active Users",  "value": "2,391",      "change": "-3%",   "up": False, "color": "#be185d"},
        {"icon": "📈", "label": "Conversion",    "value": "3.6%",       "change": "+0.4%", "up": True,  "color": "#059669"},
    ]
    # ── User info for sidebar footer ─────────────────────────────────────────
    context.user_full_name = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user
    context.user_role = (frappe.get_roles(frappe.session.user) or ["User"])[0]
    return context
'''
    elif preset == 'spa_scrollnav':
        base += '''
    # All sections are on one page — populate each section's data here
    context.features = [
        {"icon": "⚡", "title": "Speed",         "desc": "Built for sub-second response times at any scale."},
        {"icon": "🎨", "title": "Design",         "desc": "Beautiful, accessible UI components out of the box."},
        {"icon": "🔒", "title": "Security",       "desc": "Zero-trust architecture with audit logging."},
        {"icon": "📊", "title": "Analytics",      "desc": "Real-time dashboards and exportable reports."},
        {"icon": "🔌", "title": "Integrations",   "desc": "Connect any tool via REST, webhooks, or SDKs."},
        {"icon": "☁️",  "title": "Cloud Native",   "desc": "Auto-scaling infrastructure, zero ops overhead."},
    ]
    context.steps = [
        {"num": "01", "title": "Sign Up Free",    "desc": "Create your account in under 60 seconds. No credit card required."},
        {"num": "02", "title": "Import Your Data","desc": "Upload a CSV or connect your existing system in one click."},
        {"num": "03", "title": "Go Live",         "desc": "Invite your team and start working — it really is that simple."},
    ]
    context.testimonials = [
        {"name": "Priya Sharma",  "role": "Founder, TechFlow",    "text": "We went from 0 to 100 customers in a month after switching. Incredible."},
        {"name": "James Okafor",  "role": "Engineering Lead",      "text": "The API is a dream. Integration took 2 hours, not 2 weeks."},
        {"name": "Maria Gonzalez","role": "COO, RetailPlus",       "text": "Our team adopted it with zero training. The UX is that intuitive."},
    ]
    context.plans = [
        {"name": "Starter", "price": "₹0",  "period": "forever", "featured": False, "features": ["Up to 5 users","1 GB storage","Community support","Basic reports"],"cta": "Get Started","href": "/register"},
        {"name": "Growth",  "price": "₹999","period": "/ month",  "featured": True,  "features": ["Unlimited users","50 GB storage","Priority support","Advanced analytics","Custom domain"],"cta": "Start 14-Day Trial","href": "/register?plan=growth"},
        {"name": "Scale",   "price": "Custom","period":"",        "featured": False, "features": ["Everything in Growth","Dedicated infra","SLA guarantee","Onboarding team","Custom contracts"],"cta": "Contact Sales","href": "/contact"},
    ]
    context.faqs = [
        {"q": "Is there a free trial?",         "a": "Yes — the Starter plan is free forever with no credit card required."},
        {"q": "Can I cancel anytime?",          "a": "Absolutely. Cancel from your account settings with one click."},
        {"q": "Do you support on-premise?",     "a": "Yes. Enterprise customers can deploy on their own infrastructure."},
        {"q": "What integrations are available?","a": "We connect with 50+ tools including Slack, Zapier, Salesforce, and more."},
    ]
    return context
'''
    elif preset == 'saas_landing':
        base += '''
    context.announcement = "🎉 We just raised our Series A — read the blog post →"
    context.announcement_href = "/blog/series-a"
    context.hero_headline  = "The smarter way to run your business"
    context.hero_subtext   = "Automate workflows, unify your data, and grow faster — without the complexity."
    context.feature_blocks = [
        {"side": "right", "icon": "⚡", "tag": "Automation", "title": "Put repetitive tasks on autopilot",
         "desc": "Build powerful workflows with a drag-and-drop editor — no code required. Save your team 10+ hours every week.",
         "bullets": ["Visual workflow builder","500+ app integrations","Real-time monitoring & alerts"]},
        {"side": "left",  "icon": "📊", "tag": "Analytics",  "title": "Understand your business in real time",
         "desc": "A single dashboard for every metric that matters. Slice, drill down, and export in one click.",
         "bullets": ["Live KPI dashboards","Custom report builder","CSV / Excel export"]},
        {"side": "right", "icon": "🤝", "tag": "Collaboration","title": "Keep your whole team in sync",
         "desc": "Shared workspaces, granular permissions, and in-app notifications keep everyone aligned.",
         "bullets": ["Role-based access control","Real-time comments","@mentions & task assignment"]},
    ]
    context.logos = ["Acme Corp", "GlobalTech", "StartupXYZ", "MegaBrand", "NextGen"]
    context.plans = [
        {"name":"Starter","price":"₹0",   "period":"forever","featured":False,"features":["5 users","10 GB","Email support"],"cta":"Get Started","href":"/register"},
        {"name":"Pro",    "price":"₹1,499","period":"/month", "featured":True, "features":["Unlimited users","100 GB","Priority support","Custom domain","API access"],"cta":"Start Free Trial","href":"/register?plan=pro"},
        {"name":"Enterprise","price":"Custom","period":"","featured":False,"features":["Everything in Pro","Dedicated server","SLA","Custom contract"],"cta":"Talk to Sales","href":"/contact"},
    ]
    context.testimonials = [
        {"name":"Ravi Menon",   "role":"CTO, FinServ",  "rating":5,"text":"Cut our manual ops by 70%. The automation builder is genuinely magical."},
        {"name":"Sarah Lee",    "role":"Head of Ops",   "rating":5,"text":"Onboarded the whole team in a day. Support is outstanding."},
        {"name":"Tom Barrett",  "role":"Founder",       "rating":5,"text":"Best ROI of any software we've bought. Period."},
        {"name":"Anita Patel",  "role":"VP Engineering","rating":5,"text":"API is clean, docs are great, and it actually works as advertised."},
    ]
    context.faqs = [
        {"q":"How long does setup take?",      "a":"Most teams are up and running in under an hour. Our onboarding guide walks you through every step."},
        {"q":"Do you offer a free trial?",     "a":"The Starter plan is free forever. Pro plans include a 14-day free trial, no credit card needed."},
        {"q":"Can I migrate from another tool?","a":"Yes — we have migration scripts for the most popular platforms and a dedicated migration team."},
        {"q":"Is my data secure?",             "a":"We're SOC 2 Type II certified, use AES-256 encryption, and offer data residency options."},
        {"q":"What support is included?",      "a":"All plans include email support. Pro and above get priority chat support and a dedicated Slack channel."},
    ]
    return context
'''
    elif preset == 'agency_portfolio':
        base += '''
    context.hero_tagline = "We craft digital experiences that move people"
    context.projects = [
        {"title":"BrandRevamp",   "category":"Branding",    "desc":"Complete visual identity redesign for a Fortune 500 firm.","color":"#5c4da8"},
        {"title":"ShopFast",      "category":"E-Commerce",  "desc":"High-conversion storefront serving 200k daily visitors.",   "color":"#0369a1"},
        {"title":"HealthTrack",   "category":"Web App",     "desc":"Patient portal with real-time data and HIPAA compliance.",  "color":"#059669"},
        {"title":"CityGuide",     "category":"Mobile",      "desc":"Location-aware city guide app with 500k downloads.",       "color":"#be185d"},
        {"title":"FinDash",       "category":"Dashboard",   "desc":"Financial analytics dashboard used by 50 hedge funds.",    "color":"#b45309"},
        {"title":"EduPlatform",   "category":"Web App",     "desc":"Online learning platform for 1M+ students globally.",      "color":"#0891b2"},
    ]
    context.services = [
        {"icon":"🎨","title":"Brand Identity",  "desc":"Logo, colour, typography — a complete visual language for your brand."},
        {"icon":"💻","title":"Web Development", "desc":"Custom-built sites and apps that perform beautifully on every device."},
        {"icon":"📱","title":"Mobile Apps",     "desc":"Native and cross-platform apps that users love."},
        {"icon":"📊","title":"Digital Strategy","desc":"Data-driven strategy to grow traffic, leads, and revenue."},
    ]
    context.team = [
        {"name":"Alex Rivera",  "role":"Creative Director","avatar":"AR"},
        {"name":"Priya Nair",   "role":"Lead Developer",   "avatar":"PN"},
        {"name":"Sam Okonkwo",  "role":"UX Strategist",    "avatar":"SO"},
        {"name":"Lily Zhang",   "role":"Brand Designer",   "avatar":"LZ"},
    ]
    context.stats = [
        {"value":"120+","label":"Projects Delivered"},
        {"value":"8",   "label":"Years in Business"},
        {"value":"40+", "label":"Happy Clients"},
        {"value":"12",  "label":"Industry Awards"},
    ]
    return context
'''
    elif preset == 'docs_leftnav':
        base += '''
    # ── Documentation sidebar navigation ────────────────────────────────────
    context.doc_sections = [
        {"heading": "Getting Started", "links": [
            {"label": "Introduction",    "href": "/docs/intro",    "active": True},
            {"label": "Installation",    "href": "/docs/install"},
            {"label": "Quick Start",     "href": "/docs/quickstart"},
            {"label": "Configuration",   "href": "/docs/config"},
        ]},
        {"heading": "Core Concepts", "links": [
            {"label": "Architecture",    "href": "/docs/architecture"},
            {"label": "Data Model",      "href": "/docs/data-model"},
            {"label": "Authentication",  "href": "/docs/auth"},
            {"label": "Permissions",     "href": "/docs/permissions"},
        ]},
        {"heading": "API Reference", "links": [
            {"label": "REST API",        "href": "/docs/api/rest"},
            {"label": "Python SDK",      "href": "/docs/api/python"},
            {"label": "Webhooks",        "href": "/docs/api/webhooks"},
        ]},
        {"heading": "Guides", "links": [
            {"label": "Custom Reports",  "href": "/docs/guides/reports"},
            {"label": "Workflow Rules",  "href": "/docs/guides/workflow"},
            {"label": "Print Formats",   "href": "/docs/guides/print"},
        ]},
    ]
    # ── Current article content (fetch from DB or filesystem as needed) ──────
    context.article_title       = "Getting Started with the Platform"
    context.article_breadcrumbs = [{"label":"Docs","href":"/docs"},{"label":"Getting Started","href":"/docs/getting-started"},{"label":"Introduction"}]
    context.article_last_updated = "15 March 2026"
    context.article_read_time    = "5"
    context.prev_article = {"label": None}
    context.next_article = {"label": "Installation", "href": "/docs/install"}
    # ── Table of contents for this article ───────────────────────────────────
    context.toc = [
        {"id": "overview",      "label": "Overview"},
        {"id": "prerequisites", "label": "Prerequisites"},
        {"id": "installation",  "label": "Installation"},
        {"id": "configuration", "label": "Configuration"},
        {"id": "first-steps",   "label": "Your First Steps"},
        {"id": "whats-next",    "label": "What's Next"},
    ]
    return context
'''
    else:  # blank
        base += '''
    # context.records = frappe.get_all("DocType", fields=["name"], limit=10)
    return context
'''
    return base


# ═══════════════════════════════════════════════════════════════════════════════
#  Advanced WWW preset template helpers
#  These return complete standalone HTML5 documents (no {% extends %}).
#  Uses plain Python strings — no .format() — so CSS/JS {} need no escaping.
#  __CC__ → css_class (slug),  __AP__ → app name
# ═══════════════════════════════════════════════════════════════════════════════

def _www_tpl_topnav(cc, app):
    """Multi-page website with responsive sticky top navigation."""
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  <!-- Bootstrap 5.3 CSS -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
  <!-- Bootstrap Icons -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  <style>
    /* ── CSS custom properties — change once, apply everywhere ───────────── */
    :root {
      --brand:       #5c4da8;
      --brand-dark:  #3d2f8f;
      --brand-light: #ede9fe;
      --accent:      #8b5cf6;
      --text-dark:   #1e1b3a;
      --text-muted:  #6b7280;
      --radius:      10px;
      --shadow-sm:   0 2px 8px rgba(92,77,168,.10);
      --shadow:      0 4px 20px rgba(92,77,168,.14);
      --shadow-lg:   0 8px 40px rgba(92,77,168,.20);
      --nav-h:       68px;
    }
    html { scroll-behavior: smooth; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: var(--text-dark); }

    /* ── TOP NAVIGATION ──────────────────────────────────────────────────── */
    /* Starts transparent over hero; .scrolled class added by JS on scroll   */
    .site-nav {
      position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
      height: var(--nav-h); display: flex; align-items: center; padding: 0 2rem;
      background: transparent; transition: background .25s, box-shadow .25s;
    }
    .site-nav.scrolled { background: #fff; box-shadow: var(--shadow-sm); }
    /* Brand */
    .nav-brand {
      font-size: 1.35rem; font-weight: 800; color: #fff; text-decoration: none;
      display: flex; align-items: center; gap: 8px; margin-right: 2rem; letter-spacing: -.03em;
    }
    .nav-brand-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }
    .site-nav.scrolled .nav-brand { color: var(--text-dark); }
    /* Desktop nav links */
    .nav-links { display: flex; align-items: center; gap: .2rem; list-style: none; margin: 0; padding: 0; flex: 1; }
    .nav-links .nav-link {
      color: rgba(255,255,255,.85); font-weight: 500; font-size: .875rem;
      padding: .45rem .75rem; border-radius: 6px; text-decoration: none;
      display: flex; align-items: center; gap: 4px; transition: color .15s, background .15s;
    }
    .nav-links .nav-link:hover, .nav-links .nav-link.active { color: #fff; background: rgba(255,255,255,.12); }
    .site-nav.scrolled .nav-links .nav-link { color: var(--text-muted); }
    .site-nav.scrolled .nav-links .nav-link:hover,
    .site-nav.scrolled .nav-links .nav-link.active { color: var(--brand); background: var(--brand-light); }
    /* Dropdown */
    .nav-dd { position: relative; }
    .nav-dd-menu {
      display: none; position: absolute; top: calc(100% + 8px); left: 0;
      background: #fff; border-radius: var(--radius); box-shadow: var(--shadow);
      min-width: 200px; padding: 8px; list-style: none; border: 1px solid #f0ebff;
    }
    .nav-dd:hover .nav-dd-menu { display: block; }
    .nav-dd-menu a {
      display: block; padding: 8px 12px; color: var(--text-dark);
      font-size: .85rem; font-weight: 500; text-decoration: none; border-radius: 6px;
      transition: background .12s;
    }
    .nav-dd-menu a:hover { background: var(--brand-light); color: var(--brand); }
    /* CTA button */
    .nav-cta {
      margin-left: auto; padding: .45rem 1.2rem; background: #fff; color: var(--brand);
      border: none; border-radius: 8px; font-weight: 700; font-size: .85rem;
      text-decoration: none; transition: background .15s, transform .15s; white-space: nowrap;
    }
    .nav-cta:hover { background: var(--brand-light); transform: translateY(-1px); color: var(--brand); }
    .site-nav.scrolled .nav-cta { background: var(--brand); color: #fff; }
    .site-nav.scrolled .nav-cta:hover { background: var(--brand-dark); color: #fff; }
    /* Mobile hamburger */
    .nav-ham {
      display: none; background: none; border: none; cursor: pointer;
      padding: 8px; flex-direction: column; gap: 5px; margin-left: auto;
    }
    .nav-ham span { display: block; width: 22px; height: 2px; background: #fff; border-radius: 2px; transition: .25s; }
    .site-nav.scrolled .nav-ham span { background: var(--text-dark); }
    /* Mobile overlay nav */
    .mob-nav {
      display: none; position: fixed; inset: 0; z-index: 999;
      background: rgba(0,0,0,.45); backdrop-filter: blur(4px);
    }
    .mob-panel {
      position: absolute; top: 0; right: 0; bottom: 0; width: 280px;
      background: #fff; padding: 80px 24px 32px;
      display: flex; flex-direction: column; gap: 6px; box-shadow: var(--shadow-lg);
    }
    .mob-panel a {
      display: block; padding: 10px 14px; color: var(--text-dark);
      font-weight: 600; font-size: 1rem; text-decoration: none; border-radius: 8px; transition: background .12s;
    }
    .mob-panel a:hover { background: var(--brand-light); color: var(--brand); }
    .mob-close {
      position: absolute; top: 20px; right: 20px; background: none; border: none;
      font-size: 1.5rem; cursor: pointer; color: var(--text-muted);
    }
    @media (max-width: 768px) {
      .nav-links, .nav-cta { display: none; }
      .nav-ham { display: flex; }
    }

    /* ── HERO ──────────────────────────────────────────────────────────────── */
    .hero {
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      background: linear-gradient(135deg, var(--brand) 0%, #6d28d9 55%, var(--accent) 100%);
      text-align: center; padding: calc(var(--nav-h) + 3rem) 1.5rem 5rem; position: relative; overflow: hidden;
    }
    /* Decorative background circles */
    .hero::before {
      content: ''; position: absolute; width: 560px; height: 560px; border-radius: 50%;
      background: rgba(255,255,255,.06); top: -180px; right: -180px;
    }
    .hero::after {
      content: ''; position: absolute; width: 320px; height: 320px; border-radius: 50%;
      background: rgba(255,255,255,.06); bottom: -80px; left: -80px;
    }
    .hero-inner { position: relative; z-index: 1; max-width: 720px; margin: 0 auto; }
    .hero-badge {
      display: inline-block; background: rgba(255,255,255,.15); backdrop-filter: blur(8px);
      border: 1px solid rgba(255,255,255,.3); color: #fff;
      padding: 4px 14px; border-radius: 20px; font-size: .8rem; font-weight: 600; margin-bottom: 1.5rem;
    }
    .hero h1 {
      font-size: clamp(2.4rem, 6vw, 4.2rem); font-weight: 900; color: #fff;
      line-height: 1.1; margin-bottom: 1.25rem; letter-spacing: -.03em;
    }
    .hero-sub { font-size: 1.1rem; color: rgba(255,255,255,.8); margin-bottom: 2.5rem; max-width: 520px; margin-left: auto; margin-right: auto; }
    .hero-btns { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
    .btn-primary-hero {
      padding: .8rem 2.2rem; background: #fff; color: var(--brand); font-weight: 700;
      border-radius: var(--radius); text-decoration: none; transition: transform .15s, box-shadow .15s;
    }
    .btn-primary-hero:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); color: var(--brand); }
    .btn-outline-hero {
      padding: .8rem 2.2rem; background: transparent; color: #fff; font-weight: 700;
      border: 2px solid rgba(255,255,255,.5); border-radius: var(--radius); text-decoration: none; transition: .15s;
    }
    .btn-outline-hero:hover { background: rgba(255,255,255,.1); border-color: #fff; color: #fff; }

    /* ── SECTIONS ────────────────────────────────────────────────────────── */
    section { padding: 5.5rem 0; }
    .eyebrow { font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .12em; color: var(--brand); margin-bottom: .6rem; }
    .section-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 800; color: var(--text-dark); line-height: 1.15; }
    .section-sub { font-size: 1rem; color: var(--text-muted); margin-top: .75rem; }

    /* ── FEATURE CARDS ───────────────────────────────────────────────────── */
    .feat-card {
      background: #fff; border-radius: var(--radius); padding: 28px 24px;
      box-shadow: var(--shadow-sm); border: 1px solid #f0ebff; height: 100%;
      transition: transform .2s, box-shadow .2s, border-color .2s;
    }
    .feat-card:hover { transform: translateY(-4px); box-shadow: var(--shadow); border-color: var(--brand-light); }
    .feat-icon { font-size: 2rem; margin-bottom: 14px; }
    .feat-title { font-size: 1rem; font-weight: 700; color: var(--text-dark); margin-bottom: 8px; }
    .feat-desc { font-size: .875rem; color: var(--text-muted); line-height: 1.65; }

    /* ── ABOUT ───────────────────────────────────────────────────────────── */
    .about-bg { background: #f8f5ff; }
    .stat-box { text-align: center; padding: 18px; }
    .stat-val { font-size: 2.4rem; font-weight: 900; color: var(--brand); line-height: 1; }
    .stat-lbl { font-size: .75rem; text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted); margin-top: 4px; }

    /* ── TESTIMONIALS ────────────────────────────────────────────────────── */
    .testi-card { background: #fff; border-radius: var(--radius); padding: 26px; box-shadow: var(--shadow-sm); border: 1px solid #f0ebff; height: 100%; }
    .testi-stars { color: #f59e0b; font-size: .95rem; margin-bottom: 10px; }
    .testi-text { font-size: .92rem; color: var(--text-muted); line-height: 1.7; font-style: italic; margin-bottom: 18px; }
    .testi-av {
      width: 42px; height: 42px; border-radius: 50%; background: var(--brand-light); color: var(--brand);
      display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: .85rem;
    }
    .testi-name { font-weight: 700; font-size: .88rem; color: var(--text-dark); }
    .testi-role { font-size: .78rem; color: var(--text-muted); }

    /* ── CTA BANNER ──────────────────────────────────────────────────────── */
    .cta-band {
      background: linear-gradient(135deg, var(--brand) 0%, #6d28d9 100%);
      color: #fff; text-align: center; padding: 5rem 1rem;
    }
    .cta-band h2 { font-size: 2.2rem; font-weight: 800; margin-bottom: 1rem; }
    .btn-white-cta {
      display: inline-block; padding: .85rem 2.4rem; background: #fff; color: var(--brand);
      font-weight: 700; border-radius: var(--radius); text-decoration: none; transition: transform .15s, box-shadow .15s;
    }
    .btn-white-cta:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); color: var(--brand); }

    /* ── FOOTER ──────────────────────────────────────────────────────────── */
    .site-footer { background: var(--text-dark); color: rgba(255,255,255,.7); padding: 4rem 0 0; }
    .footer-brand { font-size: 1.25rem; font-weight: 800; color: #fff; margin-bottom: .6rem; }
    .footer-tag { font-size: .83rem; max-width: 220px; line-height: 1.6; }
    .footer-h { font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; color: rgba(255,255,255,.45); margin-bottom: .9rem; }
    .footer-links { list-style: none; padding: 0; margin: 0; }
    .footer-links li { margin-bottom: .45rem; }
    .footer-links a { color: rgba(255,255,255,.65); text-decoration: none; font-size: .875rem; transition: color .15s; }
    .footer-links a:hover { color: #fff; }
    .social-links { display: flex; gap: 8px; margin-top: 1rem; }
    .social-links a {
      width: 34px; height: 34px; border-radius: 7px; background: rgba(255,255,255,.08);
      color: rgba(255,255,255,.65); display: flex; align-items: center; justify-content: center;
      text-decoration: none; font-size: .82rem; transition: background .15s, color .15s;
    }
    .social-links a:hover { background: var(--brand); color: #fff; }
    .footer-bar {
      margin-top: 3rem; padding: 1.25rem 0; border-top: 1px solid rgba(255,255,255,.08);
      font-size: .78rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;
    }
  </style>
</head>
<body>

  <!-- ══════════════════════════════════════════════════ TOP NAVIGATION ══ -->
  <!-- sticky; transparent over hero → white on scroll (JS toggles .scrolled) -->
  <nav class="site-nav" id="site-nav">
    <a href="/" class="nav-brand">
      <!-- Replace with your logo:
           <img src="/assets/__AP__/images/logo.svg" alt="" height="32"> -->
      <span class="nav-brand-dot"></span>
      {{ site_name or "YourBrand" }}
    </a>

    <!-- Desktop nav links — loop nav_links from get_context() -->
    <ul class="nav-links" id="nav-links">
      {% for lnk in nav_links %}
      <li {% if lnk.dropdown %}class="nav-dd"{% endif %}>
        <a href="{{ lnk.href }}" class="nav-link{% if lnk.active %} active{% endif %}">
          {{ lnk.label }}
          {% if lnk.dropdown %}<i class="bi bi-chevron-down" style="font-size:.6rem"></i>{% endif %}
        </a>
        {% if lnk.dropdown %}
        <ul class="nav-dd-menu">
          {% for sub in lnk.dropdown %}<li><a href="{{ sub.href }}">{{ sub.label }}</a></li>{% endfor %}
        </ul>
        {% endif %}
      </li>
      {% else %}
      <!-- Fallback hardcoded links when nav_links not set -->
      <li><a href="/" class="nav-link active">Home</a></li>
      <li><a href="/about" class="nav-link">About</a></li>
      <li class="nav-dd">
        <a href="/services" class="nav-link">Services <i class="bi bi-chevron-down" style="font-size:.6rem"></i></a>
        <ul class="nav-dd-menu">
          <li><a href="/services/web-design">Web Design</a></li>
          <li><a href="/services/development">Development</a></li>
          <li><a href="/services/consulting">Consulting</a></li>
        </ul>
      </li>
      <li><a href="/blog" class="nav-link">Blog</a></li>
      <li><a href="/contact" class="nav-link">Contact</a></li>
      {% endfor %}
    </ul>

    <a href="/contact" class="nav-cta">Get Started →</a>
    <button class="nav-ham" id="nav-ham" aria-label="Open menu">
      <span></span><span></span><span></span>
    </button>
  </nav>

  <!-- Mobile nav overlay -->
  <div class="mob-nav" id="mob-nav">
    <div class="mob-panel">
      <button class="mob-close" onclick="closeMobNav()" aria-label="Close">✕</button>
      <a href="/">Home</a><a href="/about">About</a>
      <a href="/services">Services</a><a href="/blog">Blog</a><a href="/contact">Contact</a>
      <a href="/contact" style="margin-top:auto;background:var(--brand);color:#fff;text-align:center">Get Started →</a>
    </div>
  </div>

  <!-- ══════════════════════════════════════════════════════════ HERO ══ -->
  <section class="hero">
    <div class="hero-inner">
      <div class="hero-badge">✨ v2.0 just launched — see what's new</div>
      <h1>{{ hero_title or title }}<br><span style="opacity:.85">{{ hero_subtitle or "That's Extraordinary" }}</span></h1>
      <p class="hero-sub">{{ hero_desc or "Your compelling one-sentence value proposition goes here. Make it clear, bold, and unmissable." }}</p>
      <div class="hero-btns">
        <a href="{{ hero_cta_href or '/contact' }}" class="btn-primary-hero">{{ hero_cta or "Get Started Free" }}</a>
        <a href="#features" class="btn-outline-hero">See How It Works</a>
      </div>
    </div>
  </section>

  <!-- Trust strip -->
  <div style="background:#fff;border-bottom:1px solid #f0ebff;padding:1rem 0">
    <div class="container text-center">
      <div class="row g-2">
        <div class="col-md-4"><span style="font-size:.83rem;font-weight:600;color:var(--text-muted)">⚡ 99.9% Uptime SLA</span></div>
        <div class="col-md-4"><span style="font-size:.83rem;font-weight:600;color:var(--text-muted)">🔒 SOC 2 Compliant</span></div>
        <div class="col-md-4"><span style="font-size:.83rem;font-weight:600;color:var(--text-muted)">💬 24/7 Live Support</span></div>
      </div>
    </div>
  </div>

  <!-- ═══════════════════════════════════════════════════ FEATURES ══ -->
  <section id="features">
    <div class="container">
      <div class="text-center mb-5">
        <p class="eyebrow">Features</p>
        <h2 class="section-title">Everything you need to succeed</h2>
        <p class="section-sub mx-auto" style="max-width:500px">A complete toolkit designed to solve real problems and deliver measurable results.</p>
      </div>
      <div class="row g-4">
        {% for feat in features %}
        <div class="col-md-6 col-lg-4">
          <div class="feat-card">
            <div class="feat-icon">{{ feat.icon }}</div>
            <div class="feat-title">{{ feat.title }}</div>
            <div class="feat-desc">{{ feat.desc }}</div>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- ═══════════════════════════════════════════════════ ABOUT ══ -->
  <section class="about-bg" id="about">
    <div class="container">
      <div class="row align-items-center g-5">
        <div class="col-lg-6">
          <p class="eyebrow">About Us</p>
          <h2 class="section-title">We're on a mission to simplify complexity</h2>
          <p style="color:var(--text-muted);font-size:1rem;line-height:1.8;margin-top:1rem">
            {{ about_text or "Replace this paragraph with your company story, mission statement, or a key differentiator. Keep it authentic and focused on how you solve your customer's biggest pain points." }}
          </p>
          <a href="/about" style="display:inline-block;margin-top:1.5rem;color:var(--brand);font-weight:700;text-decoration:none">Meet the team →</a>
        </div>
        <div class="col-lg-6">
          <!-- Replace placeholder with your image:
               <img src="/assets/__AP__/images/about.jpg" class="img-fluid rounded-4" alt="About"> -->
          <div style="background:var(--brand-light);border-radius:16px;aspect-ratio:4/3;display:flex;align-items:center;justify-content:center">
            <span style="font-size:5rem;opacity:.25">🏢</span>
          </div>
          <div class="row mt-3 g-2">
            {% for s in stats %}
            <div class="col-4"><div class="stat-box"><div class="stat-val">{{ s.value }}</div><div class="stat-lbl">{{ s.label }}</div></div></div>
            {% endfor %}
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ═══════════════════════════════════════════════ TESTIMONIALS ══ -->
  <section id="testimonials" style="background:#fff">
    <div class="container">
      <div class="text-center mb-5">
        <p class="eyebrow">Testimonials</p>
        <h2 class="section-title">Trusted by thousands</h2>
      </div>
      <div class="row g-4">
        {% for t in testimonials %}
        <div class="col-md-6 col-lg-4">
          <div class="testi-card">
            <div class="testi-stars">★★★★★</div>
            <p class="testi-text">"{{ t.text }}"</p>
            <div class="d-flex align-items-center gap-3">
              <div class="testi-av">{{ t.avatar or t.name[:2].upper() }}</div>
              <div><div class="testi-name">{{ t.name }}</div><div class="testi-role">{{ t.role }}</div></div>
            </div>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- ═════════════════════════════════════════════════ CTA BAND ══ -->
  <div class="cta-band">
    <div class="container">
      <h2>Ready to get started?</h2>
      <p style="opacity:.8;margin-bottom:2rem">Join thousands of teams already using {{ site_name or "our platform" }}.</p>
      <a href="/contact" class="btn-white-cta">Start for Free →</a>
    </div>
  </div>

  <!-- ════════════════════════════════════════════════════ FOOTER ══ -->
  <footer class="site-footer">
    <div class="container">
      <div class="row g-5">
        <div class="col-lg-3">
          <div class="footer-brand">{{ site_name or "YourBrand" }}</div>
          <p class="footer-tag">{{ footer_tagline or "Building better products for better businesses." }}</p>
          <div class="social-links">
            <!-- Replace href="#" with real URLs -->
            <a href="#" aria-label="Twitter">𝕏</a>
            <a href="#" aria-label="LinkedIn">in</a>
            <a href="#" aria-label="GitHub">GH</a>
            <a href="#" aria-label="YouTube">▶</a>
          </div>
        </div>
        <div class="col-6 col-lg-2">
          <div class="footer-h">Product</div>
          <ul class="footer-links">
            <li><a href="/features">Features</a></li><li><a href="/pricing">Pricing</a></li>
            <li><a href="/changelog">Changelog</a></li><li><a href="/roadmap">Roadmap</a></li>
          </ul>
        </div>
        <div class="col-6 col-lg-2">
          <div class="footer-h">Company</div>
          <ul class="footer-links">
            <li><a href="/about">About</a></li><li><a href="/blog">Blog</a></li>
            <li><a href="/careers">Careers</a></li><li><a href="/contact">Contact</a></li>
          </ul>
        </div>
        <div class="col-6 col-lg-2">
          <div class="footer-h">Resources</div>
          <ul class="footer-links">
            <li><a href="/docs">Docs</a></li><li><a href="/api">API</a></li>
            <li><a href="/support">Support</a></li><li><a href="/status">Status</a></li>
          </ul>
        </div>
        <div class="col-6 col-lg-2">
          <div class="footer-h">Legal</div>
          <ul class="footer-links">
            <li><a href="/privacy">Privacy</a></li><li><a href="/terms">Terms</a></li>
            <li><a href="/cookies">Cookies</a></li>
          </ul>
        </div>
      </div>
      <div class="footer-bar">
        <span>© {{ frappe.utils.now_datetime().year }} {{ site_name or "YourBrand" }}. All rights reserved.</span>
        <span>Built with Frappe Framework</span>
      </div>
    </div>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
  <script>
  // ── Navbar: add .scrolled when page is scrolled past 60px ──────────────────
  (function () {
    var nav = document.getElementById('site-nav');
    function onScroll() { nav.classList.toggle('scrolled', window.scrollY > 60); }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  })();

  // ── Mobile nav ──────────────────────────────────────────────────────────────
  function openMobNav()  { document.getElementById('mob-nav').style.display = 'block'; document.body.style.overflow = 'hidden'; }
  function closeMobNav() { document.getElementById('mob-nav').style.display = 'none';  document.body.style.overflow = ''; }
  document.getElementById('nav-ham').addEventListener('click', openMobNav);
  document.getElementById('mob-nav').addEventListener('click', function (e) { if (e.target === this) closeMobNav(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMobNav(); });

  // ── Active nav link: mark the link whose href matches current path ──────────
  (function () {
    var path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(function (a) {
      if (a.getAttribute('href') === path) a.classList.add('active');
    });
  })();

  // ── Smooth scroll for on-page anchors ──────────────────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var t = document.querySelector(this.getAttribute('href'));
      if (t) { e.preventDefault(); t.scrollIntoView({ behavior: 'smooth' }); }
    });
  });

  // ── Frappe API hook (uncomment to use frappe.call / frappe.session) ─────────
  // frappe.ready(function () {
  //   frappe.call({ method: "__AP__.api.my_module.get_data", args: {}, callback: r => console.log(r.message) });
  // });
  </script>
</body>
</html>'''.replace('__CC__', cc).replace('__AP__', app)


def _www_tpl_leftnav(cc, app):
    """Full app-shell with fixed collapsible left sidebar navigation."""
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
  <style>
    :root {
      --brand:#5c4da8; --brand-dark:#3d2f8f; --brand-light:#ede9fe;
      --accent:#8b5cf6; --text-dark:#1e1b3a; --text-muted:#6b7280;
      --sidebar-w:260px; --sidebar-collapsed-w:60px;
      --header-h:60px; --radius:10px;
      --shadow:0 4px 20px rgba(92,77,168,.12);
    }
    *, *::before, *::after { box-sizing: border-box; }
    html, body { height: 100%; margin: 0; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:var(--text-dark); background:#f5f4fb; }

    /* ── APP SHELL LAYOUT ─────────────────────────────────────────────────── */
    .app-shell { display: flex; height: 100vh; overflow: hidden; }

    /* ── LEFT SIDEBAR ─────────────────────────────────────────────────────── */
    .sidebar {
      width: var(--sidebar-w); background: #fff; border-right: 1px solid #ede9fe;
      display: flex; flex-direction: column; flex-shrink: 0;
      transition: width .25s ease; overflow: hidden; z-index: 200;
    }
    /* Collapsed: icon-only mode */
    .sidebar.collapsed { width: var(--sidebar-collapsed-w); }
    .sidebar.collapsed .nav-label,
    .sidebar.collapsed .nav-group-hdr,
    .sidebar.collapsed .sidebar-user-info { display: none; }
    .sidebar.collapsed .sidebar-logo-text { display: none; }

    /* Sidebar logo area */
    .sidebar-logo {
      display: flex; align-items: center; gap: 10px;
      padding: 0 16px; height: var(--header-h);
      border-bottom: 1px solid #ede9fe; flex-shrink: 0;
    }
    .sidebar-logo-icon {
      width: 32px; height: 32px; border-radius: 8px;
      background: var(--brand); display: flex; align-items: center;
      justify-content: center; color: #fff; font-weight: 800; font-size: .9rem; flex-shrink: 0;
    }
    .sidebar-logo-text { font-weight: 800; font-size: 1rem; color: var(--text-dark); white-space: nowrap; }

    /* Sidebar nav */
    .sidebar-nav { flex: 1; overflow-y: auto; padding: 12px 8px; }
    .sidebar-nav::-webkit-scrollbar { width: 4px; }
    .sidebar-nav::-webkit-scrollbar-thumb { background: #e5e2f0; border-radius: 2px; }
    .nav-group { margin-bottom: 6px; }
    .nav-group-hdr {
      font-size: .68rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em;
      color: var(--text-muted); padding: 8px 10px 4px; white-space: nowrap;
    }
    .sidebar-link {
      display: flex; align-items: center; gap: 10px; padding: 9px 10px;
      color: var(--text-muted); font-size: .875rem; font-weight: 500;
      text-decoration: none; border-radius: 8px; transition: background .12s, color .12s;
      white-space: nowrap;
    }
    .sidebar-link:hover { background: var(--brand-light); color: var(--brand); }
    .sidebar-link.active { background: var(--brand-light); color: var(--brand); font-weight: 700; }
    .sidebar-link .link-icon { width: 18px; text-align: center; font-size: 1rem; flex-shrink: 0; }

    /* Sidebar user footer */
    .sidebar-user {
      border-top: 1px solid #ede9fe; padding: 12px 14px;
      display: flex; align-items: center; gap: 10px; flex-shrink: 0;
    }
    .user-av {
      width: 34px; height: 34px; border-radius: 50%; background: var(--brand-light);
      color: var(--brand); font-weight: 700; font-size: .85rem; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
    }
    .sidebar-user-info { min-width: 0; }
    .user-name { font-size: .85rem; font-weight: 700; color: var(--text-dark); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .user-role { font-size: .72rem; color: var(--text-muted); }

    /* Mobile sidebar overlay */
    .sidebar-overlay {
      display: none; position: fixed; inset: 0; background: rgba(0,0,0,.4);
      backdrop-filter: blur(2px); z-index: 199;
    }
    @media (max-width: 768px) {
      .sidebar { position: fixed; top: 0; bottom: 0; left: 0; transform: translateX(-100%); transition: transform .25s; width: var(--sidebar-w) !important; }
      .sidebar.mob-open { transform: translateX(0); }
      .sidebar-overlay.active { display: block; }
    }

    /* ── MAIN AREA ────────────────────────────────────────────────────────── */
    .main-area { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }

    /* Top header */
    .top-header {
      height: var(--header-h); background: #fff; border-bottom: 1px solid #ede9fe;
      display: flex; align-items: center; padding: 0 20px; gap: 12px; flex-shrink: 0;
    }
    .hamburger-btn {
      background: none; border: none; cursor: pointer; padding: 6px 8px;
      border-radius: 6px; color: var(--text-muted); font-size: 1.1rem; transition: background .12s;
    }
    .hamburger-btn:hover { background: var(--brand-light); color: var(--brand); }
    /* Breadcrumb */
    .top-bc { display: flex; align-items: center; gap: 6px; font-size: .83rem; color: var(--text-muted); flex: 1; }
    .top-bc a { color: var(--brand); text-decoration: none; }
    .top-bc-sep { opacity: .4; }
    /* Search */
    .header-search {
      display: flex; align-items: center; gap: 6px;
      background: #f5f4fb; border-radius: 8px; padding: 6px 12px;
      border: 1px solid transparent; transition: border-color .15s;
    }
    .header-search:focus-within { border-color: var(--brand-light); background: #fff; }
    .header-search input { border: none; background: transparent; outline: none; font-size: .85rem; width: 180px; color: var(--text-dark); }
    /* Header actions */
    .header-actions { display: flex; align-items: center; gap: 8px; }
    .icon-btn {
      width: 34px; height: 34px; border: none; background: #f5f4fb; border-radius: 8px;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      font-size: .95rem; color: var(--text-muted); transition: background .12s, color .12s; position: relative;
    }
    .icon-btn:hover { background: var(--brand-light); color: var(--brand); }
    .badge-dot {
      position: absolute; top: 4px; right: 4px; width: 8px; height: 8px;
      background: #dc2626; border-radius: 50%; border: 2px solid #fff;
    }
    .header-av {
      width: 32px; height: 32px; border-radius: 50%; background: var(--brand);
      color: #fff; font-weight: 700; font-size: .78rem;
      display: flex; align-items: center; justify-content: center; cursor: pointer;
    }

    /* Page content */
    .page-main { flex: 1; overflow-y: auto; padding: 24px; }
    .page-main::-webkit-scrollbar { width: 6px; }
    .page-main::-webkit-scrollbar-thumb { background: #e5e2f0; border-radius: 3px; }

    /* ── KPI CARDS ────────────────────────────────────────────────────────── */
    .kpi-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; margin-bottom: 24px; }
    .kpi-card {
      background: #fff; border-radius: var(--radius); padding: 20px 22px;
      box-shadow: var(--shadow); border-left: 4px solid var(--brand);
      display: flex; align-items: flex-start; gap: 14px;
    }
    .kpi-icon { font-size: 1.6rem; }
    .kpi-lbl { font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted); margin-bottom: 4px; }
    .kpi-val { font-size: 1.7rem; font-weight: 900; color: var(--text-dark); line-height: 1; }
    .kpi-chg { font-size: .78rem; font-weight: 700; margin-top: 4px; }
    .kpi-chg.up   { color: #059669; }
    .kpi-chg.down { color: #dc2626; }

    /* ── CONTENT GRID ─────────────────────────────────────────────────────── */
    .content-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }
    @media (max-width: 900px) { .content-grid { grid-template-columns: 1fr; } }
    .card-panel { background: #fff; border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }
    .card-panel-hdr {
      padding: 14px 18px; font-weight: 700; font-size: .9rem; color: var(--text-dark);
      border-bottom: 1px solid #f0ebff; display: flex; align-items: center; justify-content: space-between;
    }
    .card-panel-body { padding: 16px 18px; }
    /* Data table */
    .dk-table { width: 100%; border-collapse: collapse; font-size: .83rem; }
    .dk-table th { color: var(--brand); font-weight: 700; padding: 8px 10px; text-align: left; border-bottom: 2px solid var(--brand-light); background: #faf8ff; }
    .dk-table td { padding: 9px 10px; border-bottom: 1px solid #f5f3fc; }
    .dk-table tr:hover td { background: #faf8ff; cursor: pointer; }
    .dk-badge { display: inline-block; padding: 2px 9px; border-radius: 12px; font-size: .75rem; font-weight: 700; }
    .dk-badge.green  { background: #dcfce7; color: #166534; }
    .dk-badge.yellow { background: #fef9c3; color: #713f12; }
    .dk-badge.red    { background: #fee2e2; color: #7f1d1d; }
    .dk-badge.blue   { background: #dbeafe; color: #1e3a5f; }
    /* Activity feed */
    .activity-item { display: flex; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f5f3fc; }
    .activity-item:last-child { border-bottom: none; }
    .act-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--brand-light); border: 2px solid var(--brand); flex-shrink: 0; margin-top: 4px; }
    .act-text { font-size: .83rem; color: var(--text-dark); line-height: 1.5; }
    .act-time { font-size: .72rem; color: var(--text-muted); }
  </style>
</head>
<body>
<div class="app-shell">

  <!-- ═══════════════════════════════════════════════════ SIDEBAR ══ -->
  <!-- Fixed left sidebar with logo, nav groups, and user footer      -->
  <aside class="sidebar" id="sidebar">
    <!-- Logo / brand -->
    <div class="sidebar-logo">
      <div class="sidebar-logo-icon">{{ (site_name or "Y")[0] }}</div>
      <!-- Replace with: <img src="/assets/__AP__/images/logo.svg" alt="" height="28"> -->
      <span class="sidebar-logo-text">{{ site_name or "YourApp" }}</span>
    </div>

    <!-- Navigation groups — populated from sidebar_groups in get_context() -->
    <nav class="sidebar-nav">
      {% for grp in sidebar_groups %}
      <div class="nav-group">
        <div class="nav-group-hdr">{{ grp.label }}</div>
        {% for lnk in grp.links %}
        <a href="{{ lnk.href }}" class="sidebar-link {% if lnk.active %}active{% endif %}">
          <span class="link-icon">{{ lnk.icon }}</span>
          <span class="nav-label">{{ lnk.label }}</span>
        </a>
        {% endfor %}
      </div>
      {% else %}
      <!-- Fallback nav (used when sidebar_groups not set) -->
      <div class="nav-group">
        <div class="nav-group-hdr">Main</div>
        <a href="#" class="sidebar-link active"><span class="link-icon">🏠</span><span class="nav-label">Dashboard</span></a>
        <a href="#" class="sidebar-link"><span class="link-icon">📊</span><span class="nav-label">Analytics</span></a>
        <a href="#" class="sidebar-link"><span class="link-icon">📋</span><span class="nav-label">Reports</span></a>
      </div>
      <div class="nav-group">
        <div class="nav-group-hdr">Management</div>
        <a href="#" class="sidebar-link"><span class="link-icon">👥</span><span class="nav-label">Users</span></a>
        <a href="#" class="sidebar-link"><span class="link-icon">⚙️</span><span class="nav-label">Settings</span></a>
        <a href="#" class="sidebar-link"><span class="link-icon">🔔</span><span class="nav-label">Notifications</span></a>
      </div>
      <div class="nav-group">
        <div class="nav-group-hdr">Data</div>
        <a href="#" class="sidebar-link"><span class="link-icon">📁</span><span class="nav-label">Documents</span></a>
        <a href="#" class="sidebar-link"><span class="link-icon">🗄️</span><span class="nav-label">Exports</span></a>
      </div>
      {% endfor %}
    </nav>

    <!-- User info at bottom of sidebar -->
    <div class="sidebar-user">
      <div class="user-av">{{ (user_full_name or frappe.session.user or "U")[:2].upper() }}</div>
      <div class="sidebar-user-info">
        <div class="user-name">{{ user_full_name or frappe.session.user }}</div>
        <div class="user-role">{{ user_role or "User" }}</div>
      </div>
    </div>
  </aside>

  <!-- Overlay for mobile -->
  <div class="sidebar-overlay" id="sidebar-overlay" onclick="closeSidebar()"></div>

  <!-- ═══════════════════════════════════════════════ MAIN AREA ══ -->
  <div class="main-area">

    <!-- Top header bar -->
    <header class="top-header">
      <!-- Hamburger: collapses sidebar on desktop, opens overlay on mobile -->
      <button class="hamburger-btn" onclick="toggleSidebar()" aria-label="Toggle sidebar">☰</button>

      <!-- Breadcrumb -->
      <div class="top-bc">
        <a href="/">Home</a>
        <span class="top-bc-sep">/</span>
        <span>{{ page_section or "Dashboard" }}</span>
        {% if page_subsection %}
        <span class="top-bc-sep">/</span>
        <span style="color:var(--text-dark);font-weight:600">{{ page_subsection }}</span>
        {% endif %}
      </div>

      <!-- Search bar -->
      <div class="header-search">
        <span style="color:var(--text-muted)">🔍</span>
        <input type="search" placeholder="Search…" aria-label="Search">
      </div>

      <!-- Actions -->
      <div class="header-actions">
        <button class="icon-btn" title="Notifications">
          🔔 <span class="badge-dot"></span>
        </button>
        <button class="icon-btn" title="Help">❓</button>
        <div class="header-av" title="{{ frappe.session.user }}">
          {{ (user_full_name or frappe.session.user or "U")[:2].upper() }}
        </div>
      </div>
    </header>

    <!-- Page main content -->
    <main class="page-main">
      <!-- Page title row -->
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:10px">
        <div>
          <h1 style="font-size:1.5rem;font-weight:800;color:var(--text-dark);margin:0">{{ title }}</h1>
          <p style="color:var(--text-muted);font-size:.85rem;margin:4px 0 0">
            Welcome back, {{ user_full_name or frappe.session.user }}
          </p>
        </div>
        <!-- Primary action button — customise per page -->
        <button style="background:var(--brand);color:#fff;border:none;padding:.55rem 1.2rem;border-radius:8px;font-weight:700;font-size:.875rem;cursor:pointer">
          + New Record
        </button>
      </div>

      <!-- KPI Cards row -->
      <div class="kpi-row">
        {% for kpi in kpi_cards %}
        <div class="kpi-card" style="border-color:{{ kpi.color }}">
          <div class="kpi-icon">{{ kpi.icon }}</div>
          <div>
            <div class="kpi-lbl">{{ kpi.label }}</div>
            <div class="kpi-val" style="color:{{ kpi.color }}">{{ kpi.value }}</div>
            <div class="kpi-chg {{ 'up' if kpi.up else 'down' }}">
              {{ '▲' if kpi.up else '▼' }} {{ kpi.change }} vs last period
            </div>
          </div>
        </div>
        {% endfor %}
      </div>

      <!-- 2-column content grid -->
      <div class="content-grid">
        <!-- Main table panel -->
        <div class="card-panel">
          <div class="card-panel-hdr">
            <span>Recent Records</span>
            <a href="#" style="font-size:.78rem;color:var(--brand);text-decoration:none;font-weight:600">View all →</a>
          </div>
          <div style="overflow-x:auto">
            <table class="dk-table">
              <thead>
                <tr><th>Name</th><th>Date</th><th>Amount</th><th>Status</th></tr>
              </thead>
              <tbody>
                {# Replace with: {% for row in records %} #}
                {% for i in range(5) %}
                <tr>
                  <td>Record-{{ 1000 + i }}</td>
                  <td>{{ frappe.utils.today() }}</td>
                  <td>₹ {{ (i+1)*1234 }}</td>
                  <td><span class="dk-badge {{ ['green','yellow','blue','green','red'][i] }}">{{ ['Completed','Pending','Active','Completed','Rejected'][i] }}</span></td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Right: activity feed -->
        <div class="card-panel">
          <div class="card-panel-hdr">Activity Feed</div>
          <div class="card-panel-body">
            {# Populate from context.activity_feed #}
            <div class="activity-item">
              <div class="act-dot"></div>
              <div><div class="act-text">New order #SO-0042 created by Ravi</div><div class="act-time">2 min ago</div></div>
            </div>
            <div class="activity-item">
              <div class="act-dot" style="border-color:#059669;background:#dcfce7"></div>
              <div><div class="act-text">Invoice #INV-0019 marked as Paid</div><div class="act-time">15 min ago</div></div>
            </div>
            <div class="activity-item">
              <div class="act-dot" style="border-color:#b45309;background:#fef3c7"></div>
              <div><div class="act-text">Approval request from Priya Sharma</div><div class="act-time">1 hr ago</div></div>
            </div>
            <div class="activity-item">
              <div class="act-dot"></div>
              <div><div class="act-text">Report "Monthly Sales" was exported</div><div class="act-time">3 hr ago</div></div>
            </div>
            <div class="activity-item">
              <div class="act-dot" style="border-color:#dc2626;background:#fee2e2"></div>
              <div><div class="act-text">Alert: Low stock on Item A-2290</div><div class="act-time">5 hr ago</div></div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div><!-- /.main-area -->
</div><!-- /.app-shell -->

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
// ── Sidebar toggle ────────────────────────────────────────────────────────────
var sidebar  = document.getElementById('sidebar');
var overlay  = document.getElementById('sidebar-overlay');
var isMobile = function () { return window.innerWidth <= 768; };

function toggleSidebar() {
  if (isMobile()) {
    // Mobile: slide in/out as overlay
    sidebar.classList.toggle('mob-open');
    overlay.classList.toggle('active');
  } else {
    // Desktop: collapse to icon-only width
    sidebar.classList.toggle('collapsed');
  }
}
function closeSidebar() {
  sidebar.classList.remove('mob-open');
  overlay.classList.remove('active');
}
document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeSidebar(); });

// ── Sidebar active link ───────────────────────────────────────────────────────
document.querySelectorAll('.sidebar-link').forEach(function (a) {
  a.addEventListener('click', function () {
    document.querySelectorAll('.sidebar-link').forEach(function (x) { x.classList.remove('active'); });
    this.classList.add('active');
  });
});

// ── Frappe API hook ───────────────────────────────────────────────────────────
// frappe.ready(function () {
//   frappe.call({ method: "__AP__.api.my_module.get_dashboard", args: {}, callback: r => { /* render */ } });
// });
</script>
</body>
</html>'''.replace('__CC__', cc).replace('__AP__', app)


def _www_tpl_spa(cc, app):
    """Single-page app — sticky scroll-spy nav, all sections on one page."""
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
  <style>
    :root {
      --brand:#5c4da8; --brand-dark:#3d2f8f; --brand-light:#ede9fe;
      --accent:#8b5cf6; --text-dark:#1e1b3a; --text-muted:#6b7280;
      --radius:10px; --shadow:0 4px 20px rgba(92,77,168,.12); --nav-h:60px;
    }
    html { scroll-behavior: smooth; }
    body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:var(--text-dark); }
    /* Reading progress bar at very top */
    #progress-bar { position:fixed;top:0;left:0;height:3px;background:var(--brand);width:0%;z-index:9999;transition:width .1s; }
    /* Sticky nav */
    .spa-nav {
      position:sticky;top:0;z-index:100;background:#fff;border-bottom:1px solid #ede9fe;
      height:var(--nav-h);display:flex;align-items:center;padding:0 2rem;gap:1.5rem;
      box-shadow:0 2px 8px rgba(92,77,168,.08);
    }
    .spa-brand { font-weight:800;font-size:1.1rem;color:var(--text-dark);text-decoration:none; }
    .spa-nav-links { display:flex;gap:4px;flex:1; }
    .spa-nav-links a {
      padding:.4rem .8rem;border-radius:6px;font-size:.875rem;font-weight:500;
      color:var(--text-muted);text-decoration:none;transition:color .15s,background .15s;
    }
    .spa-nav-links a:hover { color:var(--brand);background:var(--brand-light); }
    .spa-nav-links a.active { color:var(--brand);background:var(--brand-light);font-weight:700; }
    .spa-nav-cta { margin-left:auto;padding:.4rem 1.1rem;background:var(--brand);color:#fff;border:none;border-radius:7px;font-weight:700;font-size:.85rem;cursor:pointer;text-decoration:none; }
    @media(max-width:640px){ .spa-nav-links{display:none;} }
    /* Hero */
    .hero { min-height:100vh;display:flex;align-items:center;background:linear-gradient(135deg,var(--brand),#6d28d9,var(--accent));color:#fff;text-align:center; }
    .hero h1 { font-size:clamp(2.2rem,6vw,4rem);font-weight:900;line-height:1.1;letter-spacing:-.03em;margin-bottom:1.25rem; }
    .hero p  { font-size:1.1rem;opacity:.8;max-width:520px;margin:0 auto 2rem; }
    .hero-btns { display:flex;gap:12px;justify-content:center;flex-wrap:wrap; }
    .btn-hw { padding:.75rem 2rem;border-radius:var(--radius);font-weight:700;text-decoration:none;border:none;cursor:pointer; }
    .btn-hw.white { background:#fff;color:var(--brand); }
    .btn-hw.outline { background:transparent;border:2px solid rgba(255,255,255,.5);color:#fff; }
    /* Section styles */
    .spa-section { padding:5.5rem 0; }
    .spa-section.alt { background:#f8f5ff; }
    .eyebrow { font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--brand);margin-bottom:.6rem; }
    .sec-title { font-size:clamp(1.7rem,4vw,2.4rem);font-weight:800;color:var(--text-dark);line-height:1.15; }
    .sec-sub { font-size:1rem;color:var(--text-muted);margin-top:.75rem; }
    /* Feature card */
    .feat-card { background:#fff;border-radius:var(--radius);padding:24px 20px;box-shadow:var(--shadow);height:100%;border:1px solid #f0ebff;transition:transform .2s,box-shadow .2s; }
    .feat-card:hover { transform:translateY(-3px);box-shadow:0 8px 30px rgba(92,77,168,.18); }
    .feat-ico { font-size:1.9rem;margin-bottom:12px; }
    /* Steps */
    .step-num { width:48px;height:48px;border-radius:50%;background:var(--brand);color:#fff;font-size:1.1rem;font-weight:900;display:flex;align-items:center;justify-content:center;flex-shrink:0; }
    /* Testimonials */
    .testi-card { background:#fff;border-radius:var(--radius);padding:24px;box-shadow:var(--shadow);border:1px solid #f0ebff;height:100%; }
    /* Pricing */
    .price-card { background:#fff;border-radius:var(--radius);padding:28px 24px;box-shadow:var(--shadow);border:1px solid #f0ebff;text-align:center;height:100%;transition:transform .2s; }
    .price-card.featured { background:var(--brand);color:#fff;transform:scale(1.04); }
    .price-card.featured .text-muted { color:rgba(255,255,255,.75) !important; }
    .price-amount { font-size:2.6rem;font-weight:900; }
    /* FAQ */
    .faq-item { border-radius:var(--radius);background:#fff;box-shadow:var(--shadow);margin-bottom:8px;overflow:hidden;border:1px solid #f0ebff; }
    .faq-q { padding:16px 20px;font-weight:700;cursor:pointer;display:flex;justify-content:space-between;align-items:center;font-size:.92rem; }
    .faq-q:hover { background:#faf8ff; }
    .faq-a { padding:0 20px;max-height:0;overflow:hidden;transition:max-height .3s,padding .3s;font-size:.88rem;color:var(--text-muted);line-height:1.7; }
    .faq-item.open .faq-a { max-height:200px;padding:0 20px 16px; }
    .faq-item.open .faq-chevron { transform:rotate(180deg); }
    .faq-chevron { transition:transform .3s;font-size:.75rem; }
    /* Contact */
    .form-inp {
      width:100%;padding:10px 14px;border:1.5px solid #e5e2f0;border-radius:8px;
      font-size:.875rem;font-family:inherit;outline:none;transition:border-color .15s;
    }
    .form-inp:focus { border-color:var(--brand); }
    .form-lbl { font-size:.82rem;font-weight:700;color:var(--text-dark);margin-bottom:5px;display:block; }
    /* Back to top */
    #back-top {
      position:fixed;bottom:24px;right:24px;width:44px;height:44px;border-radius:50%;
      background:var(--brand);color:#fff;border:none;cursor:pointer;
      font-size:1.1rem;display:flex;align-items:center;justify-content:center;
      opacity:0;pointer-events:none;transition:opacity .25s,transform .25s;
      box-shadow:0 4px 16px rgba(92,77,168,.4);
    }
    #back-top.visible { opacity:1;pointer-events:auto; }
    #back-top:hover { transform:translateY(-2px); }
    /* Footer */
    .spa-footer { background:var(--text-dark);color:rgba(255,255,255,.65);text-align:center;padding:2.5rem 1rem; }
    .spa-footer a { color:rgba(255,255,255,.65);text-decoration:none; }
    .spa-footer a:hover { color:#fff; }
  </style>
</head>
<body>
  <!-- Reading progress bar -->
  <div id="progress-bar"></div>

  <!-- ═════════════════════════════════════════ STICKY SCROLL-SPY NAV ══ -->
  <nav class="spa-nav" id="spa-nav">
    <a href="#hero" class="spa-brand">{{ site_name or "YourBrand" }}</a>
    <div class="spa-nav-links" id="spa-nav-links">
      <a href="#features"     class="spa-link" data-section="features">Features</a>
      <a href="#how-it-works" class="spa-link" data-section="how-it-works">How It Works</a>
      <a href="#testimonials" class="spa-link" data-section="testimonials">Reviews</a>
      <a href="#pricing"      class="spa-link" data-section="pricing">Pricing</a>
      <a href="#faq"          class="spa-link" data-section="faq">FAQ</a>
      <a href="#contact"      class="spa-link" data-section="contact">Contact</a>
    </div>
    <a href="#contact" class="spa-nav-cta">Get Started</a>
  </nav>

  <!-- ══════════════════════════════════════════════════════ HERO ══ -->
  <section class="hero" id="hero">
    <div class="container">
      <div style="max-width:680px;margin:0 auto">
        <div style="display:inline-block;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);color:#fff;padding:4px 14px;border-radius:20px;font-size:.8rem;font-weight:600;margin-bottom:1.5rem">
          ✨ {{ hero_badge or "Now in public beta" }}
        </div>
        <h1>{{ title }}</h1>
        <p>{{ hero_desc or "Your compelling value proposition. One clear sentence that makes visitors stay." }}</p>
        <div class="hero-btns">
          <a href="#contact" class="btn-hw white">Get Started Free</a>
          <a href="#how-it-works" class="btn-hw outline">See How It Works</a>
        </div>
      </div>
    </div>
  </section>

  <!-- ════════════════════════════════════════════════ FEATURES ══ -->
  <section class="spa-section" id="features">
    <div class="container">
      <div class="text-center mb-5">
        <p class="eyebrow">Features</p>
        <h2 class="sec-title">Everything you need</h2>
        <p class="sec-sub mx-auto" style="max-width:480px">Designed to solve real problems and deliver measurable value from day one.</p>
      </div>
      <div class="row g-4">
        {% for f in features %}
        <div class="col-md-6 col-lg-4">
          <div class="feat-card"><div class="feat-ico">{{ f.icon }}</div><strong style="display:block;margin-bottom:8px;color:var(--text-dark)">{{ f.title }}</strong><span style="font-size:.875rem;color:var(--text-muted);line-height:1.65">{{ f.desc }}</span></div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- ══════════════════════════════════════ HOW IT WORKS ══ -->
  <section class="spa-section alt" id="how-it-works">
    <div class="container">
      <div class="text-center mb-5">
        <p class="eyebrow">Process</p>
        <h2 class="sec-title">How it works</h2>
      </div>
      <div class="row g-4 justify-content-center">
        {% for step in steps %}
        <div class="col-md-4">
          <div style="text-align:center;padding:20px">
            <div class="step-num" style="margin:0 auto 16px">{{ step.num }}</div>
            <h4 style="font-weight:800;color:var(--text-dark);margin-bottom:10px">{{ step.title }}</h4>
            <p style="font-size:.9rem;color:var(--text-muted);line-height:1.7">{{ step.desc }}</p>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- ══════════════════════════════════════ TESTIMONIALS ══ -->
  <section class="spa-section" id="testimonials">
    <div class="container">
      <div class="text-center mb-5">
        <p class="eyebrow">Testimonials</p>
        <h2 class="sec-title">Loved by teams worldwide</h2>
      </div>
      <div class="row g-4">
        {% for t in testimonials %}
        <div class="col-md-4">
          <div class="testi-card">
            <div style="color:#f59e0b;margin-bottom:10px">★★★★★</div>
            <p style="font-size:.9rem;color:var(--text-muted);font-style:italic;line-height:1.7;margin-bottom:16px">"{{ t.text }}"</p>
            <div style="display:flex;gap:10px;align-items:center">
              <div style="width:38px;height:38px;border-radius:50%;background:var(--brand-light);color:var(--brand);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.8rem">{{ t.name[:2].upper() }}</div>
              <div><strong style="font-size:.88rem;color:var(--text-dark)">{{ t.name }}</strong><br><span style="font-size:.78rem;color:var(--text-muted)">{{ t.role }}</span></div>
            </div>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- ════════════════════════════════════════════ PRICING ══ -->
  <section class="spa-section alt" id="pricing">
    <div class="container">
      <div class="text-center mb-5">
        <p class="eyebrow">Pricing</p>
        <h2 class="sec-title">Simple, transparent pricing</h2>
        <p class="sec-sub mx-auto" style="max-width:400px">No hidden fees. Cancel anytime.</p>
      </div>
      <div class="row g-4 justify-content-center align-items-center">
        {% for plan in plans %}
        <div class="col-md-4">
          <div class="price-card {% if plan.featured %}featured{% endif %}">
            {% if plan.featured %}<div style="display:inline-block;background:rgba(255,255,255,.2);color:#fff;font-size:.75rem;font-weight:700;padding:3px 12px;border-radius:20px;margin-bottom:10px">Most Popular</div>{% endif %}
            <h4 style="font-weight:800;margin-bottom:4px">{{ plan.name }}</h4>
            <div class="price-amount">{{ plan.price }}</div>
            <div class="text-muted" style="font-size:.85rem;margin-bottom:16px">{{ plan.period }}</div>
            <ul style="list-style:none;padding:0;margin:0 0 20px;text-align:left">
              {% for feat in plan.features %}<li style="padding:5px 0;font-size:.88rem;display:flex;gap:8px;align-items:center"><span style="color:{% if plan.featured %}rgba(255,255,255,.8){% else %}var(--brand){% endif %}">✓</span>{{ feat }}</li>{% endfor %}
            </ul>
            <a href="{{ plan.href }}" style="display:block;padding:.7rem;border-radius:8px;font-weight:700;text-decoration:none;text-align:center;{% if plan.featured %}background:#fff;color:var(--brand){% else %}background:var(--brand);color:#fff{% endif %}">{{ plan.cta }}</a>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- ═══════════════════════════════════════════════ FAQ ══ -->
  <section class="spa-section" id="faq">
    <div class="container" style="max-width:720px">
      <div class="text-center mb-5">
        <p class="eyebrow">FAQ</p>
        <h2 class="sec-title">Common questions</h2>
      </div>
      {% for item in faqs %}
      <div class="faq-item" data-idx="{{ loop.index }}">
        <div class="faq-q" onclick="toggleFaq(this.parentElement)">
          <span>{{ item.q }}</span><span class="faq-chevron">▼</span>
        </div>
        <div class="faq-a">{{ item.a }}</div>
      </div>
      {% endfor %}
    </div>
  </section>

  <!-- ══════════════════════════════════════════ CONTACT ══ -->
  <section class="spa-section alt" id="contact">
    <div class="container" style="max-width:600px">
      <div class="text-center mb-5">
        <p class="eyebrow">Contact</p>
        <h2 class="sec-title">Get in touch</h2>
        <p class="sec-sub">Fill in the form and we'll be back within 24 hours.</p>
      </div>
      <div style="background:#fff;border-radius:var(--radius);padding:32px;box-shadow:var(--shadow)">
        <form id="contact-form">
          <div class="row g-3">
            <div class="col-md-6"><label class="form-lbl">Full Name *</label><input class="form-inp" type="text" name="name" placeholder="Your name" required></div>
            <div class="col-md-6"><label class="form-lbl">Email *</label><input class="form-inp" type="email" name="email" placeholder="you@company.com" required></div>
            <div class="col-12"><label class="form-lbl">Message *</label><textarea class="form-inp" name="message" rows="4" placeholder="How can we help?" required style="resize:vertical"></textarea></div>
            <div class="col-12"><button type="submit" style="width:100%;padding:.75rem;background:var(--brand);color:#fff;border:none;border-radius:8px;font-weight:700;font-size:1rem;cursor:pointer">Send Message</button></div>
          </div>
        </form>
        <div id="form-msg" style="display:none;margin-top:12px;padding:10px 14px;border-radius:7px;font-size:.88rem"></div>
      </div>
    </div>
  </section>

  <!-- ════════════════════════════════════════════ FOOTER ══ -->
  <footer class="spa-footer">
    <div class="container">
      <div style="margin-bottom:16px">
        <a href="#hero" style="font-weight:800;font-size:1.1rem;color:#fff">{{ site_name or "YourBrand" }}</a>
      </div>
      <div style="display:flex;justify-content:center;gap:16px;flex-wrap:wrap;font-size:.85rem;margin-bottom:16px">
        <a href="#features">Features</a><a href="#pricing">Pricing</a>
        <a href="#faq">FAQ</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a>
      </div>
      <div style="font-size:.78rem">© {{ frappe.utils.now_datetime().year }} {{ site_name or "YourBrand" }}</div>
    </div>
  </footer>

  <!-- Back to top FAB -->
  <button id="back-top" onclick="window.scrollTo({top:0,behavior:'smooth'})" title="Back to top">▲</button>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
  <script>
  // ── Reading progress bar ────────────────────────────────────────────────────
  var bar = document.getElementById('progress-bar');
  function updateProgress() {
    var d = document.documentElement;
    bar.style.width = (d.scrollTop / (d.scrollHeight - d.clientHeight) * 100) + '%';
  }

  // ── Back-to-top visibility ──────────────────────────────────────────────────
  var btt = document.getElementById('back-top');
  function onScroll() {
    updateProgress();
    btt.classList.toggle('visible', window.scrollY > 300);
  }
  window.addEventListener('scroll', onScroll, { passive: true });

  // ── Scroll-spy: update active nav link using IntersectionObserver ───────────
  var sections = document.querySelectorAll('section[id]');
  var navLinks = document.querySelectorAll('.spa-link');
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        navLinks.forEach(function (a) { a.classList.remove('active'); });
        var active = document.querySelector('.spa-link[data-section="' + entry.target.id + '"]');
        if (active) active.classList.add('active');
      }
    });
  }, { threshold: 0.4 });
  sections.forEach(function (s) { observer.observe(s); });

  // ── FAQ accordion ───────────────────────────────────────────────────────────
  function toggleFaq(el) {
    var isOpen = el.classList.contains('open');
    document.querySelectorAll('.faq-item').forEach(function (f) { f.classList.remove('open'); });
    if (!isOpen) el.classList.add('open');
  }

  // ── Contact form submit ─────────────────────────────────────────────────────
  document.getElementById('contact-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var msg = document.getElementById('form-msg');
    var data = Object.fromEntries(new FormData(this));
    // Replace with your backend call:
    // frappe.call({ method: '__AP__.www.contact.submit', args: data, callback: r => { ... } });
    msg.style.display = 'block';
    msg.style.background = '#dcfce7'; msg.style.color = '#166534';
    msg.textContent = '✅ Message sent! We will be in touch within 24 hours.';
    this.reset();
  });
  </script>
</body>
</html>'''.replace('__CC__', cc).replace('__AP__', app)


def _www_tpl_saas(cc, app):
    """Full SaaS landing page — announcement bar, hero, features, pricing, testimonials, FAQ."""
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
  <style>
    :root {
      --brand:#5c4da8; --brand-dark:#3d2f8f; --brand-light:#ede9fe;
      --accent:#8b5cf6; --text-dark:#1e1b3a; --text-muted:#6b7280;
      --radius:10px; --shadow:0 4px 20px rgba(92,77,168,.12);
    }
    html { scroll-behavior: smooth; }
    body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:var(--text-dark); }
    /* ── Announcement bar ──────────────────────────────────────────────────── */
    .ann-bar {
      background:var(--brand);color:#fff;text-align:center;padding:8px 1rem;
      font-size:.82rem;font-weight:600;display:flex;align-items:center;justify-content:center;gap:8px;
    }
    .ann-bar a { color:#fff; text-decoration:underline; }
    .ann-close { background:none;border:none;color:rgba(255,255,255,.7);cursor:pointer;font-size:1rem;margin-left:auto;padding:0 8px; }
    /* ── Navbar ────────────────────────────────────────────────────────────── */
    .saas-nav {
      position:sticky;top:0;z-index:100;background:rgba(255,255,255,.95);
      backdrop-filter:blur(10px);border-bottom:1px solid #f0ebff;
      padding:.75rem 2rem;display:flex;align-items:center;gap:1rem;
    }
    .saas-brand { font-weight:800;font-size:1.15rem;color:var(--text-dark);text-decoration:none;margin-right:1.5rem; }
    .saas-nav-links { display:flex;gap:4px;flex:1; }
    .saas-nav-links a { padding:.4rem .8rem;border-radius:6px;font-size:.875rem;font-weight:500;color:var(--text-muted);text-decoration:none;transition:.15s; }
    .saas-nav-links a:hover { color:var(--brand);background:var(--brand-light); }
    .saas-nav-actions { display:flex;gap:8px;align-items:center; }
    .btn-ghost { padding:.4rem .9rem;background:none;border:none;color:var(--text-muted);font-weight:600;font-size:.875rem;cursor:pointer;border-radius:7px;transition:.15s;text-decoration:none; }
    .btn-ghost:hover { background:var(--brand-light);color:var(--brand); }
    .btn-solid { padding:.45rem 1.1rem;background:var(--brand);color:#fff;border:none;border-radius:8px;font-weight:700;font-size:.875rem;cursor:pointer;text-decoration:none;transition:.15s; }
    .btn-solid:hover { background:var(--brand-dark);color:#fff; }
    @media(max-width:640px){ .saas-nav-links,.saas-nav-actions .btn-ghost { display:none; } }
    /* ── Hero ──────────────────────────────────────────────────────────────── */
    .hero { padding:6rem 1rem 4rem;background:linear-gradient(160deg,#faf8ff 0%,#ede9fe 50%,#faf8ff 100%);text-align:center; }
    .hero h1 { font-size:clamp(2.4rem,6vw,4rem);font-weight:900;letter-spacing:-.04em;line-height:1.1;color:var(--text-dark);margin-bottom:1.25rem; }
    .hero h1 span { color:var(--brand); }
    .hero-sub { font-size:1.05rem;color:var(--text-muted);max-width:520px;margin:0 auto 2rem;line-height:1.7; }
    /* Email CTA form */
    .hero-form { display:flex;gap:8px;justify-content:center;flex-wrap:wrap;max-width:480px;margin:0 auto; }
    .hero-form input { flex:1;min-width:220px;padding:.7rem 1rem;border:1.5px solid #e5e2f0;border-radius:9px;font-size:.9rem;outline:none;transition:border-color .15s; }
    .hero-form input:focus { border-color:var(--brand); }
    .hero-form button { padding:.7rem 1.5rem;background:var(--brand);color:#fff;border:none;border-radius:9px;font-weight:700;font-size:.9rem;cursor:pointer;white-space:nowrap; }
    /* Product mockup placeholder */
    .mockup { margin:3rem auto 0;max-width:800px;background:#fff;border-radius:12px;box-shadow:0 20px 60px rgba(92,77,168,.2);border:1px solid #ede9fe;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center; }
    /* ── Logos strip ───────────────────────────────────────────────────────── */
    .logos-strip { padding:2.5rem 0;background:#fff;border-top:1px solid #f0ebff;border-bottom:1px solid #f0ebff; }
    .logos-strip .label { font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text-muted);text-align:center;margin-bottom:1.25rem; }
    .logos-row { display:flex;justify-content:center;align-items:center;gap:2.5rem;flex-wrap:wrap; }
    .logo-pill { padding:8px 20px;background:#f5f4fb;border-radius:8px;font-weight:700;font-size:.85rem;color:var(--text-muted); }
    /* ── Feature blocks ────────────────────────────────────────────────────── */
    .feat-block { padding:5rem 0;border-bottom:1px solid #f0ebff; }
    .feat-block:last-child { border-bottom:none; }
    .feat-tag { display:inline-block;background:var(--brand-light);color:var(--brand);font-size:.72rem;font-weight:700;padding:3px 10px;border-radius:20px;margin-bottom:.75rem; }
    .feat-title { font-size:1.9rem;font-weight:800;line-height:1.2;color:var(--text-dark);margin-bottom:1rem; }
    .feat-desc { font-size:.95rem;color:var(--text-muted);line-height:1.8;margin-bottom:1.25rem; }
    .feat-bullets { list-style:none;padding:0;margin:0; }
    .feat-bullets li { display:flex;gap:10px;align-items:flex-start;padding:5px 0;font-size:.9rem;color:var(--text-dark); }
    .feat-bullets li::before { content:'✓';color:var(--brand);font-weight:700;flex-shrink:0; }
    .feat-img { border-radius:14px;box-shadow:var(--shadow);background:var(--brand-light);aspect-ratio:4/3;display:flex;align-items:center;justify-content:center;font-size:4rem;opacity:.3; }
    /* ── Pricing ───────────────────────────────────────────────────────────── */
    .price-section { background:#f8f5ff;padding:5.5rem 0; }
    .price-card { background:#fff;border-radius:var(--radius);padding:28px 24px;box-shadow:var(--shadow);border:1px solid #f0ebff;text-align:center;height:100%; }
    .price-card.featured { background:var(--brand);color:#fff;border-color:var(--brand);transform:scale(1.04); }
    .price-card.featured .text-muted { color:rgba(255,255,255,.7) !important; }
    .price-amt { font-size:2.5rem;font-weight:900;line-height:1; }
    /* ── Testimonials ──────────────────────────────────────────────────────── */
    .testi-grid { display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px; }
    .testi-card { background:#fff;border-radius:var(--radius);padding:24px;box-shadow:var(--shadow);border:1px solid #f0ebff; }
    /* ── FAQ ───────────────────────────────────────────────────────────────── */
    .faq-item { border-bottom:1px solid #ede9fe;padding:16px 0; }
    .faq-q { font-weight:700;cursor:pointer;display:flex;justify-content:space-between;font-size:.92rem; }
    .faq-a { margin-top:10px;font-size:.88rem;color:var(--text-muted);line-height:1.7;display:none; }
    .faq-item.open .faq-a { display:block; }
    /* ── Final CTA ─────────────────────────────────────────────────────────── */
    .final-cta { background:linear-gradient(135deg,var(--brand),#6d28d9);color:#fff;padding:5rem 1rem;text-align:center; }
    .final-cta h2 { font-size:2.2rem;font-weight:800;margin-bottom:1rem; }
    /* ── Footer ────────────────────────────────────────────────────────────── */
    .saas-footer { background:var(--text-dark);color:rgba(255,255,255,.65);padding:3.5rem 0 0; }
    .footer-links { list-style:none;padding:0;margin:0; }
    .footer-links li { margin-bottom:.45rem; }
    .footer-links a { color:rgba(255,255,255,.6);text-decoration:none;font-size:.875rem; }
    .footer-links a:hover { color:#fff; }
    .footer-h { font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:rgba(255,255,255,.4);margin-bottom:.8rem; }
    .footer-bar { margin-top:2.5rem;padding:1.2rem 0;border-top:1px solid rgba(255,255,255,.08);font-size:.78rem;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px; }
    .eyebrow { font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--brand);margin-bottom:.5rem; }
    .sec-title { font-size:clamp(1.7rem,4vw,2.4rem);font-weight:800;line-height:1.15; }
  </style>
</head>
<body>

  <!-- Announcement bar -->
  <div class="ann-bar" id="ann-bar">
    <span>{{ announcement or "🎉 We just raised our Series A — read the blog post" }}
      <a href="{{ announcement_href or '/blog' }}">→</a>
    </span>
    <button class="ann-close" onclick="document.getElementById('ann-bar').style.display='none'" aria-label="Close">✕</button>
  </div>

  <!-- Sticky navbar -->
  <nav class="saas-nav" id="saas-nav">
    <a href="/" class="saas-brand">{{ site_name or "YourSaaS" }}</a>
    <div class="saas-nav-links">
      <a href="#features">Features</a><a href="#pricing">Pricing</a>
      <a href="/blog">Blog</a><a href="/docs">Docs</a>
    </div>
    <div class="saas-nav-actions">
      <a href="/login" class="btn-ghost">Log in</a>
      <a href="/register" class="btn-solid">Start Free →</a>
    </div>
  </nav>

  <!-- Hero -->
  <section class="hero" id="hero">
    <div class="container">
      <div style="display:inline-block;background:var(--brand-light);color:var(--brand);padding:4px 14px;border-radius:20px;font-size:.78rem;font-weight:700;margin-bottom:1.25rem">NEW · v2.0 Released</div>
      <h1>{{ hero_headline or title }}<br><span>without the complexity</span></h1>
      <p class="hero-sub">{{ hero_subtext or "Automate workflows, unify your data, and grow faster — without the headaches." }}</p>
      <form class="hero-form" onsubmit="handleEmailCapture(event)">
        <input type="email" name="email" placeholder="Enter your work email" required>
        <button type="submit">Get Started Free</button>
      </form>
      <p style="font-size:.78rem;color:var(--text-muted);margin-top:10px">No credit card required · 14-day free trial · Cancel anytime</p>
      <!-- Product mockup placeholder — replace with actual screenshot -->
      <div class="mockup">
        <div style="text-align:center;opacity:.25">
          <div style="font-size:3rem">🖥️</div>
          <div style="font-size:.9rem;margin-top:8px">Product screenshot goes here</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Trusted by logos -->
  <div class="logos-strip">
    <div class="container">
      <p class="label">Trusted by 500+ companies worldwide</p>
      <div class="logos-row">
        {% for logo in logos %}<div class="logo-pill">{{ logo }}</div>{% else %}
        <div class="logo-pill">Acme Corp</div><div class="logo-pill">GlobalTech</div>
        <div class="logo-pill">StartupXYZ</div><div class="logo-pill">MegaBrand</div>
        <div class="logo-pill">NextGen Co.</div>
        {% endfor %}
      </div>
    </div>
  </div>

  <!-- Feature blocks: alternating left/right -->
  <section id="features" style="padding:1rem 0">
    {% for blk in feature_blocks %}
    <div class="feat-block">
      <div class="container">
        <div class="row align-items-center g-5 {% if blk.side=='left' %}flex-row-reverse{% endif %}">
          <div class="col-lg-6">
            <span class="feat-tag">{{ blk.tag }}</span>
            <div class="feat-title">{{ blk.title }}</div>
            <p class="feat-desc">{{ blk.desc }}</p>
            <ul class="feat-bullets">{% for b in blk.bullets %}<li>{{ b }}</li>{% endfor %}</ul>
          </div>
          <div class="col-lg-6">
            <!-- Replace with screenshot: <img src="/assets/__AP__/images/{{ blk.tag|lower }}.png" class="img-fluid rounded-4"> -->
            <div class="feat-img"><span>{{ blk.icon }}</span></div>
          </div>
        </div>
      </div>
    </div>
    {% endfor %}
  </section>

  <!-- Pricing -->
  <section class="price-section" id="pricing">
    <div class="container">
      <div class="text-center mb-5">
        <p class="eyebrow">Pricing</p>
        <h2 class="sec-title">Start free, grow as you go</h2>
        <p style="color:var(--text-muted);margin-top:.75rem">All plans include a 14-day free trial. No credit card required.</p>
      </div>
      <div class="row g-4 justify-content-center align-items-center">
        {% for plan in plans %}
        <div class="col-md-4">
          <div class="price-card {% if plan.featured %}featured{% endif %}">
            {% if plan.featured %}<div style="display:inline-block;background:rgba(255,255,255,.2);color:#fff;font-size:.72rem;font-weight:700;padding:2px 10px;border-radius:12px;margin-bottom:8px">Most Popular</div>{% endif %}
            <h4 style="font-weight:800;margin-bottom:4px">{{ plan.name }}</h4>
            <div class="price-amt">{{ plan.price }}</div>
            <div class="text-muted" style="font-size:.83rem;margin-bottom:16px">{{ plan.period }}</div>
            <ul style="list-style:none;padding:0;margin:0 0 20px;text-align:left">
              {% for f in plan.features %}<li style="padding:5px 0;font-size:.88rem;display:flex;gap:8px"><span style="color:{% if plan.featured %}rgba(255,255,255,.8){% else %}var(--brand){% endif %}">✓</span>{{ f }}</li>{% endfor %}
            </ul>
            <a href="{{ plan.href }}" style="display:block;padding:.65rem;border-radius:8px;font-weight:700;text-decoration:none;text-align:center;{% if plan.featured %}background:#fff;color:var(--brand){% else %}background:var(--brand);color:#fff{% endif %}">{{ plan.cta }}</a>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- Testimonials -->
  <section style="padding:5.5rem 0;background:#fff" id="testimonials">
    <div class="container">
      <div class="text-center mb-5">
        <p class="eyebrow">Testimonials</p>
        <h2 class="sec-title">Don't take our word for it</h2>
      </div>
      <div class="testi-grid">
        {% for t in testimonials %}
        <div class="testi-card">
          <div style="color:#f59e0b;margin-bottom:8px">{{ '★' * (t.rating or 5) }}</div>
          <p style="font-size:.9rem;color:var(--text-muted);font-style:italic;line-height:1.7;margin-bottom:14px">"{{ t.text }}"</p>
          <div style="display:flex;gap:10px;align-items:center">
            <div style="width:36px;height:36px;border-radius:50%;background:var(--brand-light);color:var(--brand);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.78rem">{{ t.name[:2].upper() }}</div>
            <div><strong style="font-size:.85rem;color:var(--text-dark)">{{ t.name }}</strong><br><span style="font-size:.75rem;color:var(--text-muted)">{{ t.role }}</span></div>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- FAQ -->
  <section style="padding:5rem 0;background:#f8f5ff" id="faq">
    <div class="container" style="max-width:720px">
      <div class="text-center mb-5">
        <p class="eyebrow">FAQ</p>
        <h2 class="sec-title">Frequently asked questions</h2>
      </div>
      {% for item in faqs %}
      <div class="faq-item" onclick="this.classList.toggle('open')">
        <div class="faq-q"><span>{{ item.q }}</span><span style="font-size:.85rem;transition:transform .25s" class="faq-chev">▼</span></div>
        <div class="faq-a">{{ item.a }}</div>
      </div>
      {% endfor %}
    </div>
  </section>

  <!-- Final CTA -->
  <div class="final-cta">
    <div class="container" style="max-width:600px">
      <h2>Ready to get started?</h2>
      <p style="opacity:.8;margin-bottom:2rem">Join 500+ companies already building with {{ site_name or "our platform" }}.</p>
      <a href="/register" style="display:inline-block;padding:.85rem 2.4rem;background:#fff;color:var(--brand);font-weight:700;border-radius:var(--radius);text-decoration:none">Start Your Free Trial →</a>
    </div>
  </div>

  <!-- Footer -->
  <footer class="saas-footer">
    <div class="container">
      <div class="row g-4">
        <div class="col-lg-4">
          <div style="font-size:1.2rem;font-weight:800;color:#fff;margin-bottom:.6rem">{{ site_name or "YourSaaS" }}</div>
          <p style="font-size:.85rem;max-width:240px;line-height:1.65">{{ footer_tagline or "The smarter way to run your business." }}</p>
        </div>
        <div class="col-6 col-lg-2"><div class="footer-h">Product</div><ul class="footer-links"><li><a href="#features">Features</a></li><li><a href="#pricing">Pricing</a></li><li><a href="/changelog">Changelog</a></li></ul></div>
        <div class="col-6 col-lg-2"><div class="footer-h">Company</div><ul class="footer-links"><li><a href="/about">About</a></li><li><a href="/blog">Blog</a></li><li><a href="/contact">Contact</a></li></ul></div>
        <div class="col-6 col-lg-2"><div class="footer-h">Resources</div><ul class="footer-links"><li><a href="/docs">Docs</a></li><li><a href="/api">API</a></li><li><a href="/status">Status</a></li></ul></div>
        <div class="col-6 col-lg-2"><div class="footer-h">Legal</div><ul class="footer-links"><li><a href="/privacy">Privacy</a></li><li><a href="/terms">Terms</a></li></ul></div>
      </div>
      <div class="footer-bar">
        <span>© {{ frappe.utils.now_datetime().year }} {{ site_name or "YourSaaS" }}. All rights reserved.</span>
        <span>Built on Frappe Framework</span>
      </div>
    </div>
  </footer>

  <script>
  function handleEmailCapture(e) {
    e.preventDefault();
    var email = e.target.querySelector('input[type=email]').value;
    // Replace with your actual signup endpoint:
    // frappe.call({ method: '__AP__.www.register.capture_email', args: { email }, callback: r => { ... } });
    window.location.href = '/register?email=' + encodeURIComponent(email);
  }
  </script>
</body>
</html>'''.replace('__CC__', cc).replace('__AP__', app)


def _www_tpl_agency(cc, app):
    """Agency/portfolio website — fullscreen hero, filterable work grid, team, contact."""
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
  <style>
    :root {
      --brand:#5c4da8; --brand-light:#ede9fe; --accent:#8b5cf6;
      --text-dark:#1e1b3a; --text-muted:#6b7280; --radius:10px;
      --shadow:0 4px 20px rgba(92,77,168,.12);
    }
    html { scroll-behavior: smooth; }
    body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:var(--text-dark); }
    /* ── Nav ────────────────────────────────────────────────────────────────── */
    .ag-nav {
      position:fixed;top:0;left:0;right:0;z-index:100;
      padding:0 2.5rem;height:68px;display:flex;align-items:center;
      background:transparent;transition:background .25s,box-shadow .25s;
    }
    .ag-nav.scrolled { background:#fff;box-shadow:0 2px 12px rgba(0,0,0,.08); }
    .ag-brand { font-weight:800;font-size:1.2rem;color:#fff;text-decoration:none;flex:1; }
    .ag-nav.scrolled .ag-brand { color:var(--text-dark); }
    .ag-nav-links { display:flex;gap:4px; }
    .ag-nav-links a { padding:.4rem .85rem;border-radius:6px;font-size:.875rem;font-weight:500;color:rgba(255,255,255,.8);text-decoration:none;transition:.15s; }
    .ag-nav-links a:hover { color:#fff;background:rgba(255,255,255,.15); }
    .ag-nav.scrolled .ag-nav-links a { color:var(--text-muted); }
    .ag-nav.scrolled .ag-nav-links a:hover { color:var(--brand);background:var(--brand-light); }
    @media(max-width:640px){ .ag-nav-links { display:none; } }
    /* ── Hero ──────────────────────────────────────────────────────────────── */
    .ag-hero {
      min-height:100vh;display:flex;align-items:center;justify-content:center;
      background:linear-gradient(to bottom right,#0a0520,#1e1245 50%,#1a0a3a);
      text-align:center;padding:5rem 1.5rem;position:relative;overflow:hidden;
    }
    /* Subtle grain texture overlay via CSS */
    .ag-hero::before {
      content:'';position:absolute;inset:0;opacity:.35;
      background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='4' height='4'%3E%3Ccircle cx='2' cy='2' r='.6' fill='%23ffffff'/%3E%3C/svg%3E");
    }
    .ag-hero-inner { position:relative;z-index:1;max-width:780px;margin:0 auto; }
    .ag-eyebrow { display:inline-block;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);color:rgba(255,255,255,.8);padding:4px 14px;border-radius:20px;font-size:.78rem;font-weight:600;letter-spacing:.08em;margin-bottom:1.5rem; }
    .ag-hero h1 { font-size:clamp(2.8rem,7vw,5rem);font-weight:900;color:#fff;line-height:1.06;letter-spacing:-.04em;margin-bottom:1.5rem; }
    .ag-hero h1 .highlight { color:var(--accent); }
    .ag-hero p { font-size:1.05rem;color:rgba(255,255,255,.65);max-width:500px;margin:0 auto 2.5rem;line-height:1.75; }
    .ag-hero-btns { display:flex;gap:12px;justify-content:center;flex-wrap:wrap; }
    .btn-ag-primary { padding:.8rem 2.2rem;background:var(--brand);color:#fff;border-radius:var(--radius);font-weight:700;text-decoration:none;transition:transform .15s,box-shadow .15s; }
    .btn-ag-primary:hover { transform:translateY(-2px);box-shadow:0 8px 30px rgba(92,77,168,.5);color:#fff; }
    .btn-ag-outline { padding:.8rem 2.2rem;background:transparent;border:2px solid rgba(255,255,255,.3);color:#fff;border-radius:var(--radius);font-weight:700;text-decoration:none;transition:.15s; }
    .btn-ag-outline:hover { border-color:#fff;background:rgba(255,255,255,.08);color:#fff; }
    /* ── Stats band ────────────────────────────────────────────────────────── */
    .stats-band { background:var(--brand);color:#fff;padding:2rem 0; }
    .stat-item { text-align:center; }
    .stat-val { font-size:2.2rem;font-weight:900;line-height:1; }
    .stat-lbl { font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;opacity:.75;margin-top:4px; }
    /* ── Work grid ─────────────────────────────────────────────────────────── */
    .work-section { padding:5.5rem 0;background:#fff; }
    .work-filters { display:flex;gap:8px;flex-wrap:wrap;margin-bottom:2rem;justify-content:center; }
    .work-filter { padding:.4rem 1rem;border-radius:20px;border:1.5px solid #e5e2f0;background:#fff;color:var(--text-muted);font-size:.82rem;font-weight:600;cursor:pointer;transition:.15s; }
    .work-filter.active,.work-filter:hover { background:var(--brand);color:#fff;border-color:var(--brand); }
    /* Work card */
    .work-card { border-radius:12px;overflow:hidden;position:relative;aspect-ratio:4/3;background:var(--brand-light);cursor:pointer; }
    .work-card .work-img { width:100%;height:100%;object-fit:cover;transition:transform .35s; }
    .work-card .work-overlay {
      position:absolute;inset:0;background:rgba(30,27,58,.85);
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      opacity:0;transition:opacity .25s;padding:20px;text-align:center;
    }
    .work-card:hover .work-overlay { opacity:1; }
    .work-card:hover .work-img { transform:scale(1.06); }
    .work-cat { font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--accent);margin-bottom:8px; }
    .work-title { font-size:1.1rem;font-weight:800;color:#fff;margin-bottom:12px; }
    .work-cta { padding:.45rem 1.2rem;background:var(--brand);color:#fff;border-radius:7px;font-size:.82rem;font-weight:700;text-decoration:none;transition:background .15s; }
    .work-cta:hover { background:var(--accent);color:#fff; }
    /* ── Services ───────────────────────────────────────────────────────────── */
    .services-section { padding:5.5rem 0;background:#f8f5ff; }
    .service-card { background:#fff;border-radius:var(--radius);padding:28px 24px;box-shadow:var(--shadow);border:1px solid #f0ebff;height:100%;transition:transform .2s; }
    .service-card:hover { transform:translateY(-3px); }
    .service-ico { font-size:2.2rem;margin-bottom:14px; }
    /* ── Team ───────────────────────────────────────────────────────────────── */
    .team-section { padding:5.5rem 0;background:#fff; }
    .team-card { text-align:center; }
    .team-av { width:80px;height:80px;border-radius:50%;background:var(--brand-light);color:var(--brand);font-size:1.4rem;font-weight:800;display:flex;align-items:center;justify-content:center;margin:0 auto 14px; }
    /* ── Contact ────────────────────────────────────────────────────────────── */
    .contact-section { padding:5.5rem 0;background:#f8f5ff; }
    .form-inp { width:100%;padding:10px 14px;border:1.5px solid #e5e2f0;border-radius:8px;font-size:.875rem;font-family:inherit;outline:none;transition:border-color .15s; }
    .form-inp:focus { border-color:var(--brand); }
    /* ── Footer ─────────────────────────────────────────────────────────────── */
    .ag-footer { background:var(--text-dark);color:rgba(255,255,255,.6);text-align:center;padding:2.5rem 1rem; }
    .ag-footer a { color:rgba(255,255,255,.6);text-decoration:none; }
    .ag-footer a:hover { color:#fff; }
    .eyebrow { font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--brand);margin-bottom:.6rem; }
    .sec-title { font-size:clamp(1.7rem,4vw,2.4rem);font-weight:800;line-height:1.15; }
  </style>
</head>
<body>

  <!-- Nav -->
  <nav class="ag-nav" id="ag-nav">
    <a href="/" class="ag-brand">{{ site_name or "Studio" }}</a>
    <div class="ag-nav-links">
      <a href="#work">Work</a><a href="#services">Services</a>
      <a href="#team">Team</a><a href="#contact">Contact</a>
    </div>
  </nav>

  <!-- Hero -->
  <section class="ag-hero" id="hero">
    <div class="ag-hero-inner">
      <div class="ag-eyebrow">Creative Agency · Est. 2016</div>
      <h1>{{ hero_tagline or "We craft digital experiences" }}<br><span class="highlight">that move people</span></h1>
      <p>{{ hero_sub or "Strategy, design, and development — from concept to launch, we build what makes brands grow." }}</p>
      <div class="ag-hero-btns">
        <a href="#work" class="btn-ag-primary">View Our Work</a>
        <a href="#contact" class="btn-ag-outline">Start a Project</a>
      </div>
    </div>
  </section>

  <!-- Stats band -->
  <div class="stats-band">
    <div class="container">
      <div class="row g-3">
        {% for s in stats %}
        <div class="col-6 col-md-3"><div class="stat-item"><div class="stat-val">{{ s.value }}</div><div class="stat-lbl">{{ s.label }}</div></div></div>
        {% else %}
        <div class="col-6 col-md-3"><div class="stat-item"><div class="stat-val">120+</div><div class="stat-lbl">Projects</div></div></div>
        <div class="col-6 col-md-3"><div class="stat-item"><div class="stat-val">8</div><div class="stat-lbl">Years</div></div></div>
        <div class="col-6 col-md-3"><div class="stat-item"><div class="stat-val">40+</div><div class="stat-lbl">Clients</div></div></div>
        <div class="col-6 col-md-3"><div class="stat-item"><div class="stat-val">12</div><div class="stat-lbl">Awards</div></div></div>
        {% endfor %}
      </div>
    </div>
  </div>

  <!-- Work Grid -->
  <section class="work-section" id="work">
    <div class="container">
      <div class="text-center mb-4">
        <p class="eyebrow">Portfolio</p>
        <h2 class="sec-title">Selected work</h2>
      </div>
      <!-- Filter buttons — JS filters by data-cat -->
      <div class="work-filters">
        <button class="work-filter active" data-cat="all">All</button>
        <button class="work-filter" data-cat="Branding">Branding</button>
        <button class="work-filter" data-cat="E-Commerce">E-Commerce</button>
        <button class="work-filter" data-cat="Web App">Web App</button>
        <button class="work-filter" data-cat="Mobile">Mobile</button>
        <button class="work-filter" data-cat="Dashboard">Dashboard</button>
      </div>
      <div class="row g-4" id="work-grid">
        {% for proj in projects %}
        <div class="col-md-6 col-lg-4 work-item" data-cat="{{ proj.category }}">
          <div class="work-card">
            <!-- Replace bg with: <img src="/assets/__AP__/images/work-{{ loop.index }}.jpg" class="work-img" alt="{{ proj.title }}"> -->
            <div class="work-img" style="background:{{ proj.color }};opacity:.35"></div>
            <div class="work-overlay">
              <div class="work-cat">{{ proj.category }}</div>
              <div class="work-title">{{ proj.title }}</div>
              <p style="font-size:.82rem;color:rgba(255,255,255,.7);margin-bottom:14px">{{ proj.desc }}</p>
              <a href="#" class="work-cta">View Project</a>
            </div>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- Services -->
  <section class="services-section" id="services">
    <div class="container">
      <div class="text-center mb-5">
        <p class="eyebrow">What We Do</p>
        <h2 class="sec-title">Our services</h2>
      </div>
      <div class="row g-4">
        {% for svc in services %}
        <div class="col-md-6 col-lg-3">
          <div class="service-card">
            <div class="service-ico">{{ svc.icon }}</div>
            <h5 style="font-weight:800;color:var(--text-dark);margin-bottom:10px">{{ svc.title }}</h5>
            <p style="font-size:.875rem;color:var(--text-muted);line-height:1.65;margin:0">{{ svc.desc }}</p>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- Team -->
  <section class="team-section" id="team">
    <div class="container">
      <div class="text-center mb-5">
        <p class="eyebrow">The Team</p>
        <h2 class="sec-title">Meet the people behind the work</h2>
      </div>
      <div class="row g-4 justify-content-center">
        {% for member in team %}
        <div class="col-6 col-md-3">
          <div class="team-card">
            <!-- Replace with <img src="..."> -->
            <div class="team-av">{{ member.avatar }}</div>
            <strong style="color:var(--text-dark)">{{ member.name }}</strong>
            <div style="font-size:.83rem;color:var(--text-muted);margin-top:4px">{{ member.role }}</div>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- Contact -->
  <section class="contact-section" id="contact">
    <div class="container">
      <div class="row g-5 align-items-start justify-content-center">
        <div class="col-lg-5">
          <p class="eyebrow">Get In Touch</p>
          <h2 class="sec-title" style="margin-bottom:1rem">Start a project with us</h2>
          <p style="color:var(--text-muted);line-height:1.75;margin-bottom:1.5rem">Have a project in mind? Fill in the form and we'll get back to you within 24 hours.</p>
          <div style="display:flex;flex-direction:column;gap:12px">
            <div style="display:flex;gap:10px;align-items:center"><span style="font-size:1.2rem">📧</span><span style="font-size:.9rem;color:var(--text-muted)">hello@yourstudio.com</span></div>
            <div style="display:flex;gap:10px;align-items:center"><span style="font-size:1.2rem">📞</span><span style="font-size:.9rem;color:var(--text-muted)">+1 (555) 000-0000</span></div>
            <div style="display:flex;gap:10px;align-items:center"><span style="font-size:1.2rem">📍</span><span style="font-size:.9rem;color:var(--text-muted)">Mumbai, India · Remote-first</span></div>
          </div>
        </div>
        <div class="col-lg-6">
          <div style="background:#fff;border-radius:var(--radius);padding:32px;box-shadow:var(--shadow)">
            <form id="agency-form">
              <div class="row g-3">
                <div class="col-md-6"><input class="form-inp" type="text" name="name" placeholder="Your Name *" required></div>
                <div class="col-md-6"><input class="form-inp" type="email" name="email" placeholder="Email Address *" required></div>
                <div class="col-12"><input class="form-inp" type="text" name="company" placeholder="Company / Brand"></div>
                <div class="col-12">
                  <select class="form-inp" name="service">
                    <option value="">— Select service —</option>
                    <option>Brand Identity</option><option>Web Development</option>
                    <option>Mobile App</option><option>Digital Strategy</option>
                  </select>
                </div>
                <div class="col-12"><input class="form-inp" type="text" name="budget" placeholder="Estimated Budget (optional)"></div>
                <div class="col-12"><textarea class="form-inp" name="message" rows="4" placeholder="Tell us about your project *" required style="resize:vertical"></textarea></div>
                <div class="col-12"><button type="submit" style="width:100%;padding:.8rem;background:var(--brand);color:#fff;border:none;border-radius:8px;font-weight:700;font-size:.95rem;cursor:pointer">Send Message →</button></div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="ag-footer">
    <div style="font-weight:800;font-size:1.1rem;color:#fff;margin-bottom:12px">{{ site_name or "Studio" }}</div>
    <div style="display:flex;justify-content:center;gap:16px;margin-bottom:16px;font-size:.85rem;flex-wrap:wrap">
      <a href="#work">Work</a><a href="#services">Services</a><a href="#team">Team</a>
      <a href="/privacy">Privacy</a><a href="/terms">Terms</a>
    </div>
    <div style="font-size:.78rem">© {{ frappe.utils.now_datetime().year }} {{ site_name or "Your Studio" }}. All rights reserved.</div>
  </footer>

  <script>
  // ── Navbar scroll effect ─────────────────────────────────────────────────────
  var nav = document.getElementById('ag-nav');
  window.addEventListener('scroll', function () { nav.classList.toggle('scrolled', window.scrollY > 60); }, { passive:true });

  // ── Work grid filter ─────────────────────────────────────────────────────────
  document.querySelectorAll('.work-filter').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.work-filter').forEach(function (b) { b.classList.remove('active'); });
      this.classList.add('active');
      var cat = this.dataset.cat;
      document.querySelectorAll('.work-item').forEach(function (item) {
        item.style.display = (cat === 'all' || item.dataset.cat === cat) ? '' : 'none';
      });
    });
  });

  // ── Contact form ─────────────────────────────────────────────────────────────
  document.getElementById('agency-form').addEventListener('submit', function (e) {
    e.preventDefault();
    // frappe.call({ method: '__AP__.www.contact.submit', args: Object.fromEntries(new FormData(this)), callback: r => { ... } });
    alert('Thank you! We\'ll be in touch within 24 hours.');
    this.reset();
  });
  </script>
</body>
</html>'''.replace('__CC__', cc).replace('__AP__', app)


def _www_tpl_docs(cc, app):
    """Documentation with 3-panel layout: sidebar nav tree + article + TOC."""
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
  <style>
    :root {
      --brand:#5c4da8; --brand-light:#ede9fe; --accent:#8b5cf6;
      --text-dark:#1e1b3a; --text-muted:#6b7280; --radius:8px;
      --sidebar-w:256px; --toc-w:220px; --header-h:56px;
    }
    html { scroll-behavior: smooth; }
    body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:var(--text-dark); background:#fff; }
    /* ── TOP HEADER BAR ────────────────────────────────────────────────────── */
    .docs-header {
      position:sticky;top:0;z-index:200;height:var(--header-h);
      background:#fff;border-bottom:1px solid #ede9fe;
      display:flex;align-items:center;padding:0 1.5rem;gap:12px;
    }
    .docs-brand { font-weight:800;font-size:1.05rem;color:var(--text-dark);text-decoration:none;margin-right:8px; }
    .docs-header-links { display:flex;gap:2px; }
    .docs-header-links a { padding:.35rem .75rem;border-radius:6px;font-size:.83rem;font-weight:500;color:var(--text-muted);text-decoration:none;transition:.15s; }
    .docs-header-links a:hover { color:var(--brand);background:var(--brand-light); }
    .docs-header-links a.active { color:var(--brand);font-weight:700; }
    /* Header search */
    .docs-search {
      margin-left:auto;display:flex;align-items:center;gap:6px;
      background:#f5f4fb;border:1px solid #ede9fe;border-radius:7px;padding:5px 10px;
      transition:border-color .15s;
    }
    .docs-search:focus-within { border-color:var(--brand);background:#fff; }
    .docs-search input { border:none;background:transparent;outline:none;font-size:.83rem;width:200px;color:var(--text-dark); }
    .docs-ham { display:none;background:none;border:none;cursor:pointer;padding:6px;font-size:1.1rem;color:var(--text-muted); }
    @media(max-width:768px) {
      .docs-header-links { display:none; }
      .docs-ham { display:block; }
      .docs-search input { width:120px; }
    }
    /* ── MAIN LAYOUT ───────────────────────────────────────────────────────── */
    .docs-layout {
      display:grid;
      grid-template-columns:var(--sidebar-w) 1fr var(--toc-w);
      min-height:calc(100vh - var(--header-h));
      max-width:1280px;margin:0 auto;
    }
    @media(max-width:1100px) { .docs-layout { grid-template-columns:var(--sidebar-w) 1fr; } .docs-toc-col { display:none; } }
    @media(max-width:768px) { .docs-layout { grid-template-columns:1fr; } }
    /* ── LEFT SIDEBAR ──────────────────────────────────────────────────────── */
    .docs-sidebar {
      border-right:1px solid #ede9fe;padding:20px 0;
      position:sticky;top:var(--header-h);height:calc(100vh - var(--header-h));
      overflow-y:auto;
    }
    .docs-sidebar::-webkit-scrollbar { width:4px; }
    .docs-sidebar::-webkit-scrollbar-thumb { background:#e5e2f0;border-radius:2px; }
    /* Sidebar search */
    .sidebar-search {
      margin:0 12px 16px;display:flex;align-items:center;gap:6px;
      background:#f5f4fb;border:1px solid #ede9fe;border-radius:7px;padding:6px 10px;
    }
    .sidebar-search input { border:none;background:transparent;outline:none;font-size:.82rem;width:100%;color:var(--text-dark); }
    /* Sidebar nav sections */
    .sidebar-section { margin-bottom:4px; }
    .sidebar-section-hdr {
      font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;
      color:var(--text-muted);padding:8px 16px 4px;cursor:pointer;
      display:flex;justify-content:space-between;align-items:center;
    }
    .sidebar-links { list-style:none;padding:0 8px;margin:0; }
    .sidebar-links li a {
      display:block;padding:6px 10px;border-radius:6px;font-size:.84rem;font-weight:500;
      color:var(--text-muted);text-decoration:none;transition:.12s;
    }
    .sidebar-links li a:hover { color:var(--brand);background:var(--brand-light); }
    .sidebar-links li a.active {
      color:var(--brand);background:var(--brand-light);font-weight:700;
      border-left:3px solid var(--brand);
    }
    /* Mobile sidebar */
    @media(max-width:768px) {
      .docs-sidebar {
        position:fixed;top:0;bottom:0;left:0;z-index:300;
        background:#fff;transform:translateX(-100%);transition:transform .25s;
        padding-top:calc(var(--header-h) + 16px);
      }
      .docs-sidebar.open { transform:translateX(0); }
    }
    .sidebar-overlay {
      display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:299;
    }
    /* ── ARTICLE AREA ──────────────────────────────────────────────────────── */
    .docs-article { padding:2rem 2.5rem;max-width:720px; }
    @media(max-width:768px) { .docs-article { padding:1.5rem 1rem; } }
    /* Breadcrumb */
    .docs-bc { display:flex;align-items:center;gap:6px;font-size:.78rem;color:var(--text-muted);margin-bottom:1.5rem;flex-wrap:wrap; }
    .docs-bc a { color:var(--brand);text-decoration:none; }
    .docs-bc a:hover { text-decoration:underline; }
    .docs-bc-sep { opacity:.4; }
    /* Article meta */
    .article-meta { display:flex;gap:16px;font-size:.78rem;color:var(--text-muted);margin-bottom:2rem;padding-bottom:1.25rem;border-bottom:1px solid #f0ebff;flex-wrap:wrap; }
    /* Typography */
    .docs-article h1 { font-size:1.9rem;font-weight:900;color:var(--text-dark);margin-bottom:.75rem; }
    .docs-article h2 { font-size:1.3rem;font-weight:800;color:var(--text-dark);margin-top:2.5rem;margin-bottom:.75rem;padding-top:.5rem;border-top:1px solid #f0ebff; }
    .docs-article h3 { font-size:1.05rem;font-weight:700;color:var(--text-dark);margin-top:1.75rem;margin-bottom:.5rem; }
    .docs-article p { font-size:.93rem;line-height:1.8;color:#374151;margin-bottom:1rem; }
    .docs-article ul, .docs-article ol { font-size:.93rem;line-height:1.8;color:#374151;margin-bottom:1rem;padding-left:1.4rem; }
    .docs-article li { margin-bottom:.35rem; }
    .docs-article a { color:var(--brand);text-decoration:none; }
    .docs-article a:hover { text-decoration:underline; }
    /* Code blocks */
    .docs-article code {
      background:#f5f3ff;color:var(--brand);font-size:.84em;
      padding:2px 6px;border-radius:4px;font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace;
    }
    .docs-article pre {
      background:#1e1b3a;border-radius:var(--radius);padding:18px 20px;
      overflow-x:auto;margin:1.25rem 0;position:relative;
    }
    .docs-article pre code { background:transparent;color:#e4e0ff;font-size:.85rem;padding:0; }
    /* Copy button hint */
    .docs-article pre::after {
      content:'⧉ copy';position:absolute;top:8px;right:10px;
      font-size:.7rem;color:rgba(255,255,255,.3);cursor:pointer;font-family:inherit;
    }
    /* Callout boxes */
    .callout { border-radius:var(--radius);padding:14px 18px;margin:1.25rem 0;font-size:.88rem;line-height:1.7;border-left:4px solid; }
    .callout.info    { background:#ede9fe;border-color:var(--brand);color:#3d2f8f; }
    .callout.warning { background:#fef3c7;border-color:#b45309;color:#78350f; }
    .callout.danger  { background:#fee2e2;border-color:#dc2626;color:#7f1d1d; }
    .callout.success { background:#dcfce7;border-color:#059669;color:#064e3b; }
    .callout strong  { display:block;margin-bottom:4px; }
    /* Prev/Next nav */
    .prev-next { display:flex;gap:12px;margin-top:3rem;padding-top:1.5rem;border-top:1px solid #f0ebff;flex-wrap:wrap; }
    .pn-card {
      flex:1;min-width:180px;padding:14px 18px;border-radius:var(--radius);border:1.5px solid #ede9fe;
      text-decoration:none;color:var(--text-dark);transition:border-color .15s,background .15s;
    }
    .pn-card:hover { border-color:var(--brand);background:var(--brand-light); }
    .pn-label { font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--text-muted);margin-bottom:4px; }
    .pn-title { font-size:.9rem;font-weight:700;color:var(--text-dark); }
    /* ── TABLE OF CONTENTS ─────────────────────────────────────────────────── */
    .docs-toc-col { padding:2rem 1rem 2rem 0; }
    .docs-toc {
      position:sticky;top:calc(var(--header-h) + 1rem);
      padding:0 0 0 1rem;border-left:1px solid #ede9fe;
    }
    .toc-label { font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text-muted);margin-bottom:.75rem; }
    .toc-links { list-style:none;padding:0;margin:0; }
    .toc-links li a {
      display:block;padding:4px 8px;font-size:.82rem;color:var(--text-muted);text-decoration:none;
      border-radius:5px;transition:.12s;border-left:2px solid transparent;margin-bottom:2px;
    }
    .toc-links li a:hover { color:var(--brand); }
    .toc-links li a.active { color:var(--brand);font-weight:600;border-left-color:var(--brand); }
  </style>
</head>
<body>

  <!-- ════════════════════════════════════ DOCS TOP HEADER ══ -->
  <header class="docs-header">
    <button class="docs-ham" id="docs-ham" onclick="toggleDocsSidebar()">☰</button>
    <a href="/" class="docs-brand">{{ site_name or "Docs" }}</a>
    <div class="docs-header-links">
      <a href="/docs" class="active">Documentation</a>
      <a href="/api">API Reference</a>
      <a href="/guides">Guides</a>
      <a href="/changelog">Changelog</a>
    </div>
    <div class="docs-search">
      <span style="color:var(--text-muted);font-size:.85rem">🔍</span>
      <input type="search" placeholder="Search docs… (Ctrl+K)" id="docs-search-input" aria-label="Search documentation">
    </div>
  </header>

  <div class="docs-layout">

    <!-- ══════════════════════════════ LEFT SIDEBAR ══ -->
    <aside class="docs-sidebar" id="docs-sidebar">
      <div class="sidebar-search">
        <span style="color:var(--text-muted);font-size:.82rem">🔍</span>
        <input type="search" placeholder="Filter…" id="sidebar-filter" oninput="filterSidebar(this.value)" aria-label="Filter sidebar">
      </div>

      <!-- Navigation sections — from doc_sections in get_context() -->
      {% for section in doc_sections %}
      <div class="sidebar-section">
        <div class="sidebar-section-hdr">
          <span>{{ section.heading }}</span>
        </div>
        <ul class="sidebar-links">
          {% for lnk in section.links %}
          <li><a href="{{ lnk.href }}" class="{% if lnk.active %}active{% endif %}">{{ lnk.label }}</a></li>
          {% endfor %}
        </ul>
      </div>
      {% endfor %}
    </aside>
    <div class="sidebar-overlay" id="sidebar-ov" onclick="toggleDocsSidebar()"></div>

    <!-- ══════════════════════════════ ARTICLE ══ -->
    <article class="docs-article">
      <!-- Breadcrumb -->
      <nav class="docs-bc" aria-label="Breadcrumb">
        {% for bc in article_breadcrumbs %}
        {% if bc.href %}<a href="{{ bc.href }}">{{ bc.label }}</a><span class="docs-bc-sep">/</span>
        {% else %}<span style="color:var(--text-dark);font-weight:600">{{ bc.label }}</span>
        {% endif %}
        {% else %}
        <a href="/">Home</a><span class="docs-bc-sep">/</span>
        <a href="/docs">Docs</a><span class="docs-bc-sep">/</span>
        <span style="color:var(--text-dark);font-weight:600">{{ title }}</span>
        {% endfor %}
      </nav>

      <h1>{{ article_title or title }}</h1>

      <!-- Article meta -->
      <div class="article-meta">
        <span>📅 Updated {{ article_last_updated or "recently" }}</span>
        <span>⏱ {{ article_read_time or "5" }} min read</span>
        <span style="margin-left:auto"><a href="#" style="color:var(--brand);font-size:.78rem">✏️ Edit this page</a></span>
      </div>

      <!-- ══ ARTICLE CONTENT ══════════════════════════════════════════════════ -->
      <!-- Replace the sections below with your actual documentation content    -->

      <h2 id="overview">Overview</h2>
      <p>
        This is the documentation page for <strong>{{ article_title or title }}</strong>.
        Replace the content below with your actual documentation. You have access to all Jinja2
        template features and the full context from <code>get_context()</code>.
      </p>

      <div class="callout info">
        <strong>ℹ️ Info</strong>
        Use these callout boxes to highlight important information. Available types:
        <code>info</code>, <code>warning</code>, <code>danger</code>, <code>success</code>.
      </div>

      <h2 id="prerequisites">Prerequisites</h2>
      <p>Before you begin, make sure you have the following installed:</p>
      <ul>
        <li>Python 3.10+</li>
        <li>Node.js 18+ and npm</li>
        <li>Frappe Framework v15+</li>
        <li>MariaDB 10.6+</li>
      </ul>

      <h2 id="installation">Installation</h2>
      <p>Install via bench:</p>

      <pre><code>bench get-app https://github.com/your-org/your-app
bench --site yoursite.localhost install-app your_app
bench migrate</code></pre>

      <div class="callout warning">
        <strong>⚠️ Warning</strong>
        Always run <code>bench migrate</code> after installing a new app or after pulling updates that include schema changes.
      </div>

      <h2 id="configuration">Configuration</h2>
      <p>After installation, configure the app in <strong>Settings &gt; App Settings</strong>:</p>

      <pre><code># site_config.json
{
  "db_name": "your_database",
  "your_app_api_key": "your_key_here",
  "debug": 0
}</code></pre>

      <h2 id="first-steps">Your First Steps</h2>
      <p>Once installed, navigate to <strong>Home &gt; Your App</strong> in the Frappe desk to get started.</p>

      <div class="callout success">
        <strong>✅ You're all set!</strong>
        The app is now installed and ready to use. Check the next section for a complete walkthrough.
      </div>

      <h2 id="whats-next">What's Next</h2>
      <p>Explore more topics:</p>
      <ul>
        {% for item in toc %}
        <li><a href="#{{ item.id }}">{{ item.label }}</a></li>
        {% endfor %}
      </ul>

      <!-- ══ PREV / NEXT NAVIGATION ══════════════════════════════════════════ -->
      <div class="prev-next">
        {% if prev_article.label %}
        <a href="{{ prev_article.href }}" class="pn-card" style="text-align:left">
          <div class="pn-label">← Previous</div>
          <div class="pn-title">{{ prev_article.label }}</div>
        </a>
        {% endif %}
        {% if next_article.label %}
        <a href="{{ next_article.href }}" class="pn-card" style="text-align:right;margin-left:auto">
          <div class="pn-label">Next →</div>
          <div class="pn-title">{{ next_article.label }}</div>
        </a>
        {% endif %}
      </div>
    </article>

    <!-- ═══════════════════════════ TABLE OF CONTENTS ══ -->
    <div class="docs-toc-col">
      <div class="docs-toc">
        <div class="toc-label">On this page</div>
        <ul class="toc-links" id="toc-links">
          {% for item in toc %}
          <li><a href="#{{ item.id }}" data-target="{{ item.id }}">{{ item.label }}</a></li>
          {% else %}
          <li><a href="#overview">Overview</a></li>
          <li><a href="#prerequisites">Prerequisites</a></li>
          <li><a href="#installation">Installation</a></li>
          <li><a href="#configuration">Configuration</a></li>
          <li><a href="#first-steps">First Steps</a></li>
          <li><a href="#whats-next">What's Next</a></li>
          {% endfor %}
        </ul>
      </div>
    </div>

  </div><!-- /.docs-layout -->

  <script>
  // ── Mobile sidebar toggle ────────────────────────────────────────────────────
  function toggleDocsSidebar() {
    document.getElementById('docs-sidebar').classList.toggle('open');
    document.getElementById('sidebar-ov').style.display =
      document.getElementById('docs-sidebar').classList.contains('open') ? 'block' : 'none';
  }

  // ── Sidebar link filter ──────────────────────────────────────────────────────
  function filterSidebar(q) {
    q = q.toLowerCase();
    document.querySelectorAll('.sidebar-links li').forEach(function (li) {
      li.style.display = li.querySelector('a').textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  }

  // ── TOC scroll spy (IntersectionObserver) ────────────────────────────────────
  var tocLinks = document.querySelectorAll('#toc-links a');
  var headings = document.querySelectorAll('.docs-article h2[id], .docs-article h3[id]');
  if (headings.length && tocLinks.length) {
    var tocObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          tocLinks.forEach(function (a) { a.classList.remove('active'); });
          var active = document.querySelector('#toc-links a[href="#' + entry.target.id + '"]');
          if (active) active.classList.add('active');
        }
      });
    }, { rootMargin: '-10% 0px -80% 0px' });
    headings.forEach(function (h) { tocObserver.observe(h); });
  }

  // ── Keyboard shortcut Ctrl+K focuses search ──────────────────────────────────
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      document.getElementById('docs-search-input').focus();
    }
    if (e.key === 'Escape') {
      document.getElementById('docs-sidebar').classList.remove('open');
      document.getElementById('sidebar-ov').style.display = 'none';
    }
  });

  // ── Code block copy (click pre::after pseudo-element region) ─────────────────
  document.querySelectorAll('pre').forEach(function (pre) {
    pre.style.cursor = 'pointer';
    pre.title = 'Click to copy code';
    pre.addEventListener('click', function () {
      navigator.clipboard && navigator.clipboard.writeText(pre.querySelector('code').innerText)
        .then(function () {
          pre.style.outline = '2px solid var(--brand)';
          setTimeout(function () { pre.style.outline = ''; }, 1000);
        });
    });
  });
  </script>
</body>
</html>'''.replace('__CC__', cc).replace('__AP__', app)


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
def create_desk_page(app, module, page_name, title, preset='blank'):
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
    py_body = _desk_py_template(fn_name, tpl_path, app, module, page_name, preset)
    with open(os.path.join(page_dir, page_name + ".py"), "w") as f:
        f.write(py_body)

    # .js
    method_path = f"{app}.{rel_from_root.replace('/', '.')}.{fn_name}.get_{fn_name}"
    js_body = _desk_js_template(page_name, title, method_path, app, preset)
    with open(os.path.join(page_dir, page_name + ".js"), "w") as f:
        f.write(js_body)

    # .html (minimal page-level wrapper)
    with open(os.path.join(page_dir, page_name + ".html"), "w") as f:
        f.write(f"<!-- Frappe page wrapper for {title} -->\n")

    # templates/{page_name}.html
    tpl_body = _desk_tpl_template(page_name, title, preset)
    with open(os.path.join(tpl_dir, page_name + ".html"), "w") as f:
        f.write(tpl_body)

    return {
        "created": True,
        "path": os.path.relpath(page_dir, root).replace("\\", "/"),
        "page_name": page_name,
    }


def _desk_js_template(page_name, title, method_path, app, preset='blank'):
    """Return rich commented JS boilerplate for a desk page."""
    fn = page_name.replace("-", "_")
    # Presets that need full-width single column (they handle their own layout)
    single_col = 'true' if preset in ('app_shell_sidebar', 'split_explorer', 'adv_dashboard') else 'false'
    preset_note = {
        'app_shell_sidebar': '// Preset: App Shell + Sidebar — the template contains a full fixed-height sidebar layout.\n// The Python backend renders the .html template into page.main.\n',
        'split_explorer':    '// Preset: Split Explorer — left list pane + right detail pane.\n// Populate the list by passing records from the Python context (see template comments).\n',
        'adv_dashboard':     '// Preset: Advanced Dashboard — KPIs + Chart.js charts + activity feed.\n// Chart.js is loaded from CDN automatically. Replace sample data with real frappe.call() data.\n',
    }.get(preset, '')
    return f'''{preset_note}// ── {title} — Desk Page ──────────────────────────────────────────────────────
// Frappe Desk Page lifecycle:
//   on_page_load   — fires once when the page DOM is created
//   on_page_show   — fires every time the page becomes visible (tab switch / refresh)
//   on_page_hide   — fires when leaving this page
//   on_page_unload — fires when the page is destroyed

frappe.pages["{page_name}"].on_page_load = function(wrapper) {{
\t// ── Create the page shell ────────────────────────────────────────────────
\tvar page = frappe.ui.make_app_page({{
\t\tparent:    wrapper,
\t\ttitle:     "{title}",
\t\tsingle_column: {single_col},   // true = full-width (sidebar/dashboard presets)
\t}});

\t// ── Store page reference for use in other handlers ────────────────────────
\twrapper.page_obj = page;

\t// ── Add action buttons to the page header ────────────────────────────────
\t// page.set_primary_action("New Item", () => frappe.new_doc("Item"), "add");
\t// page.add_menu_item("Export CSV", () => {{  }});
\t// page.add_inner_button("Refresh", () => load_data());

\t// ── Add filter / search controls to the page toolbar ─────────────────────
\t// var $company = page.add_field({{
\t//   label: "Company", fieldtype: "Link", options: "Company",
\t//   change() {{ load_data(); }}
\t// }});
\t// var $from = page.add_field({{ label: "From", fieldtype: "Date", change() {{ load_data(); }} }});
\t// var $to   = page.add_field({{ label: "To",   fieldtype: "Date", change() {{ load_data(); }} }});

\t// ── Load initial data ─────────────────────────────────────────────────────
\tload_data();

\t// ── load_data: calls the Python backend and renders the template ──────────
\tfunction load_data() {{
\t\tpage.set_indicator("Loading…", "blue");

\t\tfrappe.call({{
\t\t\tmethod: "{method_path}",
\t\t\targs: {{
\t\t\t\t// company: $company.get_value(),
\t\t\t\t// from_date: $from.get_value(),
\t\t\t}},
\t\t\tcallback: function(r) {{
\t\t\t\tif (!r.message) {{ page.set_indicator("Error", "red"); return; }}
\t\t\t\t$(page.main).html(r.message);
\t\t\t\tbind_events(page);
\t\t\t\tpage.clear_indicator();
\t\t\t}},
\t\t\terror: function() {{ page.set_indicator("Failed", "red"); }}
\t\t}});
\t}}
}};

frappe.pages["{page_name}"].on_page_show = function(wrapper) {{
\t// Re-render or refresh data every time the user switches to this page
\t// wrapper.page_obj && load_data();
}};

// ── bind_events: wire up interactive elements after HTML is injected ──────────
function bind_events(page) {{
\t// Example: handle row clicks in a table
\t// $(page.main).find(".data-row").on("click", function() {{
\t//   frappe.set_route("Form", "Item", $(this).data("name"));
\t// }});

\t// Example: handle a button click
\t// $(page.main).find("#my-btn").on("click", function() {{
\t//   frappe.call({{ method: "{app}.api.module.do_something", callback: r => load_data() }});
\t// }});

\t// Example: initialise a Chart.js chart
\t// var ctx = $(page.main).find("#my-chart")[0].getContext("2d");
\t// new Chart(ctx, {{ type: "bar", data: {{ ... }}, options: {{ ... }} }});

\t// Example: real-time via frappe.realtime
\t// frappe.realtime.on("update_event", (data) => load_data());
}}
'''


def _desk_py_template(fn_name, tpl_path, app, module, page_name, preset='blank'):
    """Return rich commented Python boilerplate for a desk page."""
    return f'''import frappe
from frappe import _


@frappe.whitelist()
def get_{fn_name}(**kwargs):
    """
    Backend handler for the {page_name} desk page.
    Called by frappe.call() in the .js file.
    Returns rendered HTML that is injected into page.main.

    Parameters passed from JS via args: {{ ... }} are received as **kwargs.

    Common patterns — uncomment as needed:
    ──────────────────────────────────────────────────────────────────────────

    # ── Check permission ────────────────────────────────────────────────────
    # frappe.only_for("System Manager")   # restrict to one role
    # if not frappe.has_permission("Sales Invoice", "read"):
    #     frappe.throw(_("Not permitted"), frappe.PermissionError)

    # ── Read filter args from the JS call ───────────────────────────────────
    # company   = kwargs.get("company")   or frappe.defaults.get_global_default("company")
    # from_date = kwargs.get("from_date") or frappe.utils.add_months(frappe.utils.today(), -1)
    # to_date   = kwargs.get("to_date")   or frappe.utils.today()

    # ── Query the database ───────────────────────────────────────────────────
    # records = frappe.get_all(
    #     "Sales Invoice",
    #     filters={{"company": company, "docstatus": 1}},
    #     fields=["name", "customer", "grand_total", "posting_date", "status"],
    #     order_by="posting_date desc",
    #     limit=100,
    # )

    # ── Aggregate / summarise with SQL ───────────────────────────────────────
    # totals = frappe.db.sql("""
    #     SELECT
    #         SUM(grand_total) AS total_sales,
    #         COUNT(*) AS invoice_count,
    #         customer
    #     FROM `tabSales Invoice`
    #     WHERE docstatus = 1
    #       AND company = %(company)s
    #     GROUP BY customer
    #     ORDER BY total_sales DESC
    #     LIMIT 10
    # """, {{"company": company}}, as_dict=1)

    # ── Compute KPI cards ────────────────────────────────────────────────────
    # kpis = [
    #     {{"label": "Open Orders", "value": frappe.db.count("Sales Order", {{"status": "To Deliver and Bill"}}), "color": "#5c4da8"}},
    #     {{"label": "Unpaid Invoices", "value": frappe.db.count("Sales Invoice", {{"outstanding_amount": [">", 0]}}),"color": "#dc2626"}},
    # ]

    # ── Render a Jinja2 template ─────────────────────────────────────────────
    # html = frappe.render_template("{tpl_path}", {{
    #     "records": records,
    #     "totals": totals,
    #     "kpis": kpis,
    # }})
    # return html
    """
    context = {{
        "title": "{page_name.replace("-", " ").replace("_", " ").title()}",
        # "records": [],
    }}
    html = frappe.render_template("{tpl_path}", context)
    return html
'''


# ─────────────────────────────────────────────────────────────────────────────
# Desk page preset template helpers
# ─────────────────────────────────────────────────────────────────────────────

def _desk_tpl_app_shell(cc, title):
    """App Shell + Sidebar — fixed sidebar, top header, tabbed content area."""
    return r'''
<!-- ══ APP SHELL + SIDEBAR DESK PRESET ═════════════════════════════════════
     Tabs: frappe.ui renders .nav-tabs / .tab-content inside page.main.
     CSS vars in :root are scoped to this page so they don't bleed.
     The sidebar toggle button collapses/expands the sidebar at 240px.
════════════════════════════════════════════════════════════════════════════ -->
<style>
  :root {
    --sh-brand:     #5c4da8;
    --sh-sidebar-w: 240px;
    --sh-header-h:  48px;
    --sh-bg:        #f7f5fc;
    --sh-sidebar-bg:#2a2050;
    --sh-text:      #1e1b3a;
    --sh-muted:     #6b7280;
    --sh-radius:    8px;
    --sh-shadow:    0 2px 12px rgba(92,77,168,.12);
  }
  .sh-shell {
    display: flex; height: 100%; background: var(--sh-bg);
    overflow: hidden; position: relative;
  }
  /* ── Sidebar ── */
  .sh-sidebar {
    width: var(--sh-sidebar-w); background: var(--sh-sidebar-bg); color: #e2d9f3;
    display: flex; flex-direction: column; flex-shrink: 0;
    transition: width .25s ease; overflow: hidden;
  }
  .sh-sidebar.collapsed { width: 52px; }
  .sh-sidebar-logo {
    padding: 14px 16px; font-weight: 800; font-size: 15px; color: #fff;
    border-bottom: 1px solid rgba(255,255,255,.08); white-space: nowrap;
    display: flex; align-items: center; gap: 10px;
  }
  .sh-nav { flex: 1; overflow-y: auto; padding: 10px 0; }
  .sh-nav-item {
    display: flex; align-items: center; gap: 10px; padding: 10px 16px;
    cursor: pointer; white-space: nowrap; font-size: 13px;
    border-left: 3px solid transparent; transition: background .15s, border-color .15s;
  }
  .sh-nav-item:hover { background: rgba(255,255,255,.07); }
  .sh-nav-item.active { background: rgba(255,255,255,.13); border-color: #a78bfa; color: #fff; }
  .sh-nav-item .sh-ico { font-size: 16px; flex-shrink: 0; }
  .sh-nav-label { opacity: 1; transition: opacity .2s; }
  .sh-sidebar.collapsed .sh-nav-label { opacity: 0; pointer-events: none; }
  .sh-nav-group { font-size: 10px; text-transform: uppercase; letter-spacing: .1em;
    color: rgba(255,255,255,.35); padding: 14px 18px 4px; white-space: nowrap; }
  .sh-sidebar.collapsed .sh-nav-group { opacity: 0; }
  .sh-sidebar-footer { padding: 12px 14px; border-top: 1px solid rgba(255,255,255,.08); }
  /* ── Main area ── */
  .sh-main { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }
  .sh-header {
    height: var(--sh-header-h); background: #fff; border-bottom: 1px solid #e8e0f8;
    display: flex; align-items: center; gap: 12px; padding: 0 20px; flex-shrink: 0;
    box-shadow: 0 1px 4px rgba(92,77,168,.06);
  }
  .sh-toggle-btn {
    width: 32px; height: 32px; border: 1px solid #e8e0f8; border-radius: 6px;
    background: #fff; cursor: pointer; display: flex; align-items: center;
    justify-content: center; font-size: 16px; color: var(--sh-brand);
  }
  .sh-toggle-btn:hover { background: var(--sh-bg); }
  .sh-breadcrumb { font-size: 12px; color: var(--sh-muted); flex: 1; }
  .sh-breadcrumb span { color: var(--sh-text); font-weight: 600; }
  .sh-header-search {
    display: flex; align-items: center; gap: 6px; background: var(--sh-bg);
    border: 1px solid #e8e0f8; border-radius: 20px; padding: 4px 14px;
    font-size: 12px; color: var(--sh-muted); cursor: text; width: 200px;
  }
  .sh-avatar {
    width: 32px; height: 32px; border-radius: 50%; background: var(--sh-brand);
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 13px; cursor: pointer; flex-shrink: 0;
  }
  .sh-content { flex: 1; overflow-y: auto; padding: 20px; }
  /* ── Tabs ── */
  .sh-tabs { display: flex; gap: 0; border-bottom: 2px solid #e8e0f8; margin-bottom: 20px; }
  .sh-tab {
    padding: 9px 18px; font-size: 13px; font-weight: 600; color: var(--sh-muted);
    cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px;
    transition: color .15s, border-color .15s;
  }
  .sh-tab:hover { color: var(--sh-brand); }
  .sh-tab.active { color: var(--sh-brand); border-color: var(--sh-brand); }
  .sh-panel { display: none; }
  .sh-panel.active { display: block; }
  /* ── Cards ── */
  .sh-kpi-row { display: grid; grid-template-columns: repeat(auto-fill,minmax(180px,1fr)); gap: 14px; margin-bottom: 20px; }
  .sh-kpi-card {
    background: #fff; border-radius: var(--sh-radius); box-shadow: var(--sh-shadow);
    padding: 18px 20px; border-left: 4px solid var(--sh-brand);
  }
  .sh-kpi-val { font-size: 1.9rem; font-weight: 900; color: var(--sh-brand); }
  .sh-kpi-lbl { font-size: 11px; text-transform: uppercase; letter-spacing: .07em; color: var(--sh-muted); }
  .sh-card {
    background: #fff; border-radius: var(--sh-radius); box-shadow: var(--sh-shadow);
    padding: 20px; margin-bottom: 16px;
  }
  .sh-card-title { font-weight: 700; font-size: 14px; color: var(--sh-text); margin-bottom: 14px; }
  /* ── Table ── */
  .sh-tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
  .sh-tbl th { background: #f0eaff; color: var(--sh-brand); padding: 9px 14px;
    text-align: left; font-weight: 700; border-bottom: 2px solid #e0d4fc; }
  .sh-tbl td { padding: 8px 14px; border-bottom: 1px solid #f3f0fc; }
  .sh-tbl tr:hover td { background: #faf7ff; cursor: pointer; }
  .sh-badge { display:inline-block; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:700; }
  .sh-badge-green { background:#dcfce7; color:#14532d; }
  .sh-badge-blue  { background:#dbeafe; color:#1e3a5f; }
  .sh-badge-red   { background:#fee2e2; color:#7f1d1d; }
</style>

<div class="sh-shell" id="sh-shell">
  <!-- ── Sidebar ── -->
  <div class="sh-sidebar" id="sh-sidebar">
    <div class="sh-sidebar-logo">
      <span>⬡</span>
      <span class="sh-nav-label">''' + title + r'''</span>
    </div>
    <div class="sh-nav">
      <div class="sh-nav-group">Main</div>
      <div class="sh-nav-item active" data-panel="dashboard" onclick="shNav(this,'dashboard')">
        <span class="sh-ico">📊</span><span class="sh-nav-label">Dashboard</span>
      </div>
      <div class="sh-nav-item" data-panel="records" onclick="shNav(this,'records')">
        <span class="sh-ico">📋</span><span class="sh-nav-label">Records</span>
      </div>
      <div class="sh-nav-item" data-panel="analytics" onclick="shNav(this,'analytics')">
        <span class="sh-ico">📈</span><span class="sh-nav-label">Analytics</span>
      </div>
      <div class="sh-nav-group">Settings</div>
      <div class="sh-nav-item" data-panel="settings" onclick="shNav(this,'settings')">
        <span class="sh-ico">⚙️</span><span class="sh-nav-label">Settings</span>
      </div>
    </div>
    <div class="sh-sidebar-footer">
      <div class="sh-nav-item" style="padding-left:0">
        <span class="sh-ico">👤</span>
        <span class="sh-nav-label" style="font-size:12px">{{ frappe.session.user }}</span>
      </div>
    </div>
  </div>

  <!-- ── Main area ── -->
  <div class="sh-main">
    <div class="sh-header">
      <button class="sh-toggle-btn" onclick="shToggle()" title="Toggle sidebar">☰</button>
      <div class="sh-breadcrumb">Home / <span id="sh-bc-label">Dashboard</span></div>
      <div class="sh-header-search">🔍 Search…</div>
      <div class="sh-avatar" title="{{ frappe.session.user }}">
        {{ frappe.session.user[:1].upper() }}
      </div>
    </div>
    <div class="sh-content">
      <!-- ── Dashboard panel ── -->
      <div class="sh-panel active" id="sh-panel-dashboard">
        <div class="sh-kpi-row">
          <div class="sh-kpi-card"><div class="sh-kpi-val" id="kpi1">—</div><div class="sh-kpi-lbl">Open Orders</div></div>
          <div class="sh-kpi-card" style="border-color:#0891b2"><div class="sh-kpi-val" style="color:#0891b2" id="kpi2">—</div><div class="sh-kpi-lbl">Revenue (MTD)</div></div>
          <div class="sh-kpi-card" style="border-color:#16a34a"><div class="sh-kpi-val" style="color:#16a34a" id="kpi3">—</div><div class="sh-kpi-lbl">Customers</div></div>
          <div class="sh-kpi-card" style="border-color:#dc2626"><div class="sh-kpi-val" style="color:#dc2626" id="kpi4">—</div><div class="sh-kpi-lbl">Pending Tasks</div></div>
        </div>
        <div style="display:grid;grid-template-columns:2fr 1fr;gap:16px">
          <div class="sh-card">
            <div class="sh-card-title">Recent Activity</div>
            <!-- Activity feed — populate from Python context -->
            <div style="color:#9080b8;font-size:13px;text-align:center;padding:20px">
              No recent activity.<br><em style="font-size:11px">Pass <code>activity</code> list from Python context.</em>
            </div>
          </div>
          <div class="sh-card">
            <div class="sh-card-title">Quick Actions</div>
            <div style="display:flex;flex-direction:column;gap:8px">
              <button class="btn btn-primary btn-sm" onclick="frappe.new_doc('Sales Order')">＋ New Order</button>
              <button class="btn btn-default btn-sm" onclick="frappe.set_route('List','Customer')">View Customers</button>
              <button class="btn btn-default btn-sm" onclick="frappe.set_route('query-report','Sales Analytics')">Run Report</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Records panel ── -->
      <div class="sh-panel" id="sh-panel-records">
        <div class="sh-tabs">
          <div class="sh-tab active" onclick="shTab(this,'tab-all')">All Records</div>
          <div class="sh-tab" onclick="shTab(this,'tab-open')">Open</div>
          <div class="sh-tab" onclick="shTab(this,'tab-closed')">Closed</div>
        </div>
        <div id="sh-tab-all" class="sh-card">
          <div style="overflow-x:auto">
            <table class="sh-tbl">
              <thead><tr><th>#</th><th>Name</th><th>Date</th><th>Amount</th><th>Status</th></tr></thead>
              <tbody id="sh-records-body">
                <tr><td colspan="5" style="text-align:center;padding:30px;color:#9080b8">
                  Load records from Python → pass <code>records</code> list in context.</td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <div id="sh-tab-open"   style="display:none" class="sh-card"><p style="color:#9080b8">Filter <code>records</code> by status in Python or JS.</p></div>
        <div id="sh-tab-closed" style="display:none" class="sh-card"><p style="color:#9080b8">Filter <code>records</code> by status in Python or JS.</p></div>
      </div>

      <!-- ── Analytics panel ── -->
      <div class="sh-panel" id="sh-panel-analytics">
        <div class="sh-card">
          <div class="sh-card-title">Analytics</div>
          <p style="color:#9080b8;font-size:13px">
            Add <a href="https://www.chartjs.org/" target="_blank">Chart.js</a> or Frappe Charts here.<br>
            Load the script in your .js file and call <code>new Chart(ctx, config)</code>.
          </p>
        </div>
      </div>

      <!-- ── Settings panel ── -->
      <div class="sh-panel" id="sh-panel-settings">
        <div class="sh-card">
          <div class="sh-card-title">Settings</div>
          <p style="color:#9080b8;font-size:13px">Add frappe.ui.form fields or custom settings UI here.</p>
        </div>
      </div>
    </div><!-- /sh-content -->
  </div><!-- /sh-main -->
</div><!-- /sh-shell -->

<script>
/* ── Sidebar toggle ── */
function shToggle() {
  document.getElementById('sh-sidebar').classList.toggle('collapsed');
}

/* ── Sidebar nav ── */
function shNav(el, panel) {
  document.querySelectorAll('.sh-nav-item').forEach(i => i.classList.remove('active'));
  document.querySelectorAll('.sh-panel').forEach(p => p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('sh-panel-' + panel).classList.add('active');
  const label = el.querySelector('.sh-nav-label');
  if (label) document.getElementById('sh-bc-label').textContent = label.textContent;
}

/* ── Inner tab switching (Records panel) ── */
function shTab(el, tabId) {
  el.closest('.sh-tabs').querySelectorAll('.sh-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  ['sh-tab-all','sh-tab-open','sh-tab-closed'].forEach(id => {
    const el2 = document.getElementById(id);
    if (el2) el2.style.display = (id === tabId) ? '' : 'none';
  });
}

/* ── KPI example — replace with real frappe.call() ── */
// document.addEventListener('DOMContentLoaded', () => {
//   frappe.call({ method: 'your_app.api.module.get_kpis', callback: r => {
//     document.getElementById('kpi1').textContent = r.message.open_orders;
//     document.getElementById('kpi2').textContent = '₹' + r.message.revenue;
//   }});
// });
</script>
'''


def _desk_tpl_split_explorer(cc, title):
    """Split Explorer — filterable list left, detail view right."""
    return r'''
<!-- ══ SPLIT EXPLORER DESK PRESET ══════════════════════════════════════════
     Left pane: searchable/filterable list of records.
     Right pane: detail view with tabs for different data sections.
     The splitter bar can be dragged to resize panes.
════════════════════════════════════════════════════════════════════════════ -->
<style>
  .spx-wrap {
    display: flex; height: 100%; overflow: hidden; font-family: inherit;
    background: #f7f5fc;
  }
  /* ── Left pane ── */
  .spx-left {
    width: 300px; min-width: 200px; max-width: 50%;
    display: flex; flex-direction: column; background: #fff;
    border-right: 1px solid #e8e0f8; flex-shrink: 0; overflow: hidden;
  }
  .spx-left-hdr {
    padding: 12px 14px; background: #f0eaff; border-bottom: 1px solid #e0d4fc;
    font-weight: 700; font-size: 13px; color: #3a2e5e; flex-shrink: 0;
  }
  .spx-search {
    padding: 8px 12px; flex-shrink: 0; border-bottom: 1px solid #eee;
  }
  .spx-search input {
    width: 100%; border: 1px solid #e0d4fc; border-radius: 6px;
    padding: 6px 10px; font-size: 12px; outline: none; background: #faf8ff;
  }
  .spx-search input:focus { border-color: #a78bfa; box-shadow: 0 0 0 2px rgba(167,139,250,.15); }
  .spx-filter-row {
    display: flex; gap: 6px; padding: 6px 12px; flex-wrap: wrap;
    border-bottom: 1px solid #eee; flex-shrink: 0;
  }
  .spx-filter-chip {
    padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600;
    cursor: pointer; background: #f0eaff; color: #5c4da8; border: 1px solid #d4bcfc;
    white-space: nowrap;
  }
  .spx-filter-chip.active { background: #5c4da8; color: #fff; border-color: #5c4da8; }
  .spx-list { flex: 1; overflow-y: auto; }
  .spx-item {
    padding: 11px 14px; border-bottom: 1px solid #f3f0fc; cursor: pointer;
    transition: background .12s;
  }
  .spx-item:hover { background: #faf7ff; }
  .spx-item.active { background: #ede9fe; border-left: 3px solid #7c3aed; padding-left: 11px; }
  .spx-item-name { font-weight: 600; font-size: 13px; color: #1e1b3a; }
  .spx-item-meta { font-size: 11px; color: #9080b8; margin-top: 2px; }
  .spx-badge { display:inline-block;padding:1px 8px;border-radius:12px;font-size:10px;font-weight:700;margin-left:6px; }
  /* ── Splitter ── */
  .spx-splitter {
    width: 5px; background: #e8e0f8; cursor: col-resize; flex-shrink: 0;
    transition: background .15s;
  }
  .spx-splitter:hover, .spx-splitter.dragging { background: #7c3aed; }
  /* ── Right pane ── */
  .spx-right { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
  .spx-right-hdr {
    padding: 14px 20px; background: #fff; border-bottom: 1px solid #e8e0f8;
    display: flex; align-items: center; gap: 12px; flex-shrink: 0;
  }
  .spx-right-title { font-weight: 700; font-size: 15px; color: #1e1b3a; flex: 1; }
  .spx-empty {
    flex: 1; display: flex; flex-direction: column; align-items: center;
    justify-content: center; color: #b0a8d0; gap: 12px;
  }
  .spx-empty-ico { font-size: 3rem; }
  .spx-detail { flex: 1; overflow-y: auto; padding: 20px; display: none; }
  .spx-tabs { display:flex;border-bottom:2px solid #e8e0f8;background:#fff;flex-shrink:0;padding:0 20px; }
  .spx-tab { padding:9px 16px;font-size:12px;font-weight:600;color:#9080b8;cursor:pointer;
    border-bottom:2px solid transparent;margin-bottom:-2px;transition:color .15s,border-color .15s; }
  .spx-tab:hover { color:#5c4da8; }
  .spx-tab.active { color:#5c4da8;border-color:#5c4da8; }
  .spx-tab-panel { display:none; }
  .spx-tab-panel.active { display:block; }
  .spx-field-row { display:flex;gap:8px;margin-bottom:12px;align-items:baseline; }
  .spx-field-lbl { font-size:11px;font-weight:700;color:#9080b8;text-transform:uppercase;
    letter-spacing:.06em;min-width:120px;flex-shrink:0; }
  .spx-field-val { font-size:13px;color:#1e1b3a; }
  .spx-section-title { font-weight:700;font-size:13px;color:#3a2e5e;margin:16px 0 8px;
    border-bottom:1px solid #f0eaff;padding-bottom:6px; }
  .spx-card { background:#fff;border-radius:8px;box-shadow:0 2px 12px rgba(92,77,168,.08);
    padding:18px;margin-bottom:14px; }
</style>

<div class="spx-wrap" id="spx-wrap">
  <!-- ── Left list pane ── -->
  <div class="spx-left" id="spx-left">
    <div class="spx-left-hdr">''' + title + r''' <span id="spx-count" style="font-weight:400;font-size:11px;margin-left:6px;color:#9080b8"></span></div>
    <div class="spx-search">
      <input type="text" id="spx-search" placeholder="Search…" oninput="spxFilter()">
    </div>
    <div class="spx-filter-row">
      <div class="spx-filter-chip active" data-filter="all" onclick="spxSetFilter(this,'all')">All</div>
      <div class="spx-filter-chip" data-filter="open"   onclick="spxSetFilter(this,'open')">Open</div>
      <div class="spx-filter-chip" data-filter="closed" onclick="spxSetFilter(this,'closed')">Closed</div>
    </div>
    <div class="spx-list" id="spx-list">
      <div style="padding:30px;text-align:center;color:#b0a8d0;font-size:13px">
        Load items from Python context → pass <code>records</code> list.
      </div>
    </div>
  </div>

  <!-- ── Drag splitter ── -->
  <div class="spx-splitter" id="spx-splitter"></div>

  <!-- ── Right detail pane ── -->
  <div class="spx-right" id="spx-right">
    <div class="spx-empty" id="spx-empty">
      <div class="spx-empty-ico">☚</div>
      <div>Select a record from the list</div>
    </div>
    <div id="spx-detail-wrap" style="display:none;flex:1;display:none;flex-direction:column;overflow:hidden">
      <div class="spx-right-hdr">
        <div class="spx-right-title" id="spx-detail-title">—</div>
        <button class="btn btn-default btn-sm" onclick="spxClose()">✕ Close</button>
        <button class="btn btn-primary btn-sm" id="spx-open-btn">Open Form →</button>
      </div>
      <div class="spx-tabs">
        <div class="spx-tab active" onclick="spxDetailTab(this,'overview')">Overview</div>
        <div class="spx-tab" onclick="spxDetailTab(this,'details')">Details</div>
        <div class="spx-tab" onclick="spxDetailTab(this,'history')">History</div>
      </div>
      <div class="spx-detail">
        <!-- Overview tab -->
        <div class="spx-tab-panel active" id="spxtab-overview">
          <div class="spx-card">
            <div class="spx-section-title">Summary</div>
            <div class="spx-field-row"><span class="spx-field-lbl">Name</span><span class="spx-field-val" id="spx-f-name">—</span></div>
            <div class="spx-field-row"><span class="spx-field-lbl">Status</span><span class="spx-field-val" id="spx-f-status">—</span></div>
            <div class="spx-field-row"><span class="spx-field-lbl">Date</span><span class="spx-field-val" id="spx-f-date">—</span></div>
            <div class="spx-field-row"><span class="spx-field-lbl">Amount</span><span class="spx-field-val" id="spx-f-amount">—</span></div>
          </div>
        </div>
        <!-- Details tab -->
        <div class="spx-tab-panel" id="spxtab-details">
          <div class="spx-card"><p style="color:#9080b8;font-size:13px">
            Fetch full document via <code>frappe.call → frappe.get_doc</code> and render fields here.
          </p></div>
        </div>
        <!-- History tab -->
        <div class="spx-tab-panel" id="spxtab-history">
          <div class="spx-card"><p style="color:#9080b8;font-size:13px">
            Load document timeline via <code>frappe.get_list("Comment", {"reference_doctype": doctype, "reference_name": name})</code>.
          </p></div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
/* ── Splitter drag-resize ── */
(function() {
  var sp = document.getElementById('spx-splitter');
  var lp = document.getElementById('spx-left');
  var dragging = false, startX = 0, startW = 0;
  sp.addEventListener('mousedown', function(e) {
    dragging = true; startX = e.clientX; startW = lp.offsetWidth;
    sp.classList.add('dragging');
    document.body.style.cursor = 'col-resize'; e.preventDefault();
  });
  document.addEventListener('mousemove', function(e) {
    if (!dragging) return;
    var newW = Math.max(180, Math.min(startW + (e.clientX - startX), window.innerWidth * .5));
    lp.style.width = newW + 'px';
  });
  document.addEventListener('mouseup', function() {
    if (!dragging) return;
    dragging = false; sp.classList.remove('dragging');
    document.body.style.cursor = '';
  });
})();

/* ── Active filter ── */
var _spxFilter = 'all';
function spxSetFilter(el, f) {
  document.querySelectorAll('.spx-filter-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  _spxFilter = f;
  spxFilter();
}

/* ── Filter + search ── */
function spxFilter() {
  var q = (document.getElementById('spx-search').value || '').toLowerCase();
  var items = document.querySelectorAll('.spx-item');
  var visible = 0;
  items.forEach(function(item) {
    var text  = item.textContent.toLowerCase();
    var status = (item.dataset.status || '').toLowerCase();
    var matchQ = !q || text.includes(q);
    var matchF = _spxFilter === 'all' || status === _spxFilter;
    item.style.display = (matchQ && matchF) ? '' : 'none';
    if (matchQ && matchF) visible++;
  });
  var cnt = document.getElementById('spx-count');
  if (cnt) cnt.textContent = '(' + visible + ')';
}

/* ── Open detail view ── */
function spxOpen(name, title, status, date, amount, doctype) {
  document.querySelectorAll('.spx-item').forEach(i => i.classList.remove('active'));
  var el = document.querySelector('.spx-item[data-name="' + name + '"]');
  if (el) el.classList.add('active');
  document.getElementById('spx-detail-title').textContent = title || name;
  document.getElementById('spx-f-name').textContent   = name   || '—';
  document.getElementById('spx-f-status').textContent = status || '—';
  document.getElementById('spx-f-date').textContent   = date   || '—';
  document.getElementById('spx-f-amount').textContent = amount || '—';
  document.getElementById('spx-open-btn').onclick = function() {
    frappe.set_route('Form', doctype || 'DocType', name);
  };
  document.getElementById('spx-empty').style.display = 'none';
  var dw = document.getElementById('spx-detail-wrap');
  dw.style.display = 'flex'; dw.style.flexDirection = 'column';
  dw.querySelector('.spx-detail').style.display = 'block';
}

function spxClose() {
  document.getElementById('spx-empty').style.display = 'flex';
  document.getElementById('spx-detail-wrap').style.display = 'none';
  document.querySelectorAll('.spx-item').forEach(i => i.classList.remove('active'));
}

/* ── Detail tabs ── */
function spxDetailTab(el, tab) {
  el.closest('.spx-tabs').querySelectorAll('.spx-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.spx-tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('spxtab-' + tab).classList.add('active');
}

/* ── Example: populate list from Jinja context ──
   In Python, pass:  context["records"] = frappe.get_all("Sales Order", fields=["name","status","transaction_date","grand_total"], limit=200)
   Then in template, before </script>:

   {% for r in records %}
   (function(){
     var li = document.createElement('div');
     li.className = 'spx-item';
     li.dataset.name   = {{ r.name | tojson }};
     li.dataset.status = {{ (r.status or '') | lower | tojson }};
     li.innerHTML = '<div class="spx-item-name">' + frappe.utils.escape_html({{ r.name | tojson }}) + '</div>'
       + '<div class="spx-item-meta">{{ r.transaction_date }} · ₹{{ r.grand_total }}</div>';
     li.onclick = function() {
       spxOpen({{ r.name | tojson }}, {{ r.name | tojson }}, {{ r.status | tojson }},
               {{ r.transaction_date | tojson }}, '₹{{ r.grand_total }}', 'Sales Order');
     };
     document.getElementById('spx-list').appendChild(li);
   })();
   {% endfor %}
   spxFilter(); // update count
── */
</script>
'''


def _desk_tpl_adv_dashboard(cc, title):
    """Advanced Dashboard — Chart.js area chart, KPI row, activity feed, quick actions."""
    return r'''
<!-- ══ ADVANCED DASHBOARD DESK PRESET ══════════════════════════════════════
     Sections:
       1. KPI row with trend indicators
       2. Chart.js area/line chart + pie/doughnut chart side-by-side
       3. Activity feed (timeline)
       4. Quick-action cards at the bottom
     CDN: Chart.js 4.4 loaded dynamically when the page opens.
════════════════════════════════════════════════════════════════════════════ -->
<style>
  .adv-dash { padding: 0 4px; font-family: inherit; }
  :root {
    --ad-brand:  #5c4da8;
    --ad-accent: #8b5cf6;
    --ad-bg:     #f7f5fc;
    --ad-card:   #fff;
    --ad-border: #e8e0f8;
    --ad-muted:  #9080b8;
    --ad-text:   #1e1b3a;
    --ad-radius: 10px;
    --ad-shadow: 0 2px 12px rgba(92,77,168,.1);
  }
  /* ── KPI row ── */
  .ad-kpi-row { display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px;margin-bottom:20px; }
  .ad-kpi {
    background:var(--ad-card);border-radius:var(--ad-radius);box-shadow:var(--ad-shadow);
    padding:18px 20px;border-left:4px solid var(--ad-brand);
    display:flex;align-items:center;gap:16px;
  }
  .ad-kpi-ico { font-size:2rem; }
  .ad-kpi-val { font-size:1.9rem;font-weight:900;color:var(--ad-brand); }
  .ad-kpi-lbl { font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--ad-muted); }
  .ad-kpi-trend { font-size:11px;font-weight:700;padding:2px 7px;border-radius:12px;margin-top:3px;display:inline-block; }
  .trend-up   { background:#dcfce7;color:#16a34a; }
  .trend-down { background:#fee2e2;color:#dc2626; }
  .trend-flat { background:#f3f4f6;color:#6b7280; }
  /* ── Chart area ── */
  .ad-charts { display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:20px; }
  @media(max-width:900px){ .ad-charts { grid-template-columns:1fr; } }
  .ad-card {
    background:var(--ad-card);border-radius:var(--ad-radius);box-shadow:var(--ad-shadow);padding:20px;
  }
  .ad-card-hdr { display:flex;align-items:center;gap:10px;margin-bottom:16px; }
  .ad-card-title { font-weight:700;font-size:14px;color:var(--ad-text);flex:1; }
  .ad-card-badge { font-size:11px;padding:3px 10px;border-radius:12px;background:#ede9fe;color:var(--ad-brand);font-weight:600; }
  /* ── Bottom row ── */
  .ad-bottom { display:grid;grid-template-columns:1fr 1fr;gap:16px; }
  @media(max-width:800px){ .ad-bottom { grid-template-columns:1fr; } }
  /* ── Activity feed ── */
  .ad-feed { list-style:none;padding:0;margin:0; }
  .ad-feed li {
    display:flex;gap:12px;align-items:flex-start;padding:10px 0;
    border-bottom:1px solid var(--ad-border);font-size:12.5px;
  }
  .ad-feed li:last-child { border:none; }
  .ad-feed-dot { width:8px;height:8px;border-radius:50%;background:var(--ad-accent);margin-top:4px;flex-shrink:0; }
  .ad-feed-text { flex:1;color:var(--ad-text); }
  .ad-feed-time { font-size:11px;color:var(--ad-muted);white-space:nowrap; }
  /* ── Quick actions ── */
  .ad-actions { display:flex;flex-direction:column;gap:8px; }
  .ad-action-btn {
    display:flex;align-items:center;gap:10px;padding:12px 16px;
    background:#fff;border:1px solid var(--ad-border);border-radius:var(--ad-radius);
    cursor:pointer;font-size:13px;color:var(--ad-text);transition:all .15s;text-decoration:none;
  }
  .ad-action-btn:hover { background:var(--ad-bg);border-color:var(--ad-accent);color:var(--ad-brand); }
  .ad-action-btn .ad-act-ico { font-size:18px; }
  .ad-action-lbl { flex:1;font-weight:600; }
  .ad-action-arrow { color:var(--ad-muted); }
  /* ── Chart size helper ── */
  .ad-chart-box { position:relative; }
</style>

<div class="adv-dash">

  <!-- ══ KPI ROW ══════════════════════════════════════════════════════════ -->
  <div class="ad-kpi-row">
    <div class="ad-kpi" style="border-color:#5c4da8">
      <div class="ad-kpi-ico">📦</div>
      <div>
        <div class="ad-kpi-val" id="ad-kpi1">—</div>
        <div class="ad-kpi-lbl">Open Orders</div>
        <span class="ad-kpi-trend trend-up" id="ad-t1">↑ 12%</span>
      </div>
    </div>
    <div class="ad-kpi" style="border-color:#0891b2">
      <div class="ad-kpi-ico">💰</div>
      <div>
        <div class="ad-kpi-val" style="color:#0891b2" id="ad-kpi2">—</div>
        <div class="ad-kpi-lbl">Revenue (MTD)</div>
        <span class="ad-kpi-trend trend-up" id="ad-t2">↑ 8%</span>
      </div>
    </div>
    <div class="ad-kpi" style="border-color:#16a34a">
      <div class="ad-kpi-ico">👥</div>
      <div>
        <div class="ad-kpi-val" style="color:#16a34a" id="ad-kpi3">—</div>
        <div class="ad-kpi-lbl">Active Customers</div>
        <span class="ad-kpi-trend trend-flat" id="ad-t3">→ 0%</span>
      </div>
    </div>
    <div class="ad-kpi" style="border-color:#dc2626">
      <div class="ad-kpi-ico">⚠️</div>
      <div>
        <div class="ad-kpi-val" style="color:#dc2626" id="ad-kpi4">—</div>
        <div class="ad-kpi-lbl">Overdue Tasks</div>
        <span class="ad-kpi-trend trend-down" id="ad-t4">↑ 3%</span>
      </div>
    </div>
  </div>

  <!-- ══ CHARTS ═══════════════════════════════════════════════════════════ -->
  <div class="ad-charts">
    <div class="ad-card">
      <div class="ad-card-hdr">
        <span class="ad-card-title">Revenue Trend (Last 6 months)</span>
        <span class="ad-card-badge" id="ad-chart-total">Loading…</span>
      </div>
      <div class="ad-chart-box" style="height:240px">
        <canvas id="ad-area-chart"></canvas>
      </div>
    </div>
    <div class="ad-card">
      <div class="ad-card-hdr">
        <span class="ad-card-title">Status Breakdown</span>
      </div>
      <div class="ad-chart-box" style="height:240px">
        <canvas id="ad-donut-chart"></canvas>
      </div>
    </div>
  </div>

  <!-- ══ BOTTOM ROW: Activity Feed + Quick Actions ════════════════════════ -->
  <div class="ad-bottom">
    <div class="ad-card">
      <div class="ad-card-hdr">
        <span class="ad-card-title">Activity Feed</span>
        <a href="#" style="font-size:11px;color:#5c4da8" onclick="return false">View all</a>
      </div>
      <ul class="ad-feed" id="ad-feed">
        <li><div class="ad-feed-dot"></div><div class="ad-feed-text">No activity yet. Pass <code>activity</code> list from Python.</div><div class="ad-feed-time">now</div></li>
      </ul>
    </div>
    <div class="ad-card">
      <div class="ad-card-hdr"><span class="ad-card-title">Quick Actions</span></div>
      <div class="ad-actions">
        <a class="ad-action-btn" href="#" onclick="frappe.new_doc('Sales Order');return false">
          <span class="ad-act-ico">📋</span><span class="ad-action-lbl">New Sales Order</span><span class="ad-action-arrow">›</span>
        </a>
        <a class="ad-action-btn" href="#" onclick="frappe.set_route('List','Customer');return false">
          <span class="ad-act-ico">👤</span><span class="ad-action-lbl">Customer List</span><span class="ad-action-arrow">›</span>
        </a>
        <a class="ad-action-btn" href="#" onclick="frappe.set_route('query-report','Sales Analytics');return false">
          <span class="ad-act-ico">📊</span><span class="ad-action-lbl">Sales Analytics</span><span class="ad-action-arrow">›</span>
        </a>
        <a class="ad-action-btn" href="#" onclick="frappe.set_route('List','ToDo');return false">
          <span class="ad-act-ico">✅</span><span class="ad-action-lbl">My Tasks</span><span class="ad-action-arrow">›</span>
        </a>
      </div>
    </div>
  </div>

</div><!-- /adv-dash -->

<script>
/* ── Load Chart.js from CDN then initialise charts ── */
(function initCharts() {
  if (window.Chart) { return _adDrawCharts(); }
  var s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
  s.onload = _adDrawCharts;
  document.head.appendChild(s);
})();

function _adDrawCharts() {
  /* ── Sample data — replace with real frappe.call() data ── */
  var months  = ['Oct','Nov','Dec','Jan','Feb','Mar'];
  var revenue = [420000, 510000, 480000, 620000, 590000, 710000];
  var prev    = [380000, 460000, 440000, 570000, 540000, 660000];

  /* ── Area chart ── */
  var aCtx = document.getElementById('ad-area-chart').getContext('2d');
  new Chart(aCtx, {
    type: 'line',
    data: {
      labels: months,
      datasets: [
        {
          label: 'This Year',
          data: revenue,
          borderColor: '#5c4da8',
          backgroundColor: 'rgba(92,77,168,.12)',
          fill: true, tension: .4, pointRadius: 4, pointBackgroundColor: '#5c4da8'
        },
        {
          label: 'Last Year',
          data: prev,
          borderColor: '#c4b5fd',
          backgroundColor: 'rgba(196,181,253,.07)',
          fill: true, tension: .4, pointRadius: 3, borderDash: [4,3]
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: { font: { size: 11 } } } },
      scales: {
        y: { ticks: { callback: v => '₹' + (v/1000).toFixed(0) + 'k', font: { size: 11 } }, grid: { color: '#f0ecf8' } },
        x: { ticks: { font: { size: 11 } }, grid: { display: false } }
      }
    }
  });

  var total = revenue.reduce(function(a,b){return a+b;},0);
  document.getElementById('ad-chart-total').textContent = '₹' + (total/100000).toFixed(1) + 'L total';

  /* ── Donut chart ── */
  var dCtx = document.getElementById('ad-donut-chart').getContext('2d');
  new Chart(dCtx, {
    type: 'doughnut',
    data: {
      labels: ['Open','Closed','Pending','Cancelled'],
      datasets: [{
        data: [42, 31, 18, 9],
        backgroundColor: ['#5c4da8','#0891b2','#f59e0b','#dc2626'],
        borderWidth: 0, hoverOffset: 6
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 12 } }
      },
      cutout: '68%'
    }
  });
}

/* ── KPI loader — replace with real frappe.call() ──
frappe.call({
  method: 'your_app.api.module.get_dashboard_data',
  callback: function(r) {
    if (!r.message) return;
    var d = r.message;
    document.getElementById('ad-kpi1').textContent = d.open_orders   || 0;
    document.getElementById('ad-kpi2').textContent = '₹' + (d.revenue || 0).toLocaleString('en-IN');
    document.getElementById('ad-kpi3').textContent = d.customers      || 0;
    document.getElementById('ad-kpi4').textContent = d.overdue        || 0;
    // Populate feed
    var feed = document.getElementById('ad-feed');
    feed.innerHTML = '';
    (d.activity || []).forEach(function(a) {
      feed.innerHTML += '<li><div class="ad-feed-dot"></div>'
        + '<div class="ad-feed-text">' + frappe.utils.escape_html(a.message) + '</div>'
        + '<div class="ad-feed-time">' + frappe.utils.escape_html(a.time) + '</div></li>';
    });
  }
});
── */
</script>
'''


def _desk_tpl_template(page_name, title, preset='blank'):
    """Return rich commented Jinja2 HTML template for a desk page."""
    cc = page_name.replace("_", "-")
    if preset == 'app_shell_sidebar':
        return _desk_tpl_app_shell(cc, title)
    elif preset == 'split_explorer':
        return _desk_tpl_split_explorer(cc, title)
    elif preset == 'adv_dashboard':
        return _desk_tpl_adv_dashboard(cc, title)
    # ── default blank template ────────────────────────────────────────────────
    css_class = cc
    return f'''{{#-
  Jinja2 template for the {title} desk page.
  Available in context: everything passed from get_{page_name.replace("-","_")}() in {page_name}.py
  Frappe desk pages use Bootstrap 4/5 via frappe.ui — use standard BS classes freely.
-#}}
<style>
  /* ── CSS custom properties ────────────────────────────────────────────── */
  :root {{
    --brand:       #5c4da8;
    --brand-light: #ede9fe;
    --accent:      #8b5cf6;
    --text-dark:   #1e1b3a;
    --text-muted:  #6b7280;
    --radius:      10px;
    --shadow:      0 4px 20px rgba(92,77,168,.12);
  }}
  .{css_class}-page {{ font-family: inherit; padding: 0 4px; }}

  /* ── KPI card ─────────────────────────────────────────────────────────── */
  .kpi-card {{
    background: #fff; border-radius: var(--radius); box-shadow: var(--shadow);
    padding: 20px 24px; border-left: 4px solid var(--brand);
  }}
  .kpi-value {{ font-size: 2rem; font-weight: 900; color: var(--brand); }}
  .kpi-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted); }}

  /* ── Data table ───────────────────────────────────────────────────────── */
  .dk-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .dk-table thead th {{
    background: var(--brand-light); color: var(--brand);
    padding: 10px 14px; text-align: left; font-weight: 700;
    border-bottom: 2px solid var(--brand);
  }}
  .dk-table tbody tr:hover {{ background: #f8f5ff; cursor: pointer; }}
  .dk-table tbody td {{ padding: 9px 14px; border-bottom: 1px solid #f3f0fc; }}

  /* ── Status badge ─────────────────────────────────────────────────────── */
  .dk-badge {{
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 700;
  }}
  .dk-badge.green  {{ background: #dcfce7; color: #14532d; }}
  .dk-badge.red    {{ background: #fee2e2; color: #7f1d1d; }}
  .dk-badge.yellow {{ background: #fef9c3; color: #713f12; }}
  .dk-badge.blue   {{ background: #dbeafe; color: #1e3a5f; }}
  .dk-badge.purple {{ background: var(--brand-light); color: var(--brand); }}
</style>

<div class="{css_class}-page">

  {{#- ══ KPI CARDS ══════════════════════════════════════════════════════════ -#}}
  {{#- Uncomment when you pass kpis from Python context
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin-bottom:20px">
    {{% for kpi in kpis %}}
    <div class="kpi-card" style="border-color:{{{{ kpi.color }}}}">
      <div class="kpi-value" style="color:{{{{ kpi.color }}}}">{{{{ kpi.value }}}}</div>
      <div class="kpi-label">{{{{ kpi.label }}}}</div>
    </div>
    {{% endfor %}}
  </div>
  -#}}

  {{#- ══ DATA TABLE ════════════════════════════════════════════════════════ -#}}
  {{#- Uncomment and adapt columns to your DocType
  <div style="background:#fff;border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden">
    <div style="padding:14px 18px;font-weight:700;font-size:14px;color:var(--text-dark);border-bottom:1px solid var(--brand-light)">
      {title}
    </div>
    <table class="dk-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Date</th>
          <th>Amount</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {{% for row in records %}}
        <tr class="data-row" data-name="{{{{ row.name }}}}">
          <td>{{{{ row.name }}}}</td>
          <td>{{{{ row.posting_date }}}}</td>
          <td>{{{{ frappe.format_value(row.grand_total, dict(fieldtype="Currency")) }}}}</td>
          <td>
            <span class="dk-badge {{% if row.status == "Submitted" %}}green
                                   {{% elif row.status == "Cancelled" %}}red
                                   {{% else %}}yellow{{% endif %}}">{{{{ row.status }}}}</span>
          </td>
        </tr>
        {{% else %}}
        <tr><td colspan="4" style="text-align:center;padding:30px;color:var(--text-muted)">No records found.</td></tr>
        {{% endfor %}}
      </tbody>
    </table>
  </div>
  -#}}

  {{#- ══ PLACEHOLDER ═══════════════════════════════════════════════════════ -#}}
  <div style="text-align:center;padding:60px 20px;color:var(--text-muted)">
    <div style="font-size:3rem;margin-bottom:12px">🖥️</div>
    <h3 style="color:var(--text-dark)">{title}</h3>
    <p>Edit <code>{page_name}.py</code> to return data and <code>templates/{page_name}.html</code> to design the layout.</p>
  </div>

</div>
'''


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
