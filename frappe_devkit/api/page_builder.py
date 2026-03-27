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
    else:  # blank
        base += '''
    # context.records = frappe.get_all("DocType", fields=["name"], limit=10)
    return context
'''
    return base


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


def _desk_js_template(page_name, title, method_path, app):
    """Return rich commented JS boilerplate for a desk page."""
    fn = page_name.replace("-", "_")
    return f'''// ── {title} — Desk Page ──────────────────────────────────────────────────────
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
\t\tsingle_column: false,   // set true for a full-width single column layout
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


def _desk_py_template(fn_name, tpl_path, app, module, page_name):
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


def _desk_tpl_template(page_name, title):
    """Return rich commented Jinja2 HTML template for a desk page."""
    css_class = page_name.replace("_", "-")
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
