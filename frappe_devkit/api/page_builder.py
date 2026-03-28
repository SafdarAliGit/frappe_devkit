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
    """Return modules for an app, reading modules.txt as the authoritative source."""
    root = _app_root(app)
    inner = app.replace("-", "_")

    # Try modules.txt in the inner package directory first, then the app root
    for base in [os.path.join(root, inner), os.path.join(root, app), root]:
        mtxt = os.path.join(base, 'modules.txt')
        if os.path.isfile(mtxt):
            with open(mtxt) as f:
                modules = [l.strip() for l in f if l.strip()]
            return {'modules': modules}

    return {'modules': []}


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
            '    <a href="#" onclick="window.location.href=\'/login?redirect-to=\'+encodeURIComponent(window.location.pathname);return false;" class="btn btn-lg mt-3" style="background:var(--brand);color:#fff">Log In</a>\n'
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
            '      <!-- Share buttons (uncomment to enable) -->\n'
            '      <!-- <div class="mt-4 d-flex gap-3">\n'
            '        <a href="#" onclick="window.open(\'https://twitter.com/intent/tweet?text=\'+encodeURIComponent(document.title)+\'&url=\'+encodeURIComponent(window.location.href),\'_blank\');return false;" class="btn btn-sm btn-outline-secondary">Twitter</a>\n'
            '        <a href="#" onclick="window.open(\'https://www.linkedin.com/sharing/share-offsite/?url=\'+encodeURIComponent(window.location.href),\'_blank\');return false;" class="btn btn-sm btn-outline-secondary">LinkedIn</a>\n'
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

# ════════════════════════════════════════════════════════════════════════════════
# {title} — Web Page Backend
# ════════════════════════════════════════════════════════════════════════════════
# HOW WWW PAGES WORK
# ─────────────────────────────────────────────────────────────────────────────
# Frappe renders {title.lower().replace(" ", "_")}.html with the context dict built here.
# Route: /{title.lower().replace(" ", "-")} (matches the filename without extension)
# URL params are in frappe.form_dict  e.g. frappe.form_dict.get("name")
#
# HOW TO EXTEND THIS PAGE
# ─────────────────────────────────────────────────────────────────────────────
# • Add keys to `context` here → use them as {{ variable }} in the HTML template
# • Add AJAX endpoints: create @frappe.whitelist() functions in a separate .py file
#   and call them from JavaScript via frappe.call({{ method: "...", args: {{}} }})
# • Add a sitemap entry: set context.sitemap = True and context.priority = 0.8
# • Control caching: set no_cache = 0 and define context.base_template_path for CDN
# • Create child pages: add {title.lower().replace(" ", "_")}/child-name.html + .py
# ════════════════════════════════════════════════════════════════════════════════

# ── Page-level settings ───────────────────────────────────────────────────────
no_cache       = 1      # 1 = no HTTP cache (good for dynamic content)
# login_required = True   # redirect Guest users to /login automatically
# allow_guest   = True    # explicitly allow unauthenticated access
# sitemap       = True    # include this page in the sitemap


def get_context(context):
    """
    Build the Jinja2 template context for {title}.

    `context` is a frappe._dict — set attributes directly:
        context.my_var = "value"        → {{ my_var }} in HTML
        context.records = [...]         → {{% for r in records %}} in HTML

    ── Auth & permission guard ────────────────────────────────────────────────
    # Guest redirect (manual):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.local.request.path
        raise frappe.Redirect
    # Role guard:
    if not frappe.has_permission("Sales Invoice", "read"):
        raise frappe.PermissionError

    ── SEO / Open Graph meta tags ─────────────────────────────────────────────
    context.metatags = {{
        "title":       "{title}",
        "description": "Describe this page in 1-2 sentences for search engines.",
        "image":       "/assets/{app}/images/og-cover.png",
        "keywords":    "keyword1, keyword2, keyword3",
        "og:type":     "website",
    }}

    ── Current user info ──────────────────────────────────────────────────────
    context.current_user   = frappe.session.user
    context.user_roles     = frappe.get_roles()
    context.full_name      = frappe.db.get_value("User", frappe.session.user, "full_name")
    context.is_system_user = "System Manager" in frappe.get_roles()

    ── URL query parameters ───────────────────────────────────────────────────
    context.search    = frappe.form_dict.get("q", "")
    context.category  = frappe.form_dict.get("category", "")
    context.page_no   = int(frappe.form_dict.get("page") or 1)

    ── ORM list query with pagination ────────────────────────────────────────
    PAGE_SIZE = 20
    filters = {{"docstatus": 1}}
    if context.category: filters["item_group"] = context.category
    if context.search:   filters["item_name"]  = ["like", f"%{{context.search}}%"]
    context.records = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=["name", "customer", "grand_total", "posting_date", "status"],
        order_by="posting_date desc",
        limit_start=(context.page_no - 1) * PAGE_SIZE,
        limit_page_length=PAGE_SIZE + 1,
    )
    context.has_next = len(context.records) > PAGE_SIZE
    context.records  = context.records[:PAGE_SIZE]
    context.total    = frappe.db.count("Sales Invoice", filters)

    ── Fetch a single document by URL param ──────────────────────────────────
    name = frappe.form_dict.get("name")
    if not name:
        raise frappe.DoesNotExistError
    doc = frappe.get_doc("Sales Invoice", name)
    if not frappe.has_permission("Sales Invoice", "read", doc=doc):
        raise frappe.PermissionError
    context.doc = doc.as_dict()

    ── System defaults ────────────────────────────────────────────────────────
    context.company  = frappe.defaults.get_global_default("company")
    context.currency = frappe.defaults.get_global_default("currency")

    ── Cache expensive queries (5 minutes) ───────────────────────────────────
    cache_key = f"{{frappe.local.site}}:{title.lower().replace(' ','_')}_data"
    cached = frappe.cache().get_value(cache_key)
    if not cached:
        cached = frappe.get_all("Item", fields=["name","item_name"], limit=500)
        frappe.cache().set_value(cache_key, cached, expires_in_sec=300)
    context.items = cached

    ── Custom 404 / redirect ──────────────────────────────────────────────────
    raise frappe.DoesNotExistError          # → shows 404 page
    frappe.local.flags.redirect_location = "/other-page"
    raise frappe.Redirect

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
        {% if prev_article is defined and prev_article.label %}
        <a href="{{ prev_article.href }}" class="pn-card" style="text-align:left">
          <div class="pn-label">← Previous</div>
          <div class="pn-title">{{ prev_article.label }}</div>
        </a>
        {% endif %}
        {% if next_article is defined and next_article.label %}
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

    # Frappe's load_assets() calls scrub(self.name) which converts hyphens to underscores,
    # so the directory and all filenames must use underscores even if page_name has hyphens.
    dir_name = page_name.replace("-", "_")

    page_dir = _safe_join(root, os.path.relpath(mod_dir, root), "page", dir_name)
    if os.path.exists(page_dir):
        frappe.throw(f"Desk page '{page_name}' already exists")
    os.makedirs(page_dir)

    # templates/ subfolder
    tpl_dir = os.path.join(page_dir, "templates")
    os.makedirs(tpl_dir, exist_ok=True)

    # relative template path used in render_template (relative to inner package dir)
    # e.g. my_dev/page/adv_dashboard/templates/adv_dashboard.html
    rel_from_inner = os.path.relpath(page_dir, os.path.join(root, inner)).replace("\\", "/")
    tpl_path = f"{rel_from_inner}/templates/{dir_name}.html"

    # Python module path importable from app root (sys.path entry): inner.module.page.name.name
    # e.g. my_dev.my_dev.page.adv_dashboard.adv_dashboard.get_adv_dashboard
    rel_from_root = os.path.relpath(page_dir, root).replace("\\", "/")

    fn_name = dir_name

    # .json — name field keeps the original page_name (may have hyphens, used as URL/DB key)
    page_meta = {
        "doctype": "Page", "name": page_name, "page_name": page_name,
        "title": title, "module": module,
        "roles": [{"doctype": "Has Role", "role": "System Manager"}],
    }
    with open(os.path.join(page_dir, dir_name + ".json"), "w") as f:
        json.dump(page_meta, f, indent=1)

    # .py
    py_body = _desk_py_template(fn_name, tpl_path, app, module, dir_name, preset)
    with open(os.path.join(page_dir, dir_name + ".py"), "w") as f:
        f.write(py_body)

    # .js — frappe.pages[...] must use the original page_name (hyphens = URL route key)
    method_path = f"{rel_from_root.replace('/', '.')}.{fn_name}.get_{fn_name}"
    js_body = _desk_js_template(page_name, title, method_path, app, preset)
    with open(os.path.join(page_dir, dir_name + ".js"), "w") as f:
        f.write(js_body)

    # .html (minimal page-level wrapper)
    with open(os.path.join(page_dir, dir_name + ".html"), "w") as f:
        f.write(f"<!-- Frappe page wrapper for {title} -->\n")

    # templates/{dir_name}.html
    tpl_body = _desk_tpl_template(dir_name, title, preset)
    with open(os.path.join(tpl_dir, dir_name + ".html"), "w") as f:
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
\t// Fires every time the user navigates to this page (tab switch or URL change).
\t// Useful for refreshing stale data without a full reload.
\t// var page = wrapper.page_obj;
\t// if (page) load_data();
}};

frappe.pages["{page_name}"].on_page_hide = function(wrapper) {{
\t// Fires when the user leaves this page. Clean up timers, event listeners, etc.
\t// clearInterval(window._refresh_timer);
\t// frappe.realtime.off("my_event");
}};

// ── bind_events: wire up interactive elements after HTML is injected ──────────
// Called every time load_data() succeeds. Re-attach handlers here because
// $(page.main).html(...) replaces the DOM, removing all previous listeners.
function bind_events(page) {{

\t// ── Table row → navigate to form ───────────────────────────────────────────
\t// $(page.main).find(".data-row").on("click", function() {{
\t//   frappe.set_route("Form", "Sales Invoice", $(this).data("name"));
\t// }});

\t// ── Action button → call backend ───────────────────────────────────────────
\t// $(page.main).find("[data-action='approve']").on("click", function() {{
\t//   var name = $(this).data("name");
\t//   frappe.confirm("Approve this record?", () => {{
\t//     frappe.call({{
\t//       method: "{method_path}.approve_record",
\t//       args: {{ name }},
\t//       callback: r => {{ frappe.show_alert("Approved", "green"); load_data(); }}
\t//     }});
\t//   }});
\t// }});

\t// ── Inline edit → save on blur ─────────────────────────────────────────────
\t// $(page.main).find(".editable-field").on("blur", function() {{
\t//   frappe.call({{
\t//     method: "{method_path}.save_field",
\t//     args: {{ name: $(this).data("name"), field: $(this).data("field"), value: $(this).val() }},
\t//     callback: r => frappe.show_alert("Saved", "green"),
\t//   }});
\t// }});

\t// ── Chart.js initialisation ────────────────────────────────────────────────
\t// var $canvas = $(page.main).find("#my-chart");
\t// if ($canvas.length) {{
\t//   new Chart($canvas[0].getContext("2d"), {{
\t//     type: "bar",
\t//     data: {{
\t//       labels: JSON.parse($canvas.data("labels") || "[]"),
\t//       datasets: [{{ label: "Revenue", data: JSON.parse($canvas.data("values") || "[]"),
\t//                    backgroundColor: "#5c4da880", borderColor: "#5c4da8", borderWidth: 2 }}]
\t//     }},
\t//     options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
\t//   }});
\t// }}

\t// ── Real-time push from server ─────────────────────────────────────────────
\t// frappe.realtime.on("{page_name}_update", (data) => {{
\t//   // Call frappe.publish_realtime("{page_name}_update", payload) in Python to trigger
\t//   frappe.show_alert(data.message || "Update received", "blue");
\t//   load_data();
\t// }});

\t// ── Infinite scroll ────────────────────────────────────────────────────────
\t// var _page_no = 1;
\t// $(page.main).find(".load-more-btn").on("click", function() {{
\t//   _page_no++;
\t//   frappe.call({{ method: "...get_{fn}", args: {{ page_no: _page_no }},
\t//     callback: r => $(page.main).find(".records-list").append(r.message)
\t//   }});
\t// }});
}}
'''


def _desk_py_preset_block(preset, tpl_path, page_name):
    """Return a preset-specific commented Python snippet appended after the generic boilerplate."""
    _PRESET_BLOCKS = {
        'dashboard': f'''
    # ════════════════════════════════════════════════════════════════════════
    # DASHBOARD preset — suggested queries
    # ════════════════════════════════════════════════════════════════════════
    # company   = kwargs.get("company") or frappe.defaults.get_global_default("company")
    # from_date = kwargs.get("from_date") or frappe.utils.add_months(frappe.utils.today(), -1)
    # to_date   = kwargs.get("to_date")   or frappe.utils.today()
    #
    # # KPI: Total Revenue (submitted Sales Invoices)
    # total_revenue = frappe.db.sql("""
    #     SELECT IFNULL(SUM(grand_total), 0) AS val
    #     FROM `tabSales Invoice`
    #     WHERE docstatus = 1 AND company = %(company)s
    #       AND posting_date BETWEEN %(from_date)s AND %(to_date)s
    # """, {{"company": company, "from_date": from_date, "to_date": to_date}}, as_dict=1)[0].val
    #
    # # KPI: Total Expenses (submitted Purchase Invoices)
    # total_expenses = frappe.db.sql("""
    #     SELECT IFNULL(SUM(grand_total), 0) AS val
    #     FROM `tabPurchase Invoice`
    #     WHERE docstatus = 1 AND company = %(company)s
    #       AND posting_date BETWEEN %(from_date)s AND %(to_date)s
    # """, {{"company": company, "from_date": from_date, "to_date": to_date}}, as_dict=1)[0].val
    #
    # # KPI: Open Orders (Sales Orders not fully delivered+billed)
    # open_orders = frappe.db.count("Sales Order", {{
    #     "company": company, "docstatus": 1,
    #     "status": ["in", ["To Deliver and Bill", "To Deliver", "To Bill"]],
    # }})
    #
    # # KPI: Open Issues
    # open_issues = frappe.db.count("Issue", {{"status": ["in", ["Open", "Replied"]]}})
    #
    # # Recent Sales Invoices
    # recent_invoices = frappe.get_all(
    #     "Sales Invoice",
    #     filters={{"company": company, "docstatus": 1}},
    #     fields=["name", "customer", "grand_total", "posting_date", "status", "outstanding_amount"],
    #     order_by="posting_date desc", limit=20,
    # )
    #
    # # Top Customers by revenue
    # top_customers = frappe.db.sql("""
    #     SELECT customer, SUM(grand_total) AS total
    #     FROM `tabSales Invoice`
    #     WHERE docstatus = 1 AND company = %(company)s
    #     GROUP BY customer ORDER BY total DESC LIMIT 10
    # """, {{"company": company}}, as_dict=1)
    #
    # # Activity Feed
    # activity = frappe.get_all(
    #     "Activity Log",
    #     fields=["subject", "full_name AS user", "creation AS time"],
    #     order_by="creation desc", limit=15,
    # )
    #
    # context = {{
    #     "title":          "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "total_revenue":  total_revenue,
    #     "total_expenses": total_expenses,
    #     "open_orders":    open_orders,
    #     "open_issues":    open_issues,
    #     "recent_invoices": recent_invoices,
    #     "top_customers":  top_customers,
    #     "activity":       activity,
    # }}
''',
        'list_tool': f'''
    # ════════════════════════════════════════════════════════════════════════
    # LIST TOOL preset — suggested queries
    # ════════════════════════════════════════════════════════════════════════
    # doctype    = kwargs.get("doctype", "Sales Invoice")
    # page_no    = int(kwargs.get("page_no", 1))
    # page_size  = int(kwargs.get("page_size", 20))
    # status     = kwargs.get("status")
    # from_date  = kwargs.get("from_date")
    # to_date    = kwargs.get("to_date")
    # search_txt = kwargs.get("search_txt", "")
    #
    # filters = {{"docstatus": ["!=", 2]}}
    # if status:    filters["status"] = status
    # if from_date: filters["posting_date"] = [">=", from_date]
    # if to_date:   filters["posting_date"] = ["<=", to_date]
    # if search_txt:
    #     filters["name"] = ["like", f"%{{search_txt}}%"]
    #
    # total_count = frappe.db.count(doctype, filters)
    # records = frappe.get_all(
    #     doctype,
    #     filters=filters,
    #     fields=["name", "customer", "posting_date", "grand_total", "status", "owner"],
    #     order_by="posting_date desc",
    #     limit_start=(page_no - 1) * page_size,
    #     limit_page_length=page_size,
    # )
    # context = {{
    #     "title":       "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "records":     records,
    #     "total_count": total_count,
    #     "page_no":     page_no,
    #     "page_size":   page_size,
    # }}
''',
        'form_tool': f'''
    # ════════════════════════════════════════════════════════════════════════
    # FORM TOOL preset — load/save a single document
    # ════════════════════════════════════════════════════════════════════════
    # docname = kwargs.get("docname")   # None = new record
    #
    # if docname:
    #     doc = frappe.get_doc("Sales Invoice", docname)
    #     doc.check_permission("read")
    #     context = {{
    #         "title":   "{page_name.replace("-", " ").replace("_", " ").title()}",
    #         "docname": docname,
    #         "doc":     doc.as_dict(),
    #     }}
    # else:
    #     context = {{
    #         "title":   "{page_name.replace("-", " ").replace("_", " ").title()}",
    #         "docname": None,
    #         "doc":     {{}},
    #     }}
    #
    # # --- Save handler (separate whitelisted function) ---
    # # @frappe.whitelist()
    # # def save_{page_name.replace("-","_")}(**kwargs):
    # #     data = frappe.parse_json(kwargs.get("data", "{{}}"))
    # #     if data.get("name"):
    # #         doc = frappe.get_doc("Sales Invoice", data["name"])
    # #         doc.update(data); doc.save()
    # #     else:
    # #         doc = frappe.get_doc({{"doctype": "Sales Invoice", **data}})
    # #         doc.insert()
    # #     frappe.db.commit()
    # #     return doc.name
''',
        'analytics': f'''
    # ════════════════════════════════════════════════════════════════════════
    # ANALYTICS preset — metrics + trend data
    # ════════════════════════════════════════════════════════════════════════
    # company   = kwargs.get("company") or frappe.defaults.get_global_default("company")
    # from_date = kwargs.get("from_date") or frappe.utils.add_months(frappe.utils.today(), -12)
    # to_date   = kwargs.get("to_date")   or frappe.utils.today()
    # group_by  = kwargs.get("group_by", "month")   # month | quarter | year
    #
    # # Top-level metrics
    # revenue = frappe.db.sql("""SELECT IFNULL(SUM(grand_total),0) v FROM `tabSales Invoice`
    #     WHERE docstatus=1 AND company=%(co)s AND posting_date BETWEEN %(fd)s AND %(td)s
    # """, {{"co": company, "fd": from_date, "td": to_date}}, as_dict=1)[0].v
    #
    # cost = frappe.db.sql("""SELECT IFNULL(SUM(grand_total),0) v FROM `tabPurchase Invoice`
    #     WHERE docstatus=1 AND company=%(co)s AND posting_date BETWEEN %(fd)s AND %(td)s
    # """, {{"co": company, "fd": from_date, "td": to_date}}, as_dict=1)[0].v
    #
    # # Monthly trend
    # trend_data = frappe.db.sql("""
    #     SELECT DATE_FORMAT(posting_date,'%Y-%m') AS month,
    #            SUM(grand_total) AS revenue, COUNT(*) AS count
    #     FROM `tabSales Invoice`
    #     WHERE docstatus=1 AND company=%(co)s
    #       AND posting_date BETWEEN %(fd)s AND %(td)s
    #     GROUP BY month ORDER BY month
    # """, {{"co": company, "fd": from_date, "td": to_date}}, as_dict=1)
    #
    # # Top 10 customers
    # top_customers = frappe.db.sql("""
    #     SELECT customer, SUM(grand_total) AS total, COUNT(*) AS invoice_count
    #     FROM `tabSales Invoice`
    #     WHERE docstatus=1 AND company=%(co)s
    #       AND posting_date BETWEEN %(fd)s AND %(td)s
    #     GROUP BY customer ORDER BY total DESC LIMIT 10
    # """, {{"co": company, "fd": from_date, "td": to_date}}, as_dict=1)
    #
    # context = {{
    #     "title":         "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "metrics":       {{"revenue": revenue, "cost": cost, "profit": revenue - cost,
    #                        "margin": round((revenue - cost) / revenue * 100, 1) if revenue else 0}},
    #     "trend_data":    trend_data,
    #     "top_customers": top_customers,
    # }}
''',
        'settings': f'''
    # ════════════════════════════════════════════════════════════════════════
    # SETTINGS preset — read/write frappe.db.get/set_single_value
    # ════════════════════════════════════════════════════════════════════════
    # # Load settings from a Single DocType (e.g. "My App Settings")
    # settings_doc = frappe.get_single("My App Settings")
    # context = {{
    #     "title": "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "settings": settings_doc.as_dict(),
    #     "timezones": frappe.utils.get_time_zone_abbr(),
    #     "companies":  [c.name for c in frappe.get_all("Company", fields=["name"])],
    # }}
    #
    # # --- Save handler ---
    # # @frappe.whitelist()
    # # def save_{page_name.replace("-","_")}(**kwargs):
    # #     data = frappe.parse_json(kwargs.get("data", "{{}}"))
    # #     doc  = frappe.get_single("My App Settings")
    # #     for key, val in data.items():
    # #         doc.set(key, val)
    # #     doc.save(ignore_permissions=True)
    # #     frappe.db.commit()
    # #     return "Saved"
''',
        'wizard': f'''
    # ════════════════════════════════════════════════════════════════════════
    # WIZARD preset — multi-step form context
    # ════════════════════════════════════════════════════════════════════════
    # # Doctypes for dropdowns
    # users     = frappe.get_all("User", filters={{"enabled": 1}}, fields=["name", "full_name"])
    # doctypes  = frappe.get_all("DocType", filters={{"istable": 0}}, fields=["name"], limit=50)
    # priorities = ["Low", "Medium", "High", "Urgent"]
    #
    # context = {{
    #     "title":      "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "users":      users,
    #     "doctypes":   doctypes,
    #     "priorities": priorities,
    # }}
    #
    # # --- Submit handler ---
    # # @frappe.whitelist()
    # # def submit_{page_name.replace("-","_")}(**kwargs):
    # #     data = frappe.parse_json(kwargs.get("data"))
    # #     # data = {{ "step1": {{...}}, "step2": {{...}} }}
    # #     doc = frappe.get_doc({{
    # #         "doctype":      data["step1"]["doctype"],
    # #         "subject":      data["step1"]["name"],
    # #         "description":  data["step1"]["description"],
    # #         "priority":     data["step1"]["priority"],
    # #         "assigned_to":  data["step2"]["assigned_to"],
    # #         "due_date":     data["step2"]["due_date"],
    # #     }})
    # #     doc.insert()
    # #     frappe.db.commit()
    # #     return {{"docname": doc.name}}
''',
        'kanban': f'''
    # ════════════════════════════════════════════════════════════════════════
    # KANBAN preset — group Tasks or Issues by status
    # ════════════════════════════════════════════════════════════════════════
    # COLUMN_MAP = {{
    #     "todo":        "Open",
    #     "in_progress": "Working",
    #     "in_review":   "Pending Review",
    #     "done":        "Completed",
    # }}
    #
    # all_tasks = frappe.get_all(
    #     "Task",
    #     fields=["name", "subject AS title", "status", "priority",
    #             "_assign AS assignee", "exp_end_date AS due_date",
    #             "description", "tags"],
    #     order_by="modified desc",
    # )
    #
    # columns = {{col: [] for col in COLUMN_MAP}}
    # for task in all_tasks:
    #     for col_key, status_val in COLUMN_MAP.items():
    #         if task.status == status_val:
    #             columns[col_key].append(task)
    #
    # context = {{
    #     "title":   "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "columns": columns,
    # }}
''',
        'import_export': f'''
    # ════════════════════════════════════════════════════════════════════════
    # IMPORT/EXPORT preset — doctype fields + import history
    # ════════════════════════════════════════════════════════════════════════
    # selected_doctype = kwargs.get("doctype", "Sales Invoice")
    # meta = frappe.get_meta(selected_doctype)
    # doctype_fields = [
    #     {{"fieldname": f.fieldname, "label": f.label, "fieldtype": f.fieldtype}}
    #     for f in meta.fields
    #     if f.fieldtype not in ("Section Break", "Column Break", "HTML", "Tab Break")
    # ]
    #
    # import_history = frappe.get_all(
    #     "Data Import",
    #     filters={{"reference_doctype": selected_doctype}},
    #     fields=["name", "reference_doctype", "import_type", "status",
    #             "total_records", "failed_records", "creation"],
    #     order_by="creation desc", limit=10,
    # )
    #
    # context = {{
    #     "title":            "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "doctype_fields":   doctype_fields,
    #     "import_history":   import_history,
    #     "selected_doctype": selected_doctype,
    # }}
''',
        'approval_inbox': f'''
    # ════════════════════════════════════════════════════════════════════════
    # APPROVAL INBOX preset — approval requests from Workflow Action
    # ════════════════════════════════════════════════════════════════════════
    # status_filter = kwargs.get("status", "Open")   # Open | Approved | Rejected
    # from_date     = kwargs.get("from_date")
    # to_date       = kwargs.get("to_date")
    # submitted_by  = kwargs.get("submitted_by")
    #
    # filters = {{"status": status_filter}}
    # if from_date: filters["creation"] = [">=", from_date]
    # if to_date:   filters["creation"] = ["<=", to_date]
    # if submitted_by: filters["owner"] = submitted_by
    #
    # requests = frappe.get_all(
    #     "Workflow Action",
    #     filters=filters,
    #     fields=["name", "reference_doctype AS doctype", "reference_name AS document_name",
    #             "owner AS submitted_by", "creation", "status", "workflow_state"],
    #     order_by="creation desc",
    # )
    #
    # # Enrich each request with doc-level data
    # for req in requests:
    #     try:
    #         doc = frappe.get_doc(req.doctype, req.document_name)
    #         req.amount      = getattr(doc, "grand_total", None)
    #         req.description = getattr(doc, "title", None) or getattr(doc, "subject", None)
    #         req.priority    = getattr(doc, "priority", None)
    #         from frappe.utils import pretty_date
    #         req.pending_since = pretty_date(req.creation)
    #     except Exception:
    #         pass
    #
    # context = {{
    #     "title":    "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "requests": requests,
    #     "counts":   {{
    #         "all":     frappe.db.count("Workflow Action"),
    #         "pending": frappe.db.count("Workflow Action", {{"status": "Open"}}),
    #         "approved":frappe.db.count("Workflow Action", {{"status": "Approved"}}),
    #         "rejected":frappe.db.count("Workflow Action", {{"status": "Rejected"}}),
    #     }},
    # }}
''',
        'report_viewer': f'''
    # ════════════════════════════════════════════════════════════════════════
    # REPORT VIEWER preset — dynamic query builder
    # ════════════════════════════════════════════════════════════════════════
    # doctype   = kwargs.get("doctype", "Sales Invoice")
    # filters_j = frappe.parse_json(kwargs.get("filters", "[]"))
    # sort_by   = kwargs.get("sort_by", "name")
    # sort_ord  = kwargs.get("sort_order", "desc")
    # limit     = int(kwargs.get("limit", 50))
    # page_no   = int(kwargs.get("page_no", 1))
    #
    # meta = frappe.get_meta(doctype)
    # columns = [
    #     {{"fieldname": f.fieldname, "label": f.label, "fieldtype": f.fieldtype}}
    #     for f in meta.fields
    #     if f.in_list_view and f.fieldtype not in ("Section Break", "Column Break")
    # ]
    # if not columns:
    #     columns = [{{"fieldname": "name", "label": "Name", "fieldtype": "Data"}}]
    #
    # # Convert filter list [[fieldname, op, value], ...] to frappe filter dict
    # built_filters = {{}}
    # for fltr in filters_j:
    #     if len(fltr) == 3:
    #         built_filters[fltr[0]] = [fltr[1], fltr[2]]
    #
    # fieldnames = [c["fieldname"] for c in columns] + ["name"]
    # total_count = frappe.db.count(doctype, built_filters)
    # data = frappe.get_all(
    #     doctype,
    #     filters=built_filters,
    #     fields=list(set(fieldnames)),
    #     order_by=f"{{sort_by}} {{sort_ord}}",
    #     limit_start=(page_no - 1) * limit,
    #     limit_page_length=limit,
    # )
    #
    # context = {{
    #     "title":        "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "report_title": doctype,
    #     "columns":      columns,
    #     "data":         data,
    #     "total_count":  total_count,
    #     "page_no":      page_no,
    #     "limit":        limit,
    # }}
''',
        'calendar_view': f'''
    # ════════════════════════════════════════════════════════════════════════
    # CALENDAR VIEW preset — build calendar weeks with events
    # ════════════════════════════════════════════════════════════════════════
    # import calendar as pycal
    # from frappe.utils import getdate, today, add_days
    #
    # year  = int(kwargs.get("year",  frappe.utils.getdate().year))
    # month = int(kwargs.get("month", frappe.utils.getdate().month))
    #
    # # Fetch events from multiple sources
    # tasks = frappe.get_all("Task",
    #     filters={{"exp_end_date": ["between", [f"{{year}}-{{month:02d}}-01",
    #                                            f"{{year}}-{{month:02d}}-31"]]}},
    #     fields=["name", "subject AS title", "exp_end_date AS date", "priority"],
    # )
    # for t in tasks: t["color"] = "yellow"; t["category"] = "Task"
    #
    # events_raw = tasks  # add meetings, holidays etc. the same way
    # events_by_date = {{}}
    # for ev in events_raw:
    #     d = str(ev.get("date", ""))[:10]
    #     events_by_date.setdefault(d, []).append(ev)
    #
    # # Build week matrix
    # cal_weeks = []
    # for week in pycal.monthcalendar(year, month):
    #     row = []
    #     for day_num in week:
    #         if day_num == 0:
    #             row.append({{"day": None, "events": []}})
    #         else:
    #             key = f"{{year}}-{{month:02d}}-{{day_num:02d}}"
    #             row.append({{"day": day_num, "date": key,
    #                          "events": events_by_date.get(key, [])}})
    #     cal_weeks.append(row)
    #
    # month_names = ["", "January","February","March","April","May","June",
    #                "July","August","September","October","November","December"]
    # context = {{
    #     "title":             "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "current_month_name": month_names[month],
    #     "current_year":      year,
    #     "current_month":     month,
    #     "calendar_weeks":    cal_weeks,
    # }}
''',
        'audit_trail': f'''
    # ════════════════════════════════════════════════════════════════════════
    # AUDIT TRAIL preset — query Version / Activity Log
    # ════════════════════════════════════════════════════════════════════════
    # user      = kwargs.get("user")
    # doctype   = kwargs.get("doctype")
    # from_date = kwargs.get("from_date")
    # to_date   = kwargs.get("to_date")
    # action    = kwargs.get("action")   # Create | Update | Delete | Submit
    #
    # filters = {{}}
    # if user:      filters["owner"] = user
    # if doctype:   filters["ref_doctype"] = doctype
    # if from_date: filters["creation"]    = [">=", from_date]
    # if to_date:   filters["creation"]    = ["<=", to_date]
    # if action:    filters["data"]        = ["like", f"%{{action}}%"]
    #
    # raw_logs = frappe.get_all(
    #     "Version",
    #     filters=filters,
    #     fields=["name", "ref_doctype AS doctype", "docname",
    #             "owner AS user", "creation AS timestamp", "data"],
    #     order_by="creation desc", limit=50,
    # )
    #
    # import json as _json
    # audit_logs = []
    # for log in raw_logs:
    #     try:
    #         diff = _json.loads(log.get("data") or "{{}}") or {{}}
    #     except Exception:
    #         diff = {{}}
    #     changed = diff.get("changed", [])
    #     log["action"]  = "Update" if changed else "Create"
    #     log["changes"] = [
    #         {{"field": c[0], "old": c[1], "new": c[2]}} for c in changed
    #     ] if changed else []
    #     audit_logs.append(log)
    #
    # context = {{
    #     "title":      "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "audit_logs": audit_logs,
    # }}
''',
        'notification_center': f'''
    # ════════════════════════════════════════════════════════════════════════
    # NOTIFICATION CENTER preset — Notification Log grouped by date
    # ════════════════════════════════════════════════════════════════════════
    # tab_filter = kwargs.get("tab", "all")   # all | unread | mentions | system | workflow
    # user = frappe.session.user
    #
    # filters = {{"for_user": user}}
    # if tab_filter == "unread":   filters["read"] = 0
    # if tab_filter == "mentions": filters["type"] = "Mention"
    # if tab_filter == "system":   filters["type"] = "Alert"
    # if tab_filter == "workflow": filters["type"] = "Workflow Action"
    #
    # notifs = frappe.get_all(
    #     "Notification Log",
    #     filters=filters,
    #     fields=["name", "subject", "type", "read AS is_read",
    #             "from_user", "creation", "document_type", "document_name"],
    #     order_by="creation desc", limit=60,
    # )
    #
    # from frappe.utils import pretty_date, getdate, today, add_days
    # from collections import OrderedDict
    # today_d = getdate(today())
    # yesterday_d = add_days(today_d, -1)
    #
    # groups = OrderedDict()
    # for n in notifs:
    #     d = getdate(n.creation)
    #     if d == today_d:          label = "Today"
    #     elif d == yesterday_d:    label = "Yesterday"
    #     else:                     label = "This Week"
    #     n["age"] = pretty_date(n.creation)
    #     groups.setdefault(label, []).append(n)
    #
    # notification_groups = [
    #     {{"date_label": lbl, "items": items}} for lbl, items in groups.items()
    # ]
    # unread_count = sum(1 for n in notifs if not n.is_read)
    #
    # context = {{
    #     "title":               "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "notification_groups": notification_groups,
    #     "unread_count":        unread_count,
    # }}
''',
        'bulk_ops': f'''
    # ════════════════════════════════════════════════════════════════════════
    # BULK OPS preset — load records + bulk action handler
    # ════════════════════════════════════════════════════════════════════════
    # doctype   = kwargs.get("doctype", "Sales Invoice")
    # status    = kwargs.get("status")
    # from_date = kwargs.get("from_date")
    # to_date   = kwargs.get("to_date")
    #
    # filters = {{"docstatus": ["!=", 2]}}
    # if status:    filters["status"]       = status
    # if from_date: filters["posting_date"] = [">=", from_date]
    # if to_date:   filters["posting_date"] = ["<=", to_date]
    #
    # records = frappe.get_all(
    #     doctype,
    #     filters=filters,
    #     fields=["name", "status", "owner", "creation", "grand_total"],
    #     order_by="creation desc", limit=200,
    # )
    # context = {{
    #     "title":   "{page_name.replace("-", " ").replace("_", " ").title()}",
    #     "records": records,
    # }}
    #
    # # --- Bulk action handler (separate whitelisted fn) ---
    # # @frappe.whitelist()
    # # def bulk_action_{page_name.replace("-","_")}(**kwargs):
    # #     names  = frappe.parse_json(kwargs.get("names", "[]"))
    # #     action = kwargs.get("action")   # approve | submit | cancel | delete | assign
    # #     results = {{"success": [], "failed": []}}
    # #     for name in names:
    # #         try:
    # #             doc = frappe.get_doc(doctype, name)
    # #             if action == "submit":  doc.submit()
    # #             elif action == "cancel": doc.cancel()
    # #             elif action == "delete": frappe.delete_doc(doctype, name)
    # #             results["success"].append(name)
    # #         except Exception as e:
    # #             results["failed"].append({{"name": name, "error": str(e)}})
    # #     frappe.db.commit()
    # #     return results
''',
    }
    block = _PRESET_BLOCKS.get(preset, '')
    if not block:
        return ''

    # Append universal extension guide to every preset block
    extension_guide = f'''
# ════════════════════════════════════════════════════════════════════════════
# HOW TO EXTEND THIS PRESET
# ════════════════════════════════════════════════════════════════════════════
# ── Add more data to context ───────────────────────────────────────────────
# Simply add more keys to the context dict and reference them in the template:
#   context["my_key"] = frappe.get_all("My DocType", ...)
#   context["site_name"] = frappe.local.site
#   context["user_roles"] = frappe.get_roles(frappe.session.user)
#   context["settings"] = frappe.get_single("My App Settings").as_dict()
#
# ── Add toolbar filters (pass from JS args) ────────────────────────────────
# In the JS frappe.call args: {{ company: "...", from_date: "...", status: "..." }}
# In Python: company = kwargs.get("company") or frappe.defaults.get_global_default("company")
#
# ── Add a real-time refresh ────────────────────────────────────────────────
# Python (call this from another handler to push data to all clients):
#   frappe.publish_realtime("{page_name}_refresh", {{"message": "Data updated"}},
#                           user=frappe.session.user)
# JavaScript (add inside bind_events):
#   frappe.realtime.on("{page_name}_refresh", () => load_data());
#
# ── Add a background job for heavy queries ─────────────────────────────────
# Python:
#   @frappe.whitelist()
#   def run_{page_name.replace("-","_")}_report(**kwargs):
#       frappe.enqueue("{{app}}.{{module}}.page.{page_name}.{page_name}.build_report",
#                      queue="long", job_id="{page_name}_report", **kwargs)
#       return {{"queued": True}}
#
# ── Export to CSV / Excel ──────────────────────────────────────────────────
# @frappe.whitelist()
# def export_{page_name.replace("-","_")}_data(**kwargs):
#     import csv
#     from io import StringIO
#     records = frappe.get_all("Sales Invoice", fields=["name","customer","grand_total"])
#     buf = StringIO()
#     w = csv.DictWriter(buf, fieldnames=["name","customer","grand_total"])
#     w.writeheader(); w.writerows([dict(r) for r in records])
#     frappe.response["filename"]     = "{page_name}_export.csv"
#     frappe.response["filecontent"]  = buf.getvalue()
#     frappe.response["type"]         = "download"
#     frappe.response["content_type"] = "text/csv"
#
# ── Cache expensive queries ────────────────────────────────────────────────
# Use caching to avoid hitting the DB on every page load:
#   cache_key = f"{page_name}_kpis_{{company}}_{{from_date}}"
#   cached = frappe.cache().get_value(cache_key)
#   if not cached:
#       cached = {{...}}  # your expensive query
#       frappe.cache().set_value(cache_key, cached, expires_in_sec=300)
#   context["kpis"] = cached
#
# ── Permission guard patterns ──────────────────────────────────────────────
#   frappe.only_for("System Manager")                           # single role guard
#   frappe.only_for(["System Manager", "Accounts Manager"])    # any of these roles
#   if not frappe.has_permission("Sales Invoice", "read"):
#       frappe.throw(_("Not permitted"), frappe.PermissionError)
#   if frappe.session.user == "Guest":
#       frappe.throw(_("Login required"), frappe.AuthenticationError)
# ════════════════════════════════════════════════════════════════════════════
'''
    return block + extension_guide


def _desk_py_preset_context_lines(preset):
    """Return extra lines to inject into the active context dict for presets that require
    specific variables in their Jinja template (beyond the generic 'title' key)."""
    _EXTRA = {
        'wizard': (
            '        "step": int(kwargs.get("step") or 1),\n'
            '        "data": frappe.parse_json(kwargs.get("data") or "{}"),\n'
        ),
    }
    return _EXTRA.get(preset, '')


def _desk_py_template(fn_name, tpl_path, app, module, page_name, preset='blank'):
    """Return rich commented Python boilerplate for a desk page."""
    title_str = page_name.replace("-", " ").replace("_", " ").title()
    return f'''import frappe
from frappe import _


# ════════════════════════════════════════════════════════════════════════════════
# {title_str} — Desk Page Backend
# ════════════════════════════════════════════════════════════════════════════════
# HOW THIS PAGE WORKS
# ─────────────────────────────────────────────────────────────────────────────
# 1. The JS file calls frappe.call({{ method: "...get_{fn_name}", args: {{...}} }})
# 2. This function builds a context dict from DB queries / business logic
# 3. frappe.render_template() renders the Jinja2 HTML template with that context
# 4. The rendered HTML string is returned to the JS, which sets page.main.html()
#
# HOW TO ADD A NEW DATA SOURCE
# ─────────────────────────────────────────────────────────────────────────────
# a) frappe.get_all()        — ORM-style: filters, fields, order_by, limit, group_by
# b) frappe.db.sql()         — Raw SQL for aggregations / complex JOINs
# c) frappe.db.get_value()   — Single field from a single document
# d) frappe.db.count()       — Count matching records quickly
# e) frappe.get_doc()        — Full document including child tables
#
# HOW TO EXTEND THIS PAGE
# ─────────────────────────────────────────────────────────────────────────────
# • Add new context keys here → reference them in templates/{page_name}.html
# • Add new @frappe.whitelist() functions below for AJAX actions (save, delete, export)
# • Add real-time updates: use frappe.publish_realtime() here + frappe.realtime in JS
# • Cache expensive queries: use frappe.cache().get_value() / set_value()
# ════════════════════════════════════════════════════════════════════════════════


@frappe.whitelist()
def get_{fn_name}(**kwargs):
    """Main data loader — called on every page load / filter change."""
    # All JS frappe.call({{args: {{...}}}}) kwargs arrive here.
    #
    # ── Permission guard (choose one) ────────────────────────────────────────────
    # frappe.only_for("System Manager")
    # frappe.only_for(["System Manager", "Accounts Manager"])
    # if not frappe.has_permission("Sales Invoice", "read"):
    #     frappe.throw(_("Not permitted"), frappe.PermissionError)
    #
    # ── Read filter args sent by the JS toolbar ───────────────────────────────────
    # company   = kwargs.get("company")   or frappe.defaults.get_global_default("company")
    # from_date = kwargs.get("from_date") or frappe.utils.add_months(frappe.utils.today(), -3)
    # to_date   = kwargs.get("to_date")   or frappe.utils.today()
    # status    = kwargs.get("status")    or ""
    # search    = kwargs.get("search")    or ""
    #
    # ── ORM list query ────────────────────────────────────────────────────────────
    # filters = {{"company": company, "docstatus": 1}}
    # if status:  filters["status"] = status
    # if search:  filters["name"]   = ["like", f"%{{search}}%"]
    # records = frappe.get_all(
    #     "Sales Invoice",
    #     filters=filters,
    #     fields=["name", "customer", "customer_name", "grand_total",
    #             "outstanding_amount", "posting_date", "status"],
    #     order_by="posting_date desc", limit=200,
    # )
    #
    # ── SQL aggregate ─────────────────────────────────────────────────────────────
    # totals = frappe.db.sql(
    #     "SELECT IFNULL(SUM(grand_total),0) AS total_invoiced,"
    #     "       IFNULL(SUM(outstanding_amount),0) AS total_outstanding,"
    #     "       COUNT(*) AS invoice_count, COUNT(DISTINCT customer) AS customer_count"
    #     " FROM `tabSales Invoice`"
    #     " WHERE docstatus=1 AND company=%(company)s"
    #     "   AND posting_date BETWEEN %(from_date)s AND %(to_date)s",
    #     {{"company": company, "from_date": from_date, "to_date": to_date}},
    #     as_dict=1,
    # )[0]
    #
    # ── KPI cards ─────────────────────────────────────────────────────────────────
    # kpis = [
    #     {{"label": "Total Invoiced", "value": frappe.utils.fmt_money(totals.total_invoiced),    "icon": "💰", "color": "#5c4da8"}},
    #     {{"label": "Outstanding",    "value": frappe.utils.fmt_money(totals.total_outstanding), "icon": "⏳", "color": "#dc2626"}},
    #     {{"label": "Invoices",       "value": totals.invoice_count,                             "icon": "📄", "color": "#0369a1"}},
    #     {{"label": "Customers",      "value": totals.customer_count,                            "icon": "👥", "color": "#059669"}},
    # ]
    #
    # ── Render template ───────────────────────────────────────────────────────────
    # html = frappe.render_template("{tpl_path}", {{
    #     "title":     "{title_str}",
    #     "records":   records,
    #     "totals":    totals,
    #     "kpis":      kpis,
    #     "from_date": from_date,
    #     "to_date":   to_date,
    #     "company":   company,
    # }})
    # return html
    # ─────────────────────────────────────────────────────────────────────────────
    context = {{
        "title": "{title_str}",
{_desk_py_preset_context_lines(preset)}    }}
    html = frappe.render_template("{tpl_path}", context)
    return html


# ── Additional whitelisted actions — add as many as you need ──────────────────

# @frappe.whitelist()
# def save_{fn_name}_record(**kwargs):
#     """Save or update a record from the page form."""
#     frappe.only_for("System Manager")
#     data = frappe.parse_json(kwargs.get("data") or "{{}}")
#     if kwargs.get("name"):
#         doc = frappe.get_doc("{title_str}", kwargs["name"])
#         doc.update(data)
#     else:
#         doc = frappe.get_doc({{"doctype": "{title_str}", **data}})
#     doc.save()
#     frappe.db.commit()
#     return {{"name": doc.name, "status": "ok"}}


# @frappe.whitelist()
# def delete_{fn_name}_record(name, **kwargs):
#     """Delete a record by name."""
#     frappe.only_for("System Manager")
#     frappe.delete_doc("{title_str}", name, force=1)
#     frappe.db.commit()
#     return {{"deleted": name}}


# @frappe.whitelist()
# def export_{fn_name}_csv(**kwargs):
#     """Export current data as CSV — called by an Export button in the JS."""
#     from io import StringIO
#     import csv
#     records = frappe.get_all("{title_str}", fields=["name", "status"])
#     buf = StringIO()
#     w = csv.DictWriter(buf, fieldnames=["name", "status"])
#     w.writeheader(); w.writerows([dict(r) for r in records])
#     frappe.response["filename"]     = "{page_name}_export.csv"
#     frappe.response["filecontent"]  = buf.getvalue()
#     frappe.response["type"]         = "download"
#     frappe.response["content_type"] = "text/csv"
''' + _desk_py_preset_block(preset, tpl_path, page_name)


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


def _desk_tpl_dashboard(cc, title):
    """Executive dashboard — KPI row + recent transactions + top customers + activity feed."""
    return r'''
<!-- ══ DASHBOARD DESK PRESET ════════════════════════════════════════════════
     Python context keys expected (all optional — page degrades gracefully):
       kpis          list[{label, value, sub, color, icon}]
       recent_rows   list[{name, party, date, amount, status}]
       top_parties   list[{name, total, count}]
       activity      list[{user, action, doctype, docname, age}]
     To populate from Python (in your .py file):
       import frappe, frappe.utils as fu
       kpis = [
           {"label":"Revenue (MTD)", "value": frappe.db.sql("SELECT IFNULL(SUM(grand_total),0) FROM `tabSales Invoice` WHERE docstatus=1 AND MONTH(posting_date)=MONTH(CURDATE()) AND YEAR(posting_date)=YEAR(CURDATE())")[0][0], "icon":"💰", "color":"#5c4da8"},
           {"label":"Expenses (MTD)", "value": frappe.db.sql("SELECT IFNULL(SUM(grand_total),0) FROM `tabPurchase Invoice` WHERE docstatus=1 AND MONTH(posting_date)=MONTH(CURDATE())")[0][0], "icon":"📤", "color":"#dc2626"},
           {"label":"Open Orders",    "value": frappe.db.count("Sales Order",    {"status": ["in",["To Deliver and Bill","To Bill"]]}), "icon":"📦", "color":"#0369a1"},
           {"label":"Open Issues",    "value": frappe.db.count("Issue",          {"status": "Open"}),                                  "icon":"🔔", "color":"#b45309"},
       ]
       recent_rows = frappe.get_all("Sales Invoice", filters={"docstatus":1}, fields=["name","customer as party","posting_date as date","grand_total as amount","status"], order_by="posting_date desc", limit=10)
       top_parties = frappe.db.sql("SELECT customer as name, SUM(grand_total) as total, COUNT(*) as count FROM `tabSales Invoice` WHERE docstatus=1 AND YEAR(posting_date)=YEAR(CURDATE()) GROUP BY customer ORDER BY total DESC LIMIT 8", as_dict=1)
       activity    = frappe.get_all("Activity Log", fields=["user","subject as action","reference_doctype as doctype","reference_name as docname","creation as age"], order_by="creation desc", limit=12)
       context.update({"kpis": kpis, "recent_rows": recent_rows, "top_parties": top_parties, "activity": activity})
════════════════════════════════════════════════════════════════════════════ -->
<style>
  :root {
    --dbd-brand:  #5c4da8; --dbd-light: #ede9fe; --dbd-muted: #6b7280;
    --dbd-dark:   #1e1b3a; --dbd-r: 10px; --dbd-sh: 0 2px 12px rgba(92,77,168,.10);
  }
  .dbd-wrap { padding: 2px 0; font-family: inherit; }
  /* KPI row */
  .dbd-kpi-row { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:14px; margin-bottom:22px; }
  .dbd-kpi { background:#fff; border-radius:var(--dbd-r); box-shadow:var(--dbd-sh); padding:18px 20px; border-left:4px solid var(--dbd-brand); display:flex; align-items:center; gap:14px; }
  .dbd-kpi-ico { font-size:2rem; }
  .dbd-kpi-val { font-size:1.7rem; font-weight:900; color:var(--dbd-brand); line-height:1; }
  .dbd-kpi-label { font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:var(--dbd-muted); margin-top:3px; }
  .dbd-kpi-sub { font-size:11px; color:var(--dbd-muted); margin-top:2px; }
  /* Two-column body */
  .dbd-body { display:grid; grid-template-columns:1fr 320px; gap:16px; margin-bottom:16px; }
  @media(max-width:900px){ .dbd-body { grid-template-columns:1fr; } }
  .dbd-card { background:#fff; border-radius:var(--dbd-r); box-shadow:var(--dbd-sh); overflow:hidden; }
  .dbd-card-hdr { padding:12px 16px; font-weight:700; font-size:13px; color:var(--dbd-dark); border-bottom:1px solid var(--dbd-light); display:flex; align-items:center; justify-content:space-between; }
  .dbd-card-hdr a { font-size:11px; font-weight:400; color:var(--dbd-brand); text-decoration:none; }
  /* Table */
  .dbd-tbl { width:100%; border-collapse:collapse; font-size:13px; }
  .dbd-tbl th { padding:9px 14px; background:var(--dbd-light); color:var(--dbd-brand); font-weight:700; text-align:left; font-size:11px; text-transform:uppercase; }
  .dbd-tbl td { padding:9px 14px; border-bottom:1px solid #f4f0fc; }
  .dbd-tbl tr:hover td { background:#faf7ff; cursor:pointer; }
  .dbd-tbl tr:last-child td { border:none; }
  /* Badges */
  .dbd-badge { display:inline-block; padding:2px 9px; border-radius:20px; font-size:10px; font-weight:700; }
  .dbd-badge.green{background:#dcfce7;color:#14532d} .dbd-badge.red{background:#fee2e2;color:#7f1d1d}
  .dbd-badge.blue{background:#dbeafe;color:#1e3a5f}  .dbd-badge.yellow{background:#fef9c3;color:#713f12}
  /* Top parties bar */
  .dbd-party-row { display:flex; align-items:center; gap:8px; padding:8px 14px; border-bottom:1px solid #f4f0fc; font-size:12px; }
  .dbd-party-row:last-child { border:none; }
  .dbd-party-name { flex:1; font-weight:600; color:var(--dbd-dark); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .dbd-party-bar-wrap { width:80px; background:#f0eaff; border-radius:4px; height:6px; overflow:hidden; }
  .dbd-party-bar { height:6px; background:var(--dbd-brand); border-radius:4px; }
  .dbd-party-total { font-weight:700; color:var(--dbd-brand); min-width:50px; text-align:right; font-size:11px; }
  /* Activity feed */
  .dbd-activity-row { display:flex; gap:10px; padding:8px 14px; border-bottom:1px solid #f4f0fc; font-size:12px; }
  .dbd-activity-row:last-child { border:none; }
  .dbd-av { width:26px; height:26px; border-radius:50%; background:var(--dbd-brand); color:#fff; font-size:10px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
  .dbd-activity-body { flex:1; }
  .dbd-activity-user { font-weight:600; color:var(--dbd-dark); }
  .dbd-activity-doc { color:var(--dbd-brand); }
  .dbd-activity-age { color:var(--dbd-muted); font-size:11px; }
</style>

<div class="dbd-wrap">

  {#- ══ KPI CARDS ══ -#}
  <div class="dbd-kpi-row">
    {% for kpi in kpis %}
    <div class="dbd-kpi" style="border-color:{{ kpi.color }}">
      <div class="dbd-kpi-ico">{{ kpi.icon }}</div>
      <div>
        <div class="dbd-kpi-val" style="color:{{ kpi.color }}">{{ kpi.value }}</div>
        <div class="dbd-kpi-label">{{ kpi.label }}</div>
        {% if kpi.sub %}<div class="dbd-kpi-sub">{{ kpi.sub }}</div>{% endif %}
      </div>
    </div>
    {% else %}
    {#- Placeholder when no kpis passed from Python -#}
    {% for ph in [["💰","Revenue","#5c4da8"],["📤","Expenses","#dc2626"],["📦","Open Orders","#0369a1"],["🔔","Open Issues","#b45309"]] %}
    <div class="dbd-kpi" style="border-color:{{ ph[2] }}">
      <div class="dbd-kpi-ico">{{ ph[0] }}</div>
      <div><div class="dbd-kpi-val" style="color:{{ ph[2] }}">—</div><div class="dbd-kpi-label">{{ ph[1] }}</div></div>
    </div>
    {% endfor %}
    {% endfor %}
  </div>

  {#- ══ BODY: RECENT INVOICES + TOP CUSTOMERS ══ -#}
  <div class="dbd-body">

    {#- Recent transactions -#}
    <div class="dbd-card">
      <div class="dbd-card-hdr">
        Recent Transactions
        <a href="/app/sales-invoice">View all →</a>
      </div>
      <table class="dbd-tbl">
        <thead><tr><th>Invoice</th><th>Customer</th><th>Date</th><th>Amount</th><th>Status</th></tr></thead>
        <tbody>
          {% for row in recent_rows %}
          <tr onclick="frappe.set_route('Form','Sales Invoice','{{ row.name }}')">
            <td><strong>{{ row.name }}</strong></td>
            <td>{{ row.party }}</td>
            <td>{{ row.date }}</td>
            <td>{{ frappe.format_value(row.amount, {"fieldtype":"Currency"}) }}</td>
            <td><span class="dbd-badge {% if row.status=='Paid' %}green{% elif row.status=='Overdue' %}red{% elif row.status=='Unpaid' %}yellow{% else %}blue{% endif %}">{{ row.status }}</span></td>
          </tr>
          {% else %}
          <tr><td colspan="5" style="text-align:center;padding:24px;color:var(--dbd-muted)">No invoices yet.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    {#- Right column: top parties + activity -#}
    <div style="display:flex;flex-direction:column;gap:16px">
      <div class="dbd-card">
        <div class="dbd-card-hdr">Top Customers (YTD)</div>
        {% for p in top_parties %}
        {% set pct = [(p.total / top_parties[0].total * 100)|int, 4]|max %}
        <div class="dbd-party-row">
          <div class="dbd-party-name">{{ p.name }}</div>
          <div class="dbd-party-bar-wrap"><div class="dbd-party-bar" style="width:{{ pct }}%"></div></div>
          <div class="dbd-party-total">{{ p.count }} inv</div>
        </div>
        {% else %}
        <p style="padding:16px;color:var(--dbd-muted);font-size:12px">No data yet.</p>
        {% endfor %}
      </div>
      <div class="dbd-card">
        <div class="dbd-card-hdr">Recent Activity</div>
        {% for a in activity %}
        <div class="dbd-activity-row">
          <div class="dbd-av">{{ (a.user or "?")[0]|upper }}</div>
          <div class="dbd-activity-body">
            <span class="dbd-activity-user">{{ a.user }}</span>
            {{ a.action }}
            <a class="dbd-activity-doc" href="/app/{{ a.doctype|lower|replace(' ','-') }}/{{ a.docname }}">{{ a.docname }}</a>
            <div class="dbd-activity-age">{{ a.age }}</div>
          </div>
        </div>
        {% else %}
        <p style="padding:16px;color:var(--dbd-muted);font-size:12px">No activity yet.</p>
        {% endfor %}
      </div>
    </div>

  </div>{#- /dbd-body -#}

</div>{#- /dbd-wrap -#}
'''


def _desk_tpl_list_tool(cc, title):
    """Filterable list — search + filters + sortable table + pagination + bulk actions."""
    return r'''
<!-- ══ LIST TOOL DESK PRESET ════════════════════════════════════════════════
     Python context keys expected:
       records   list[{name, party, date, amount, status, owner}]
       total     int   — total count before pagination
       page      int   — current page (1-based)
       per_page  int   — page size
       statuses  list[str] — available status values for filter dropdown
     Example Python (in your .py file):
       page     = int(kwargs.get("page") or 1)
       per_page = int(kwargs.get("per_page") or 25)
       filters  = {}
       if kwargs.get("status"): filters["status"] = kwargs["status"]
       if kwargs.get("q"):      filters["name"]   = ["like", f"%{kwargs['q']}%"]
       total   = frappe.db.count("Sales Invoice", filters)
       records = frappe.get_all("Sales Invoice", filters=filters,
                   fields=["name","customer as party","posting_date as date","grand_total as amount","status","owner"],
                   order_by=kwargs.get("order_by","posting_date desc"),
                   limit=per_page, start=(page-1)*per_page)
       context.update({"records":records,"total":total,"page":page,"per_page":per_page})
════════════════════════════════════════════════════════════════════════════ -->
<style>
  .lt-wrap { font-family:inherit; padding:2px 0; }
  /* Toolbar */
  .lt-toolbar { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:14px; background:#fff; padding:10px 14px; border-radius:8px; box-shadow:0 1px 6px rgba(92,77,168,.08); }
  .lt-search { flex:1; min-width:180px; display:flex; align-items:center; gap:6px; background:#f7f5fc; border:1px solid #e0d4fc; border-radius:20px; padding:5px 12px; }
  .lt-search input { border:none; background:transparent; outline:none; font-size:13px; width:100%; }
  .lt-select { border:1px solid #e0d4fc; border-radius:6px; padding:5px 10px; font-size:12px; background:#faf8ff; color:#3a2e5e; outline:none; cursor:pointer; }
  .lt-btn { padding:6px 14px; border-radius:6px; border:none; cursor:pointer; font-size:12px; font-weight:600; }
  .lt-btn-primary { background:#5c4da8; color:#fff; }
  .lt-btn-primary:hover { background:#4a3d8f; }
  .lt-btn-ghost { background:#f0eaff; color:#5c4da8; border:1px solid #d4bcfc; }
  /* Bulk bar */
  .lt-bulk-bar { display:none; background:#5c4da8; color:#fff; padding:8px 14px; border-radius:8px; margin-bottom:10px; align-items:center; gap:12px; font-size:13px; }
  .lt-bulk-bar.visible { display:flex; }
  .lt-bulk-btn { padding:4px 12px; border-radius:6px; border:none; cursor:pointer; font-size:12px; font-weight:600; background:rgba(255,255,255,.15); color:#fff; }
  .lt-bulk-btn:hover { background:rgba(255,255,255,.25); }
  .lt-bulk-btn.danger { background:rgba(220,38,38,.3); }
  /* Table */
  .lt-card { background:#fff; border-radius:10px; box-shadow:0 2px 12px rgba(92,77,168,.10); overflow:hidden; }
  .lt-tbl { width:100%; border-collapse:collapse; font-size:13px; }
  .lt-tbl thead th { background:#ede9fe; color:#5c4da8; padding:10px 14px; text-align:left; font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:.06em; white-space:nowrap; }
  .lt-tbl thead th.sortable { cursor:pointer; user-select:none; }
  .lt-tbl thead th.sortable:hover { background:#e0d4fc; }
  .lt-tbl tbody tr:hover td { background:#faf7ff; }
  .lt-tbl tbody td { padding:9px 14px; border-bottom:1px solid #f3f0fc; vertical-align:middle; }
  .lt-tbl tbody tr:last-child td { border:none; }
  .lt-cb { accent-color:#5c4da8; width:14px; height:14px; cursor:pointer; }
  .lt-link { color:#5c4da8; font-weight:600; text-decoration:none; }
  .lt-link:hover { text-decoration:underline; }
  /* Badges */
  .lt-badge { display:inline-block; padding:2px 9px; border-radius:20px; font-size:10px; font-weight:700; }
  .lt-badge.green{background:#dcfce7;color:#14532d} .lt-badge.red{background:#fee2e2;color:#7f1d1d}
  .lt-badge.blue{background:#dbeafe;color:#1e3a5f}  .lt-badge.yellow{background:#fef9c3;color:#713f12}
  .lt-badge.purple{background:#ede9fe;color:#5c4da8}
  /* Row actions */
  .lt-actions { display:flex; gap:6px; opacity:0; transition:opacity .15s; }
  .lt-tbl tbody tr:hover .lt-actions { opacity:1; }
  .lt-act-btn { padding:3px 8px; border-radius:5px; border:none; cursor:pointer; font-size:11px; font-weight:600; }
  .lt-act-edit { background:#ede9fe; color:#5c4da8; }
  .lt-act-del  { background:#fee2e2; color:#dc2626; }
  /* Pagination */
  .lt-paginate { display:flex; align-items:center; justify-content:space-between; padding:10px 14px; border-top:1px solid #f0eaff; font-size:12px; color:#6b7280; }
  .lt-page-btns { display:flex; gap:4px; }
  .lt-page-btn { padding:4px 10px; border-radius:5px; border:1px solid #e0d4fc; background:#fff; cursor:pointer; font-size:12px; color:#5c4da8; }
  .lt-page-btn:hover { background:#f0eaff; }
  .lt-page-btn.active { background:#5c4da8; color:#fff; border-color:#5c4da8; }
  /* Empty state */
  .lt-empty { text-align:center; padding:50px 20px; color:#9080b8; }
  .lt-empty .lt-empty-ico { font-size:3rem; margin-bottom:10px; }
</style>

<div class="lt-wrap">
  {#- ── Toolbar ── -#}
  <div class="lt-toolbar">
    <div class="lt-search">
      <span>🔍</span>
      <input type="text" id="lt-q" placeholder="Search by name, party…" value="{{ search or '' }}">
    </div>
    <select class="lt-select" id="lt-status">
      <option value="">All Statuses</option>
      {% for s in statuses %}
      <option value="{{ s }}" {% if status==s %}selected{% endif %}>{{ s }}</option>
      {% endfor %}
    </select>
    <select class="lt-select" id="lt-order">
      <option value="posting_date desc">Newest first</option>
      <option value="posting_date asc">Oldest first</option>
      <option value="grand_total desc">Highest amount</option>
      <option value="name asc">Name A→Z</option>
    </select>
    <button class="lt-btn lt-btn-ghost" onclick="lt_export()">⬇ Export</button>
    <button class="lt-btn lt-btn-primary" onclick="frappe.new_doc('Sales Invoice')">+ New</button>
  </div>

  {#- ── Bulk action bar (shown when rows selected) ── -#}
  <div class="lt-bulk-bar" id="lt-bulk-bar">
    <strong id="lt-bulk-count">0 selected</strong>
    <button class="lt-bulk-btn" onclick="lt_bulk_assign()">👤 Assign</button>
    <button class="lt-bulk-btn" onclick="lt_bulk_export()">⬇ Export</button>
    <button class="lt-bulk-btn danger" onclick="lt_bulk_delete()">🗑 Delete</button>
    <span style="flex:1"></span>
    <button class="lt-bulk-btn" onclick="lt_clear_selection()">✕ Clear</button>
  </div>

  {#- ── Table ── -#}
  <div class="lt-card">
    <table class="lt-tbl">
      <thead>
        <tr>
          <th><input type="checkbox" class="lt-cb" id="lt-select-all" title="Select all"></th>
          <th class="sortable">Name ↕</th>
          <th class="sortable">Party ↕</th>
          <th class="sortable">Date ↕</th>
          <th class="sortable">Amount ↕</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for row in records %}
        <tr>
          <td><input type="checkbox" class="lt-cb lt-row-cb" data-name="{{ row.name }}"></td>
          <td><a class="lt-link" href="/app/sales-invoice/{{ row.name }}">{{ row.name }}</a></td>
          <td>{{ row.party }}</td>
          <td>{{ row.date }}</td>
          <td><strong>{{ frappe.format_value(row.amount, {"fieldtype":"Currency"}) }}</strong></td>
          <td>
            <span class="lt-badge {% if row.status in ['Paid','Submitted'] %}green{% elif row.status in ['Overdue','Cancelled'] %}red{% elif row.status=='Unpaid' %}yellow{% else %}blue{% endif %}">
              {{ row.status }}
            </span>
          </td>
          <td>
            <div class="lt-actions">
              <button class="lt-act-btn lt-act-edit" onclick="frappe.set_route('Form','Sales Invoice','{{ row.name }}')">Edit</button>
              <button class="lt-act-btn lt-act-del"  onclick="lt_delete_row('{{ row.name }}')">Del</button>
            </div>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="7"><div class="lt-empty"><div class="lt-empty-ico">🗂️</div><p>No records match your filters.</p></div></td></tr>
        {% endfor %}
      </tbody>
    </table>
    {#- ── Pagination ── -#}
    {% if total %}
    <div class="lt-paginate">
      <span>Showing {{ ((page-1)*per_page)+1 }}–{{ [page*per_page, total]|min }} of {{ total }}</span>
      <div class="lt-page-btns">
        {% if page > 1 %}<button class="lt-page-btn" onclick="lt_goto({{ page-1 }})">← Prev</button>{% endif %}
        {% for p in range([page-2,1]|max, [page+3, (total//per_page)+2]|min) %}
        <button class="lt-page-btn {% if p==page %}active{% endif %}" onclick="lt_goto({{ p }})">{{ p }}</button>
        {% endfor %}
        {% if page*per_page < total %}<button class="lt-page-btn" onclick="lt_goto({{ page+1 }})">Next →</button>{% endif %}
      </div>
    </div>
    {% endif %}
  </div>
</div>

<script>
/* ── List Tool interactions ──────────────────────────────────────────────── */
// Reload page with updated args via frappe.call
function lt_reload(extra) {
    var args = Object.assign({ q: $("#lt-q").val(), status: $("#lt-status").val(), order_by: $("#lt-order").val() }, extra || {});
    frappe.call({ method: window._lt_method, args: args, callback: r => { if (r.message) $(page.main).html(r.message); } });
}
function lt_goto(p) { lt_reload({ page: p }); }

// Checkbox handling
$(document).on("change", "#lt-select-all", function() {
    $(".lt-row-cb").prop("checked", this.checked);
    lt_update_bulk_bar();
});
$(document).on("change", ".lt-row-cb", function() { lt_update_bulk_bar(); });
function lt_update_bulk_bar() {
    var sel = $(".lt-row-cb:checked").length;
    if (sel > 0) { $("#lt-bulk-count").text(sel + " selected"); $("#lt-bulk-bar").addClass("visible"); }
    else         { $("#lt-bulk-bar").removeClass("visible"); }
}
function lt_clear_selection() { $(".lt-row-cb, #lt-select-all").prop("checked", false); lt_update_bulk_bar(); }
function lt_selected_names() { return $(".lt-row-cb:checked").map((i,el) => $(el).data("name")).get(); }

// Bulk actions
function lt_bulk_delete() {
    var names = lt_selected_names();
    if (!names.length) return;
    frappe.confirm("Delete " + names.length + " record(s)?", function() {
        frappe.call({ method: "frappe.client.delete_bulk",
                      args: { doctype: "Sales Invoice", names: names },
                      callback: () => { frappe.show_alert("Deleted", "green"); lt_reload(); } });
    });
}
function lt_bulk_assign() {
    // frappe.prompt({label:"Assign To", fieldtype:"Link", options:"User"}, v => { /* frappe.call assign */ });
    frappe.show_alert("Assign dialog — implement with frappe.prompt", "blue");
}
function lt_bulk_export() { frappe.show_alert("Export — implement with frappe.call + download", "blue"); }
function lt_export()      { frappe.show_alert("Export all — implement with frappe.call + download", "blue"); }
function lt_delete_row(name) {
    frappe.confirm("Delete " + name + "?", function() {
        frappe.call({ method:"frappe.client.delete", args:{doctype:"Sales Invoice",name:name}, callback:() => lt_reload() });
    });
}
// Search on Enter
$(document).on("keydown","#lt-q", function(e) { if (e.key==="Enter") lt_reload({page:1}); });
$(document).on("change","#lt-status,#lt-order", function() { lt_reload({page:1}); });
</script>
'''


def _desk_tpl_form_tool(cc, title):
    """Multi-section input form — 3 collapsible sections, validation, save/cancel."""
    return r'''
<!-- ══ FORM TOOL DESK PRESET ════════════════════════════════════════════════
     Python context keys expected (for edit/load mode):
       doc       dict   — existing document fields (empty dict for new)
       customers list   — [{"name","customer_name"}] for Customer link dropdown
       mode      str    — "new" | "edit"
     Example Python load:
       name = kwargs.get("name")
       if name:
           doc = frappe.get_doc("Sales Order", name).as_dict()
           mode = "edit"
       else:
           doc = {}; mode = "new"
       customers = frappe.get_all("Customer", fields=["name","customer_name"], limit=200)
       context.update({"doc":doc, "mode":mode, "customers":customers})
     Example Python save (separate whitelisted method):
       @frappe.whitelist()
       def save_form(**kwargs):
           doc = frappe.get_doc({"doctype":"Sales Order", **kwargs})
           doc.insert(ignore_permissions=False)
           return {"status":"ok", "name": doc.name}
════════════════════════════════════════════════════════════════════════════ -->
<style>
  .ft-wrap { max-width:860px; margin:0 auto; font-family:inherit; padding:4px 0; }
  .ft-banner { display:none; padding:10px 16px; border-radius:8px; margin-bottom:14px; font-size:13px; font-weight:600; }
  .ft-banner.success { background:#dcfce7; color:#14532d; border:1px solid #bbf7d0; }
  .ft-banner.error   { background:#fee2e2; color:#7f1d1d; border:1px solid #fca5a5; }
  /* Section */
  .ft-section { background:#fff; border-radius:10px; box-shadow:0 2px 10px rgba(92,77,168,.08); margin-bottom:14px; overflow:hidden; }
  .ft-section-hdr { display:flex; align-items:center; justify-content:space-between; padding:12px 18px; cursor:pointer; border-bottom:1px solid #f0eaff; }
  .ft-section-hdr:hover { background:#faf7ff; }
  .ft-section-title { font-weight:700; font-size:13px; color:#1e1b3a; display:flex; align-items:center; gap:8px; }
  .ft-section-chevron { color:#9080b8; font-size:12px; transition:transform .2s; }
  .ft-section.collapsed .ft-section-chevron { transform:rotate(-90deg); }
  .ft-section-body { padding:18px; }
  .ft-section.collapsed .ft-section-body { display:none; }
  /* Fields */
  .ft-field-row { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px; }
  .ft-field-row.full { grid-template-columns:1fr; }
  .ft-field { display:flex; flex-direction:column; gap:4px; }
  .ft-label { font-size:12px; font-weight:600; color:#3a2e5e; }
  .ft-label .req { color:#dc2626; margin-left:2px; }
  .ft-input, .ft-select, .ft-textarea { border:1px solid #e0d4fc; border-radius:6px; padding:7px 10px; font-size:13px; outline:none; background:#faf8ff; transition:border-color .15s; width:100%; box-sizing:border-box; }
  .ft-input:focus, .ft-select:focus, .ft-textarea:focus { border-color:#7c3aed; box-shadow:0 0 0 3px rgba(124,58,237,.1); }
  .ft-input.invalid { border-color:#dc2626; background:#fff5f5; }
  .ft-err { font-size:11px; color:#dc2626; min-height:14px; }
  .ft-textarea { min-height:90px; resize:vertical; }
  /* File upload */
  .ft-upload-zone { border:2px dashed #d4bcfc; border-radius:8px; padding:20px; text-align:center; cursor:pointer; transition:background .15s; }
  .ft-upload-zone:hover { background:#f5f0ff; }
  .ft-upload-zone p { color:#9080b8; font-size:12px; margin:4px 0; }
  /* Footer */
  .ft-footer { display:flex; align-items:center; gap:10px; padding:14px 18px; background:#fff; border-radius:10px; box-shadow:0 2px 10px rgba(92,77,168,.08); }
  .ft-save-btn { padding:9px 24px; background:#5c4da8; color:#fff; border:none; border-radius:7px; font-size:13px; font-weight:700; cursor:pointer; }
  .ft-save-btn:hover { background:#4a3d8f; }
  .ft-save-btn:disabled { opacity:.5; cursor:not-allowed; }
  .ft-cancel-btn { padding:9px 18px; background:#f0eaff; color:#5c4da8; border:1px solid #d4bcfc; border-radius:7px; font-size:13px; font-weight:600; cursor:pointer; }
  .ft-reset-btn  { padding:9px 18px; background:#fff; color:#9080b8; border:1px solid #e0d4fc; border-radius:7px; font-size:13px; cursor:pointer; }
  .ft-mode-badge { margin-left:auto; font-size:11px; padding:3px 10px; border-radius:20px; background:#dbeafe; color:#1e3a5f; font-weight:700; }
</style>

<div class="ft-wrap">
  <div class="ft-banner" id="ft-banner"></div>

  {#- ── Section 1: Basic Information ── -#}
  <div class="ft-section" id="ft-sec-basic">
    <div class="ft-section-hdr" onclick="ft_toggle('ft-sec-basic')">
      <div class="ft-section-title">📋 Basic Information</div>
      <div class="ft-section-chevron">▼</div>
    </div>
    <div class="ft-section-body">
      <div class="ft-field-row">
        <div class="ft-field">
          <label class="ft-label">Title / Name <span class="req">*</span></label>
          <input class="ft-input" id="ft-title" type="text" value="{{ doc.title or '' }}" placeholder="Enter document title">
          <div class="ft-err" id="ft-title-err"></div>
        </div>
        <div class="ft-field">
          <label class="ft-label">Customer <span class="req">*</span></label>
          <select class="ft-select" id="ft-customer">
            <option value="">— Select Customer —</option>
            {% for c in customers %}
            <option value="{{ c.name }}" {% if doc.customer==c.name %}selected{% endif %}>{{ c.customer_name or c.name }}</option>
            {% endfor %}
          </select>
          <div class="ft-err" id="ft-customer-err"></div>
        </div>
      </div>
      <div class="ft-field-row">
        <div class="ft-field">
          <label class="ft-label">Date <span class="req">*</span></label>
          <input class="ft-input" id="ft-date" type="date" value="{{ doc.transaction_date or '' }}">
          <div class="ft-err" id="ft-date-err"></div>
        </div>
        <div class="ft-field">
          <label class="ft-label">Priority</label>
          <select class="ft-select" id="ft-priority">
            {% for p in ["Low","Medium","High","Urgent"] %}
            <option value="{{ p }}" {% if doc.priority==p %}selected{% endif %}>{{ p }}</option>
            {% endfor %}
          </select>
        </div>
      </div>
      <div class="ft-field-row">
        <div class="ft-field">
          <label class="ft-label">Amount</label>
          <input class="ft-input" id="ft-amount" type="number" step="0.01" value="{{ doc.grand_total or '' }}" placeholder="0.00">
        </div>
        <div class="ft-field">
          <label class="ft-label">Currency</label>
          <select class="ft-select" id="ft-currency">
            {% for cur in ["USD","EUR","GBP","INR","AED","SAR"] %}
            <option value="{{ cur }}" {% if doc.currency==cur %}selected{% endif %}>{{ cur }}</option>
            {% endfor %}
          </select>
        </div>
      </div>
    </div>
  </div>

  {#- ── Section 2: Address & Contact ── -#}
  <div class="ft-section" id="ft-sec-addr">
    <div class="ft-section-hdr" onclick="ft_toggle('ft-sec-addr')">
      <div class="ft-section-title">📍 Address &amp; Contact</div>
      <div class="ft-section-chevron">▼</div>
    </div>
    <div class="ft-section-body">
      <div class="ft-field-row full">
        <div class="ft-field">
          <label class="ft-label">Street Address</label>
          <input class="ft-input" id="ft-address" type="text" value="{{ doc.address_line1 or '' }}" placeholder="123 Main Street">
        </div>
      </div>
      <div class="ft-field-row">
        <div class="ft-field">
          <label class="ft-label">City</label>
          <input class="ft-input" id="ft-city" type="text" value="{{ doc.city or '' }}">
        </div>
        <div class="ft-field">
          <label class="ft-label">Country</label>
          <input class="ft-input" id="ft-country" type="text" value="{{ doc.country or '' }}" placeholder="United States">
        </div>
      </div>
      <div class="ft-field-row">
        <div class="ft-field">
          <label class="ft-label">Phone</label>
          <input class="ft-input" id="ft-phone" type="tel" value="{{ doc.phone or '' }}">
        </div>
        <div class="ft-field">
          <label class="ft-label">Email</label>
          <input class="ft-input" id="ft-email" type="email" value="{{ doc.email_id or '' }}">
        </div>
      </div>
    </div>
  </div>

  {#- ── Section 3: Notes & Attachments ── -#}
  <div class="ft-section" id="ft-sec-notes">
    <div class="ft-section-hdr" onclick="ft_toggle('ft-sec-notes')">
      <div class="ft-section-title">📝 Notes &amp; Attachments</div>
      <div class="ft-section-chevron">▼</div>
    </div>
    <div class="ft-section-body">
      <div class="ft-field">
        <label class="ft-label">Internal Notes</label>
        <textarea class="ft-textarea" id="ft-notes" placeholder="Add any internal notes, instructions or context…">{{ doc.notes or '' }}</textarea>
      </div>
      <div style="margin-top:14px">
        <label class="ft-label">Attachments</label>
        <div class="ft-upload-zone" onclick="document.getElementById('ft-file').click()">
          <div style="font-size:2rem">📎</div>
          <p><strong>Click to upload</strong> or drag &amp; drop</p>
          <p>PDF, Excel, images — max 10 MB</p>
          <input type="file" id="ft-file" style="display:none" multiple>
        </div>
      </div>
    </div>
  </div>

  {#- ── Footer ── -#}
  <div class="ft-footer">
    <button class="ft-save-btn" id="ft-save-btn" onclick="ft_save()">💾 Save</button>
    <button class="ft-cancel-btn" onclick="history.back()">Cancel</button>
    <button class="ft-reset-btn" onclick="ft_reset()">↺ Reset</button>
    {% if mode %}
    <span class="ft-mode-badge">{{ mode|upper }}</span>
    {% endif %}
  </div>
</div>

<script>
/* ── Form Tool interactions ──────────────────────────────────────────────── */
function ft_toggle(id) {
    var sec = document.getElementById(id);
    sec.classList.toggle("collapsed");
}
function ft_show_banner(msg, type) {
    var el = document.getElementById("ft-banner");
    el.textContent = msg; el.className = "ft-banner " + type; el.style.display = "block";
    setTimeout(function(){ el.style.display = "none"; }, 5000);
}
function ft_reset() { document.querySelectorAll(".ft-input,.ft-textarea").forEach(el => el.value = ""); }
function ft_validate() {
    var ok = true;
    function check(id, errId, msg) {
        var val = document.getElementById(id).value.trim();
        document.getElementById(errId).textContent = val ? "" : msg;
        if (!val) { document.getElementById(id).classList.add("invalid"); ok = false; }
        else       document.getElementById(id).classList.remove("invalid");
    }
    check("ft-title",    "ft-title-err",    "Title is required");
    check("ft-customer", "ft-customer-err", "Customer is required");
    check("ft-date",     "ft-date-err",     "Date is required");
    return ok;
}
function ft_save() {
    if (!ft_validate()) return;
    var btn = document.getElementById("ft-save-btn");
    btn.disabled = true; btn.textContent = "Saving…";
    var data = {
        title:     document.getElementById("ft-title").value,
        customer:  document.getElementById("ft-customer").value,
        date:      document.getElementById("ft-date").value,
        priority:  document.getElementById("ft-priority").value,
        amount:    document.getElementById("ft-amount").value,
        currency:  document.getElementById("ft-currency").value,
        address:   document.getElementById("ft-address").value,
        city:      document.getElementById("ft-city").value,
        country:   document.getElementById("ft-country").value,
        phone:     document.getElementById("ft-phone").value,
        email:     document.getElementById("ft-email").value,
        notes:     document.getElementById("ft-notes").value,
    };
    frappe.call({
        method: window._ft_save_method || "frappe_devkit.api.page_builder.create_desk_page",
        // Replace with your actual save method: e.g. "my_app.my_module.page.my_page.my_page.save_form"
        args: data,
        callback: function(r) {
            btn.disabled = false; btn.textContent = "💾 Save";
            if (r.message && r.message.status === "ok") {
                ft_show_banner("✅ Saved successfully — " + (r.message.name || ""), "success");
            } else {
                ft_show_banner("❌ Save failed — check the console for details.", "error");
            }
        },
        error: function() { btn.disabled = false; btn.textContent = "💾 Save"; ft_show_banner("❌ Server error", "error"); }
    });
}
</script>
'''


def _desk_tpl_analytics(cc, title):
    """Analytics page — filters + 4 KPI tiles + 2 Chart.js areas + summary table."""
    return r'''
<!-- ══ ANALYTICS DESK PRESET ════════════════════════════════════════════════
     Python context keys expected:
       metrics      {revenue, cost, profit, margin_pct}
       trend_labels list[str]   — month labels ["Jan","Feb",...]
       trend_data   list[float] — revenue per month
       cost_data    list[float] — cost per month
       top_customers list[{name, revenue, pct}]
       summary_rows  list[{category, revenue, cost, profit, count}]
     Example Python:
       from_date = kwargs.get("from_date") or frappe.utils.add_months(frappe.utils.today(), -6)
       to_date   = kwargs.get("to_date")   or frappe.utils.today()
       rev = frappe.db.sql("SELECT IFNULL(SUM(grand_total),0) FROM `tabSales Invoice` WHERE docstatus=1 AND posting_date BETWEEN %(f)s AND %(t)s", {"f":from_date,"t":to_date})[0][0]
       cost= frappe.db.sql("SELECT IFNULL(SUM(grand_total),0) FROM `tabPurchase Invoice` WHERE docstatus=1 AND posting_date BETWEEN %(f)s AND %(t)s", {"f":from_date,"t":to_date})[0][0]
       trend = frappe.db.sql("SELECT DATE_FORMAT(posting_date,'%%b %%Y') as lbl, SUM(grand_total) as rev FROM `tabSales Invoice` WHERE docstatus=1 AND posting_date BETWEEN %(f)s AND %(t)s GROUP BY lbl ORDER BY MIN(posting_date)", {"f":from_date,"t":to_date}, as_dict=1)
       top   = frappe.db.sql("SELECT customer as name, SUM(grand_total) as revenue FROM `tabSales Invoice` WHERE docstatus=1 AND posting_date BETWEEN %(f)s AND %(t)s GROUP BY customer ORDER BY revenue DESC LIMIT 10", {"f":from_date,"t":to_date}, as_dict=1)
       profit = rev - cost
       context.update({"metrics":{"revenue":rev,"cost":cost,"profit":profit,"margin_pct":round(profit/rev*100,1) if rev else 0}, "trend_labels":[r.lbl for r in trend], "trend_data":[r.rev for r in trend], "cost_data":[], "top_customers":top, "summary_rows":[]})
════════════════════════════════════════════════════════════════════════════ -->
<style>
  .an-wrap { font-family:inherit; padding:2px 0; }
  /* Filter bar */
  .an-filters { display:flex; gap:10px; align-items:flex-end; flex-wrap:wrap; background:#fff; padding:12px 16px; border-radius:10px; box-shadow:0 1px 8px rgba(92,77,168,.08); margin-bottom:18px; }
  .an-fld { display:flex; flex-direction:column; gap:3px; }
  .an-fld label { font-size:11px; font-weight:600; color:#5c4da8; text-transform:uppercase; letter-spacing:.05em; }
  .an-fld input, .an-fld select { border:1px solid #e0d4fc; border-radius:6px; padding:6px 10px; font-size:12px; background:#faf8ff; outline:none; }
  .an-fld input:focus, .an-fld select:focus { border-color:#7c3aed; }
  .an-apply { padding:8px 18px; background:#5c4da8; color:#fff; border:none; border-radius:7px; font-size:12px; font-weight:700; cursor:pointer; margin-top:auto; }
  .an-apply:hover { background:#4a3d8f; }
  /* KPI tiles */
  .an-kpi-row { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:18px; }
  @media(max-width:800px){ .an-kpi-row { grid-template-columns:1fr 1fr; } }
  .an-kpi { background:#fff; border-radius:10px; box-shadow:0 2px 10px rgba(92,77,168,.08); padding:16px 18px; border-top:3px solid #5c4da8; }
  .an-kpi-val { font-size:1.6rem; font-weight:900; color:#1e1b3a; }
  .an-kpi-lbl { font-size:11px; text-transform:uppercase; color:#6b7280; letter-spacing:.06em; margin-top:4px; }
  .an-kpi-trend { font-size:12px; margin-top:4px; }
  .an-kpi-trend.up { color:#14532d; } .an-kpi-trend.down { color:#7f1d1d; }
  /* Charts row */
  .an-charts-row { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:18px; }
  @media(max-width:700px){ .an-charts-row { grid-template-columns:1fr; } }
  .an-card { background:#fff; border-radius:10px; box-shadow:0 2px 10px rgba(92,77,168,.08); overflow:hidden; }
  .an-card-hdr { padding:12px 16px; font-weight:700; font-size:13px; color:#1e1b3a; border-bottom:1px solid #f0eaff; }
  .an-chart-area { padding:16px; height:220px; display:flex; align-items:center; justify-content:center; }
  .an-chart-placeholder { text-align:center; color:#9080b8; font-size:12px; }
  /* Summary table */
  .an-tbl { width:100%; border-collapse:collapse; font-size:13px; }
  .an-tbl th { background:#ede9fe; color:#5c4da8; padding:9px 14px; text-align:left; font-size:11px; text-transform:uppercase; font-weight:700; }
  .an-tbl td { padding:9px 14px; border-bottom:1px solid #f3f0fc; }
  .an-tbl tr:last-child td { border:none; }
  .an-tbl tr:hover td { background:#faf7ff; }
  .an-bar-mini { display:inline-block; height:6px; border-radius:3px; background:#5c4da8; vertical-align:middle; margin-left:6px; }
  .an-profit-pos { color:#14532d; font-weight:700; }
  .an-profit-neg { color:#7f1d1d; font-weight:700; }
</style>

<div class="an-wrap">
  {#- ── Filter bar ── -#}
  <div class="an-filters">
    <div class="an-fld">
      <label>From Date</label>
      <input type="date" id="an-from" value="{{ from_date or '' }}">
    </div>
    <div class="an-fld">
      <label>To Date</label>
      <input type="date" id="an-to" value="{{ to_date or '' }}">
    </div>
    <div class="an-fld">
      <label>Group By</label>
      <select id="an-group">
        <option value="month">Month</option>
        <option value="quarter">Quarter</option>
        <option value="year">Year</option>
      </select>
    </div>
    <div class="an-fld">
      <label>Company</label>
      <select id="an-company">
        <option value="">All Companies</option>
        {#- populate via Python: {% for c in companies %}<option>{{ c.name }}</option>{% endfor %} -#}
      </select>
    </div>
    <button class="an-apply" onclick="an_reload()">▶ Apply</button>
  </div>

  {#- ── KPI tiles ── -#}
  <div class="an-kpi-row">
    <div class="an-kpi" style="border-color:#5c4da8">
      <div class="an-kpi-val">{{ frappe.format_value(metrics.revenue or 0, {"fieldtype":"Currency"}) }}</div>
      <div class="an-kpi-lbl">Total Revenue</div>
    </div>
    <div class="an-kpi" style="border-color:#dc2626">
      <div class="an-kpi-val">{{ frappe.format_value(metrics.cost or 0, {"fieldtype":"Currency"}) }}</div>
      <div class="an-kpi-lbl">Total Cost</div>
    </div>
    <div class="an-kpi" style="border-color:{% if (metrics.profit or 0) >= 0 %}#16a34a{% else %}#dc2626{% endif %}">
      <div class="an-kpi-val">{{ frappe.format_value(metrics.profit or 0, {"fieldtype":"Currency"}) }}</div>
      <div class="an-kpi-lbl">Gross Profit</div>
    </div>
    <div class="an-kpi" style="border-color:#0369a1">
      <div class="an-kpi-val">{{ metrics.margin_pct or 0 }}%</div>
      <div class="an-kpi-lbl">Profit Margin</div>
    </div>
  </div>

  {#- ── Charts row ── -#}
  <div class="an-charts-row">
    <div class="an-card">
      <div class="an-card-hdr">📈 Revenue vs Cost — Trend</div>
      <div class="an-chart-area">
        <canvas id="an-trend-chart" width="100%" height="200"></canvas>
      </div>
    </div>
    <div class="an-card">
      <div class="an-card-hdr">🏆 Top Customers by Revenue</div>
      <div class="an-chart-area">
        <canvas id="an-cust-chart" width="100%" height="200"></canvas>
      </div>
    </div>
  </div>

  {#- ── Summary breakdown table ── -#}
  <div class="an-card">
    <div class="an-card-hdr">📊 Breakdown by Category</div>
    <table class="an-tbl">
      <thead><tr><th>Category</th><th>Revenue</th><th>Cost</th><th>Profit</th><th>Invoices</th><th>Share</th></tr></thead>
      <tbody>
        {% set max_rev = summary_rows | map(attribute='revenue') | max if summary_rows else 1 %}
        {% for row in summary_rows %}
        <tr>
          <td><strong>{{ row.category }}</strong></td>
          <td>{{ frappe.format_value(row.revenue, {"fieldtype":"Currency"}) }}</td>
          <td>{{ frappe.format_value(row.cost, {"fieldtype":"Currency"}) }}</td>
          <td class="{% if row.profit >= 0 %}an-profit-pos{% else %}an-profit-neg{% endif %}">
            {{ frappe.format_value(row.profit, {"fieldtype":"Currency"}) }}
          </td>
          <td>{{ row.count }}</td>
          <td>
            {{ ((row.revenue / max_rev)*100)|round|int }}%
            <span class="an-bar-mini" style="width:{{ ((row.revenue / max_rev)*60)|int }}px"></span>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="6" style="text-align:center;padding:24px;color:#9080b8">No data for selected period.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<script>
/* ── Analytics — Chart.js initialisation ───────────────────────────────── */
// Chart.js is loaded from CDN. Add to your .js file on_page_load:
//   frappe.require("https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js", () => load_data());

var AN_LABELS  = {{ trend_labels | tojson }};
var AN_REVENUE = {{ trend_data   | tojson }};
var AN_COST    = {{ cost_data    | tojson }};
var AN_CUST_LABELS = {{ top_customers | map(attribute='name')    | list | tojson }};
var AN_CUST_DATA   = {{ top_customers | map(attribute='revenue') | list | tojson }};

function an_init_charts() {
    if (typeof Chart === "undefined") return; // Chart.js not yet loaded
    // Trend chart (line)
    var ctx1 = document.getElementById("an-trend-chart").getContext("2d");
    new Chart(ctx1, {
        type: "line",
        data: {
            labels: AN_LABELS,
            datasets: [
                { label:"Revenue", data:AN_REVENUE, borderColor:"#5c4da8", backgroundColor:"rgba(92,77,168,.08)", tension:.35, fill:true },
                { label:"Cost",    data:AN_COST,    borderColor:"#dc2626", backgroundColor:"rgba(220,38,38,.06)",  tension:.35, fill:true }
            ]
        },
        options: { responsive:true, maintainAspectRatio:false, plugins:{ legend:{ position:"bottom" } } }
    });
    // Top customers (horizontal bar)
    var ctx2 = document.getElementById("an-cust-chart").getContext("2d");
    new Chart(ctx2, {
        type: "bar",
        data: { labels:AN_CUST_LABELS, datasets:[{ label:"Revenue", data:AN_CUST_DATA, backgroundColor:"#5c4da8" }] },
        options: { indexAxis:"y", responsive:true, maintainAspectRatio:false, plugins:{ legend:{ display:false } } }
    });
}

function an_reload() {
    var args = { from_date: document.getElementById("an-from").value, to_date: document.getElementById("an-to").value, group_by: document.getElementById("an-group").value };
    frappe.call({ method: window._an_method, args: args, callback: r => { if (r.message) $(page.main).html(r.message); } });
}

// Init on load (works if Chart.js already present; otherwise call from .js after require)
if (typeof Chart !== "undefined") an_init_charts();
else document.addEventListener("chartjs_ready", an_init_charts);
</script>
'''


def _desk_tpl_settings(cc, title):
    """Settings page — sidebar tabs + General/Email/Integrations/Advanced/Danger Zone panels."""
    return r'''
<!-- ══ SETTINGS DESK PRESET ═════════════════════════════════════════════════
     Python context keys expected:
       settings   dict  — flat dict of current setting values
       integrations list[{id, name, icon, enabled, description}]
     Example Python:
       settings = {
           "company_name":  frappe.db.get_single_value("Global Defaults","default_company") or "",
           "currency":      frappe.db.get_single_value("Global Defaults","default_currency") or "USD",
           "timezone":      frappe.db.get_single_value("System Settings","time_zone") or "UTC",
           "smtp_host":     frappe.db.get_single_value("Email Account","smtp_server") or "",
           "smtp_port":     frappe.db.get_single_value("Email Account","smtp_port") or 587,
       }
       context.update({"settings": settings, "integrations": []})
     Save method pattern:
       @frappe.whitelist()
       def save_settings(**kwargs):
           doc = frappe.get_doc("System Settings")
           for key, val in kwargs.items():
               if hasattr(doc, key): setattr(doc, key, val)
           doc.save(ignore_permissions=True)
           return {"status":"ok"}
════════════════════════════════════════════════════════════════════════════ -->
<style>
  .stt-wrap { display:flex; height:100%; font-family:inherit; gap:0; }
  /* Sidebar */
  .stt-sidebar { width:200px; background:#fff; border-right:1px solid #e8e0f8; padding:12px 0; flex-shrink:0; }
  .stt-tab { display:flex; align-items:center; gap:8px; padding:9px 16px; cursor:pointer; font-size:13px; color:#5c4da8; border-left:3px solid transparent; transition:background .12s; }
  .stt-tab:hover { background:#f7f3ff; }
  .stt-tab.active { background:#ede9fe; border-color:#7c3aed; font-weight:700; color:#3a2060; }
  .stt-tab-ico { font-size:15px; }
  .stt-sep { height:1px; background:#f0eaff; margin:6px 0; }
  /* Content */
  .stt-content { flex:1; overflow-y:auto; padding:20px 24px; background:#f7f5fc; }
  .stt-panel { display:none; }
  .stt-panel.active { display:block; }
  .stt-panel-title { font-size:16px; font-weight:800; color:#1e1b3a; margin-bottom:4px; }
  .stt-panel-desc  { font-size:12px; color:#6b7280; margin-bottom:18px; }
  /* Cards */
  .stt-card { background:#fff; border-radius:10px; box-shadow:0 2px 8px rgba(92,77,168,.08); padding:18px 20px; margin-bottom:16px; }
  .stt-card-title { font-size:13px; font-weight:700; color:#3a2e5e; margin-bottom:14px; padding-bottom:8px; border-bottom:1px solid #f0eaff; }
  /* Fields */
  .stt-frow { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:12px; }
  .stt-frow.full { grid-template-columns:1fr; }
  .stt-fld { display:flex; flex-direction:column; gap:4px; }
  .stt-lbl { font-size:12px; font-weight:600; color:#3a2e5e; }
  .stt-lbl span { font-size:11px; font-weight:400; color:#9080b8; }
  .stt-inp, .stt-sel { border:1px solid #e0d4fc; border-radius:6px; padding:7px 10px; font-size:13px; background:#faf8ff; outline:none; width:100%; box-sizing:border-box; }
  .stt-inp:focus, .stt-sel:focus { border-color:#7c3aed; box-shadow:0 0 0 2px rgba(124,58,237,.1); }
  /* Toggle switch */
  .stt-toggle-row { display:flex; align-items:center; justify-content:space-between; padding:8px 0; border-bottom:1px solid #f5f0ff; }
  .stt-toggle-row:last-child { border:none; }
  .stt-toggle-info { flex:1; }
  .stt-toggle-lbl { font-size:13px; font-weight:600; color:#1e1b3a; }
  .stt-toggle-sub  { font-size:11px; color:#9080b8; }
  .stt-switch { position:relative; width:40px; height:22px; flex-shrink:0; }
  .stt-switch input { opacity:0; width:0; height:0; }
  .stt-slider { position:absolute; inset:0; background:#e0d4fc; border-radius:22px; cursor:pointer; transition:background .2s; }
  .stt-slider:before { content:""; position:absolute; width:16px; height:16px; left:3px; top:3px; background:#fff; border-radius:50%; transition:transform .2s; }
  .stt-switch input:checked + .stt-slider { background:#5c4da8; }
  .stt-switch input:checked + .stt-slider:before { transform:translateX(18px); }
  /* Buttons */
  .stt-save { padding:8px 20px; background:#5c4da8; color:#fff; border:none; border-radius:7px; font-size:12px; font-weight:700; cursor:pointer; margin-top:4px; }
  .stt-save:hover { background:#4a3d8f; }
  /* Danger zone */
  .stt-danger-card { background:#fff5f5; border:1px solid #fca5a5; border-radius:10px; padding:18px 20px; margin-bottom:16px; }
  .stt-danger-title { color:#7f1d1d; font-weight:700; margin-bottom:10px; }
  .stt-danger-row  { display:flex; align-items:center; justify-content:space-between; padding:8px 0; border-bottom:1px solid #fee2e2; }
  .stt-danger-row:last-child { border:none; }
  .stt-danger-btn { padding:6px 14px; border:1px solid #dc2626; color:#dc2626; background:#fff; border-radius:6px; font-size:12px; font-weight:600; cursor:pointer; }
  .stt-danger-btn:hover { background:#dc2626; color:#fff; }
  /* Integration cards */
  .stt-int-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:12px; }
  .stt-int-card { background:#fff; border:1px solid #e0d4fc; border-radius:8px; padding:14px; display:flex; align-items:flex-start; gap:10px; }
  .stt-int-ico  { font-size:1.8rem; flex-shrink:0; }
  .stt-int-name { font-weight:700; font-size:13px; color:#1e1b3a; }
  .stt-int-desc { font-size:11px; color:#9080b8; margin-top:2px; }
</style>

<div class="stt-wrap">
  {#- ── Sidebar tabs ── -#}
  <div class="stt-sidebar">
    <div class="stt-tab active" onclick="stt_show('general')"><span class="stt-tab-ico">⚙️</span> General</div>
    <div class="stt-tab" onclick="stt_show('email')"><span class="stt-tab-ico">📧</span> Email</div>
    <div class="stt-tab" onclick="stt_show('integrations')"><span class="stt-tab-ico">🔌</span> Integrations</div>
    <div class="stt-tab" onclick="stt_show('advanced')"><span class="stt-tab-ico">🔧</span> Advanced</div>
    <div class="stt-sep"></div>
    <div class="stt-tab" onclick="stt_show('danger')" style="color:#dc2626"><span class="stt-tab-ico">⚠️</span> Danger Zone</div>
  </div>

  {#- ── Content panels ── -#}
  <div class="stt-content">

    {#- General -#}
    <div class="stt-panel active" id="stt-general">
      <div class="stt-panel-title">General Settings</div>
      <div class="stt-panel-desc">Company-wide defaults applied across all modules.</div>
      <div class="stt-card">
        <div class="stt-card-title">Company</div>
        <div class="stt-frow">
          <div class="stt-fld">
            <label class="stt-lbl">Company Name</label>
            <input class="stt-inp" id="stt-company" value="{{ settings.company_name or '' }}">
          </div>
          <div class="stt-fld">
            <label class="stt-lbl">Default Currency</label>
            <select class="stt-sel" id="stt-currency">
              {% for cur in ["USD","EUR","GBP","INR","AED","SAR","PKR"] %}
              <option value="{{ cur }}" {% if settings.currency==cur %}selected{% endif %}>{{ cur }}</option>
              {% endfor %}
            </select>
          </div>
        </div>
        <div class="stt-frow">
          <div class="stt-fld">
            <label class="stt-lbl">Timezone</label>
            <select class="stt-sel" id="stt-tz">
              {% for tz in ["UTC","Asia/Karachi","Asia/Dubai","Asia/Kolkata","America/New_York","Europe/London"] %}
              <option value="{{ tz }}" {% if settings.timezone==tz %}selected{% endif %}>{{ tz }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="stt-fld">
            <label class="stt-lbl">Date Format</label>
            <select class="stt-sel" id="stt-date-fmt">
              <option value="dd-mm-yyyy">DD-MM-YYYY</option>
              <option value="mm-dd-yyyy">MM-DD-YYYY</option>
              <option value="yyyy-mm-dd">YYYY-MM-DD</option>
            </select>
          </div>
        </div>
        <button class="stt-save" onclick="stt_save('general')">Save General</button>
      </div>
      <div class="stt-card">
        <div class="stt-card-title">Feature Flags</div>
        <div class="stt-toggle-row">
          <div class="stt-toggle-info"><div class="stt-toggle-lbl">Multi-Currency</div><div class="stt-toggle-sub">Allow transactions in multiple currencies</div></div>
          <label class="stt-switch"><input type="checkbox" id="stt-multicur" {% if settings.multi_currency %}checked{% endif %}><span class="stt-slider"></span></label>
        </div>
        <div class="stt-toggle-row">
          <div class="stt-toggle-info"><div class="stt-toggle-lbl">Inventory Tracking</div><div class="stt-toggle-sub">Track stock levels per warehouse</div></div>
          <label class="stt-switch"><input type="checkbox" id="stt-inventory" {% if settings.inventory %}checked{% endif %}><span class="stt-slider"></span></label>
        </div>
        <div class="stt-toggle-row">
          <div class="stt-toggle-info"><div class="stt-toggle-lbl">Maintenance Mode</div><div class="stt-toggle-sub">Show maintenance page to non-System Managers</div></div>
          <label class="stt-switch"><input type="checkbox" id="stt-maint"><span class="stt-slider"></span></label>
        </div>
      </div>
    </div>

    {#- Email -#}
    <div class="stt-panel" id="stt-email">
      <div class="stt-panel-title">Email &amp; Notifications</div>
      <div class="stt-panel-desc">Configure outbound email (SMTP) and notification defaults.</div>
      <div class="stt-card">
        <div class="stt-card-title">SMTP Configuration</div>
        <div class="stt-frow">
          <div class="stt-fld"><label class="stt-lbl">SMTP Host</label><input class="stt-inp" id="stt-smtp-host" placeholder="smtp.gmail.com" value="{{ settings.smtp_host or '' }}"></div>
          <div class="stt-fld"><label class="stt-lbl">SMTP Port</label><input class="stt-inp" id="stt-smtp-port" type="number" placeholder="587" value="{{ settings.smtp_port or '' }}"></div>
        </div>
        <div class="stt-frow">
          <div class="stt-fld"><label class="stt-lbl">Username / Email</label><input class="stt-inp" id="stt-smtp-user" type="email" placeholder="no-reply@company.com"></div>
          <div class="stt-fld"><label class="stt-lbl">Password <span>(stored encrypted)</span></label><input class="stt-inp" id="stt-smtp-pass" type="password" placeholder="••••••••"></div>
        </div>
        <div style="display:flex;gap:10px;margin-top:4px">
          <button class="stt-save" onclick="stt_save('email')">Save SMTP</button>
          <button style="padding:8px 16px;border:1px solid #5c4da8;color:#5c4da8;background:#fff;border-radius:7px;font-size:12px;cursor:pointer" onclick="stt_test_email()">Send Test Email</button>
        </div>
      </div>
      <div class="stt-card">
        <div class="stt-card-title">Notification Preferences</div>
        <div class="stt-toggle-row">
          <div class="stt-toggle-info"><div class="stt-toggle-lbl">New Order Notifications</div><div class="stt-toggle-sub">Email alert when a Sales Order is created</div></div>
          <label class="stt-switch"><input type="checkbox" checked><span class="stt-slider"></span></label>
        </div>
        <div class="stt-toggle-row">
          <div class="stt-toggle-info"><div class="stt-toggle-lbl">Overdue Invoice Alerts</div><div class="stt-toggle-sub">Daily digest of overdue Sales Invoices</div></div>
          <label class="stt-switch"><input type="checkbox" checked><span class="stt-slider"></span></label>
        </div>
        <div class="stt-toggle-row">
          <div class="stt-toggle-info"><div class="stt-toggle-lbl">Low Stock Alerts</div><div class="stt-toggle-sub">Alert when item stock falls below reorder level</div></div>
          <label class="stt-switch"><input type="checkbox"><span class="stt-slider"></span></label>
        </div>
      </div>
    </div>

    {#- Integrations -#}
    <div class="stt-panel" id="stt-integrations">
      <div class="stt-panel-title">Integrations</div>
      <div class="stt-panel-desc">Connect with third-party services and APIs.</div>
      <div class="stt-card">
        <div class="stt-card-title">API Keys</div>
        <div class="stt-frow full">
          <div class="stt-fld">
            <label class="stt-lbl">Public API Key <span>(read-only)</span></label>
            <div style="display:flex;gap:8px">
              <input class="stt-inp" id="stt-api-key" value="{{ settings.api_key or 'dk_••••••••••••••••' }}" readonly style="flex:1">
              <button style="padding:6px 12px;border:1px solid #e0d4fc;border-radius:6px;background:#f0eaff;color:#5c4da8;font-size:12px;cursor:pointer" onclick="stt_copy('stt-api-key')">Copy</button>
            </div>
          </div>
        </div>
        <div class="stt-frow full">
          <div class="stt-fld">
            <label class="stt-lbl">Webhook URL</label>
            <input class="stt-inp" id="stt-webhook" placeholder="https://your-server.com/api/webhook" value="{{ settings.webhook_url or '' }}">
          </div>
        </div>
        <button class="stt-save" onclick="stt_save('integrations')">Save</button>
      </div>
      <div class="stt-card">
        <div class="stt-card-title">Available Integrations</div>
        <div class="stt-int-grid">
          {% for intg in integrations %}
          <div class="stt-int-card">
            <div class="stt-int-ico">{{ intg.icon }}</div>
            <div>
              <div class="stt-int-name">{{ intg.name }}</div>
              <div class="stt-int-desc">{{ intg.description }}</div>
              <label class="stt-switch" style="margin-top:8px"><input type="checkbox" {% if intg.enabled %}checked{% endif %}><span class="stt-slider"></span></label>
            </div>
          </div>
          {% else %}
          <p style="color:#9080b8;font-size:12px;grid-column:1/-1">No integrations configured. Add them from Python context.</p>
          {% endfor %}
        </div>
      </div>
    </div>

    {#- Advanced -#}
    <div class="stt-panel" id="stt-advanced">
      <div class="stt-panel-title">Advanced Settings</div>
      <div class="stt-panel-desc">Developer and system-level configuration. Handle with care.</div>
      <div class="stt-card">
        <div class="stt-card-title">System</div>
        <div class="stt-frow">
          <div class="stt-fld"><label class="stt-lbl">Session Expiry (minutes)</label><input class="stt-inp" type="number" value="60"></div>
          <div class="stt-fld"><label class="stt-lbl">Max Upload Size (MB)</label><input class="stt-inp" type="number" value="10"></div>
        </div>
        <div class="stt-frow full">
          <div class="stt-fld"><label class="stt-lbl">Custom JS (injected on all pages)</label><textarea class="stt-inp" style="min-height:80px;resize:vertical" placeholder="// console.log('hello');"></textarea></div>
        </div>
        <button class="stt-save" onclick="stt_save('advanced')">Save Advanced</button>
      </div>
    </div>

    {#- Danger zone -#}
    <div class="stt-panel" id="stt-danger">
      <div class="stt-panel-title" style="color:#dc2626">⚠️ Danger Zone</div>
      <div class="stt-panel-desc">These actions are irreversible. Proceed with extreme caution.</div>
      <div class="stt-danger-card">
        <div class="stt-danger-title">Destructive Actions</div>
        <div class="stt-danger-row">
          <div><div style="font-weight:700;font-size:13px">Clear All Cache</div><div style="font-size:11px;color:#9080b8">Clears Redis cache — users may experience a slow page load once.</div></div>
          <button class="stt-danger-btn" onclick="stt_confirm_danger('clear_cache')">Clear Cache</button>
        </div>
        <div class="stt-danger-row">
          <div><div style="font-weight:700;font-size:13px">Reset Settings to Default</div><div style="font-size:11px;color:#9080b8">All settings will revert to installation defaults.</div></div>
          <button class="stt-danger-btn" onclick="stt_confirm_danger('reset_settings')">Reset</button>
        </div>
        <div class="stt-danger-row">
          <div><div style="font-weight:700;font-size:13px">Delete All Test Data</div><div style="font-size:11px;color:#9080b8">Permanently removes all demo/test documents.</div></div>
          <button class="stt-danger-btn" onclick="stt_confirm_danger('delete_test_data')">Delete</button>
        </div>
      </div>
    </div>

  </div>
</div>

<script>
function stt_show(tab) {
    document.querySelectorAll(".stt-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".stt-panel").forEach(p => p.classList.remove("active"));
    event.currentTarget.classList.add("active");
    document.getElementById("stt-" + tab).classList.add("active");
}
function stt_save(section) {
    frappe.show_alert("Settings saved — implement frappe.call to your save method", "green");
    // frappe.call({ method: "my_app.my_page.save_settings", args: { section: section, ... }, callback: r => frappe.show_alert("Saved", "green") });
}
function stt_test_email() {
    frappe.prompt({label:"Send to", fieldtype:"Data", reqd:1}, v => {
        frappe.call({ method:"frappe.client.get", args:{doctype:"Email Account"}, callback: r => frappe.show_alert("Test email sent to " + v.value, "green") });
    });
}
function stt_copy(id) {
    var el = document.getElementById(id);
    navigator.clipboard.writeText(el.value).then(() => frappe.show_alert("Copied!", "green"));
}
function stt_confirm_danger(action) {
    frappe.confirm("Are you absolutely sure? This cannot be undone.", function() {
        frappe.call({ method: "frappe_devkit.api.page_builder.create_desk_page",
                      // Replace with your actual danger-zone method
                      args: { action: action },
                      callback: r => frappe.show_alert("Done: " + action, "green") });
    });
}
</script>
'''


def _desk_tpl_wizard(cc, title):
    """Multi-step wizard — 4-step progress bar, form per step, review + confirm."""
    return r'''
<!-- ══ WIZARD DESK PRESET ═══════════════════════════════════════════════════
     Python context keys expected:
       step      int  — current step (1–4), default 1
       data      dict — accumulated form data across steps
     Example Python:
       step = int(kwargs.get("step") or 1)
       data = frappe.parse_json(kwargs.get("data") or "{}")
       context.update({"step": step, "data": data})
     Each step submits to your Python method which returns the next step HTML.
════════════════════════════════════════════════════════════════════════════ -->
<style>
  .wiz-wrap { max-width:720px; margin:0 auto; font-family:inherit; padding:4px 0; }
  /* Progress bar */
  .wiz-steps { display:flex; align-items:center; margin-bottom:24px; }
  .wiz-step  { display:flex; flex-direction:column; align-items:center; flex:1; position:relative; }
  .wiz-step-line { position:absolute; top:16px; left:50%; right:-50%; height:2px; background:#e0d4fc; z-index:0; }
  .wiz-step:last-child .wiz-step-line { display:none; }
  .wiz-step-line.done { background:#5c4da8; }
  .wiz-step-circle { width:32px; height:32px; border-radius:50%; border:2px solid #e0d4fc; background:#fff; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; color:#9080b8; z-index:1; position:relative; }
  .wiz-step-circle.active { border-color:#5c4da8; background:#5c4da8; color:#fff; }
  .wiz-step-circle.done   { border-color:#5c4da8; background:#5c4da8; color:#fff; }
  .wiz-step-lbl { font-size:10px; text-transform:uppercase; letter-spacing:.06em; margin-top:6px; color:#9080b8; text-align:center; }
  .wiz-step-lbl.active { color:#5c4da8; font-weight:700; }
  /* Card */
  .wiz-card { background:#fff; border-radius:10px; box-shadow:0 2px 14px rgba(92,77,168,.10); overflow:hidden; margin-bottom:14px; }
  .wiz-card-hdr { background:#5c4da8; color:#fff; padding:14px 20px; font-size:15px; font-weight:800; }
  .wiz-card-body { padding:24px; }
  /* Fields */
  .wiz-frow { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }
  .wiz-frow.full { grid-template-columns:1fr; }
  .wiz-fld { display:flex; flex-direction:column; gap:5px; }
  .wiz-lbl { font-size:12px; font-weight:600; color:#3a2e5e; }
  .wiz-inp, .wiz-sel, .wiz-ta { border:1px solid #e0d4fc; border-radius:7px; padding:8px 12px; font-size:13px; background:#faf8ff; outline:none; width:100%; box-sizing:border-box; }
  .wiz-inp:focus, .wiz-sel:focus, .wiz-ta:focus { border-color:#7c3aed; box-shadow:0 0 0 3px rgba(124,58,237,.1); }
  .wiz-ta { min-height:80px; resize:vertical; }
  /* Review card */
  .wiz-review-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .wiz-review-item { background:#faf7ff; border-radius:7px; padding:10px 14px; }
  .wiz-review-key { font-size:11px; text-transform:uppercase; color:#9080b8; letter-spacing:.06em; }
  .wiz-review-val { font-size:14px; font-weight:700; color:#1e1b3a; margin-top:2px; }
  .wiz-review-edit { font-size:11px; color:#5c4da8; cursor:pointer; text-decoration:none; }
  /* Success */
  .wiz-success { text-align:center; padding:30px 20px; }
  .wiz-success-ico { font-size:3.5rem; }
  .wiz-success-title { font-size:1.3rem; font-weight:800; color:#14532d; margin:10px 0 4px; }
  .wiz-success-doc { font-size:13px; color:#5c4da8; font-weight:600; }
  /* Footer */
  .wiz-footer { display:flex; gap:10px; justify-content:space-between; padding:14px 20px; background:#fff; border-radius:10px; box-shadow:0 2px 10px rgba(92,77,168,.08); }
  .wiz-next { padding:9px 24px; background:#5c4da8; color:#fff; border:none; border-radius:7px; font-size:13px; font-weight:700; cursor:pointer; }
  .wiz-next:hover { background:#4a3d8f; }
  .wiz-prev { padding:9px 18px; background:#f0eaff; color:#5c4da8; border:1px solid #d4bcfc; border-radius:7px; font-size:13px; cursor:pointer; }
  .wiz-submit { padding:9px 24px; background:#16a34a; color:#fff; border:none; border-radius:7px; font-size:13px; font-weight:700; cursor:pointer; }
</style>

<div class="wiz-wrap">
  {#- ── Step progress ── -#}
  <div class="wiz-steps">
    {% set steps = [("1","📋","Basic Info"),("2","⚙️","Configure"),("3","🔍","Review"),("4","✅","Done")] %}
    {% for s in steps %}
    {% set n = loop.index %}
    <div class="wiz-step">
      {% if not loop.last %}<div class="wiz-step-line {% if step > n %}done{% endif %}"></div>{% endif %}
      <div class="wiz-step-circle {% if step == n %}active{% elif step > n %}done{% endif %}">
        {% if step > n %}✓{% else %}{{ s[0] }}{% endif %}
      </div>
      <div class="wiz-step-lbl {% if step == n %}active{% endif %}">{{ s[2] }}</div>
    </div>
    {% endfor %}
  </div>

  {#- ── Step 1: Basic Info ── -#}
  {% if step == 1 %}
  <div class="wiz-card">
    <div class="wiz-card-hdr">📋 Step 1 — Basic Information</div>
    <div class="wiz-card-body">
      <div class="wiz-frow">
        <div class="wiz-fld">
          <label class="wiz-lbl">Document Name *</label>
          <input class="wiz-inp" id="wiz-name" value="{{ data.name or '' }}" placeholder="Enter a unique name">
        </div>
        <div class="wiz-fld">
          <label class="wiz-lbl">Document Type *</label>
          <select class="wiz-sel" id="wiz-doctype">
            <option value="">— Select —</option>
            {% for dt in ["Sales Order","Purchase Order","Task","Issue","Lead","Quotation"] %}
            <option value="{{ dt }}" {% if data.doctype==dt %}selected{% endif %}>{{ dt }}</option>
            {% endfor %}
          </select>
        </div>
      </div>
      <div class="wiz-frow">
        <div class="wiz-fld">
          <label class="wiz-lbl">Priority</label>
          <select class="wiz-sel" id="wiz-priority">
            {% for p in ["Low","Medium","High","Urgent"] %}
            <option value="{{ p }}" {% if data.priority==p %}selected{% endif %}>{{ p }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="wiz-fld">
          <label class="wiz-lbl">Due Date</label>
          <input class="wiz-inp" type="date" id="wiz-due" value="{{ data.due_date or '' }}">
        </div>
      </div>
      <div class="wiz-frow full">
        <div class="wiz-fld">
          <label class="wiz-lbl">Description</label>
          <textarea class="wiz-ta" id="wiz-desc" placeholder="Brief description…">{{ data.description or '' }}</textarea>
        </div>
      </div>
    </div>
  </div>

  {#- ── Step 2: Configuration ── -#}
  {% elif step == 2 %}
  <div class="wiz-card">
    <div class="wiz-card-hdr">⚙️ Step 2 — Configuration</div>
    <div class="wiz-card-body">
      <div class="wiz-frow">
        <div class="wiz-fld">
          <label class="wiz-lbl">Assign To</label>
          <input class="wiz-inp" id="wiz-assign" value="{{ data.assigned_to or '' }}" placeholder="user@company.com">
        </div>
        <div class="wiz-fld">
          <label class="wiz-lbl">Department</label>
          <select class="wiz-sel" id="wiz-dept">
            <option value="">— Select —</option>
            {% for d in ["Sales","Purchasing","Operations","Finance","IT","HR"] %}
            <option value="{{ d }}" {% if data.department==d %}selected{% endif %}>{{ d }}</option>
            {% endfor %}
          </select>
        </div>
      </div>
      <div class="wiz-frow">
        <div class="wiz-fld">
          <label class="wiz-lbl">Notify by Email?</label>
          <select class="wiz-sel" id="wiz-notify">
            <option value="1" {% if data.notify %}selected{% endif %}>Yes — send email notification</option>
            <option value="0" {% if not data.notify %}selected{% endif %}>No</option>
          </select>
        </div>
        <div class="wiz-fld">
          <label class="wiz-lbl">Tags (comma-separated)</label>
          <input class="wiz-inp" id="wiz-tags" value="{{ data.tags or '' }}" placeholder="urgent, client-facing">
        </div>
      </div>
    </div>
  </div>

  {#- ── Step 3: Review ── -#}
  {% elif step == 3 %}
  <div class="wiz-card">
    <div class="wiz-card-hdr">🔍 Step 3 — Review &amp; Confirm</div>
    <div class="wiz-card-body">
      <p style="font-size:13px;color:#6b7280;margin-bottom:16px">Please review the details below before submitting.</p>
      <div class="wiz-review-grid">
        {% for pair in [("Document Name",data.name),("Document Type",data.doctype),("Priority",data.priority),("Due Date",data.due_date),("Assigned To",data.assigned_to),("Department",data.department),("Tags",data.tags)] %}
        {% if pair[1] %}
        <div class="wiz-review-item">
          <div class="wiz-review-key">{{ pair[0] }}</div>
          <div class="wiz-review-val">{{ pair[1] }}</div>
        </div>
        {% endif %}
        {% endfor %}
      </div>
      {% if data.description %}
      <div class="wiz-review-item" style="margin-top:12px;grid-column:1/-1">
        <div class="wiz-review-key">Description</div>
        <div class="wiz-review-val" style="font-size:13px;font-weight:400">{{ data.description }}</div>
      </div>
      {% endif %}
    </div>
  </div>

  {#- ── Step 4: Complete ── -#}
  {% elif step == 4 %}
  <div class="wiz-card">
    <div class="wiz-card-body">
      <div class="wiz-success">
        <div class="wiz-success-ico">✅</div>
        <div class="wiz-success-title">Created Successfully!</div>
        <div class="wiz-success-doc">{{ data.doctype }}: <a href="/app/{{ data.doctype|lower|replace(' ','-') }}/{{ data.created_name }}" style="color:#5c4da8">{{ data.created_name }}</a></div>
        <div style="margin-top:20px;display:flex;gap:12px;justify-content:center">
          <a href="/app/{{ data.doctype|lower|replace(' ','-') }}/{{ data.created_name }}" class="wiz-next" style="text-decoration:none">View Document →</a>
          <button class="wiz-prev" onclick="wiz_reset()">Create Another</button>
        </div>
      </div>
    </div>
  </div>
  {% endif %}

  {#- ── Footer navigation ── -#}
  {% if step < 4 %}
  <div class="wiz-footer">
    <div>
      {% if step > 1 %}
      <button class="wiz-prev" onclick="wiz_go({{ step - 1 }})">← Previous</button>
      {% endif %}
    </div>
    <div>
      {% if step < 3 %}
      <button class="wiz-next" onclick="wiz_go({{ step + 1 }})">Next →</button>
      {% elif step == 3 %}
      <button class="wiz-submit" onclick="wiz_submit()">🚀 Submit</button>
      {% endif %}
    </div>
  </div>
  {% endif %}
</div>

<script>
var _wiz_data = {{ data | tojson }};
function wiz_collect() {
    var step = {{ step }};
    if (step === 1) {
        _wiz_data.name        = $("#wiz-name").val();
        _wiz_data.doctype     = $("#wiz-doctype").val();
        _wiz_data.priority    = $("#wiz-priority").val();
        _wiz_data.due_date    = $("#wiz-due").val();
        _wiz_data.description = $("#wiz-desc").val();
    } else if (step === 2) {
        _wiz_data.assigned_to = $("#wiz-assign").val();
        _wiz_data.department  = $("#wiz-dept").val();
        _wiz_data.notify      = $("#wiz-notify").val();
        _wiz_data.tags        = $("#wiz-tags").val();
    }
}
function wiz_go(next_step) {
    wiz_collect();
    frappe.call({ method: window._wiz_method, args: { step: next_step, data: JSON.stringify(_wiz_data) },
                  callback: r => { if (r.message) $(page.main).html(r.message); } });
}
function wiz_submit() {
    wiz_collect();
    frappe.call({ method: window._wiz_method, args: { step: 4, submit: 1, data: JSON.stringify(_wiz_data) },
                  callback: r => { if (r.message) $(page.main).html(r.message); } });
}
function wiz_reset() { frappe.call({ method: window._wiz_method, args: { step:1, data:"{}" }, callback: r => { if(r.message) $(page.main).html(r.message); } }); }
</script>
'''


def _desk_tpl_kanban(cc, title):
    """Kanban board — 4 columns (Todo/In Progress/Review/Done) with draggable cards."""
    return r'''
<!-- ══ KANBAN DESK PRESET ═══════════════════════════════════════════════════
     Python context keys expected:
       columns  dict  — {"todo":[], "inprogress":[], "review":[], "done":[]}
       Each card:  {name, title, description, assignee, avatar, priority, due_date, tags}
     Example Python (Task doctype):
       statuses = {"todo":"Open","inprogress":"Working","review":"Pending Review","done":"Completed"}
       columns  = {}
       for col, status in statuses.items():
           columns[col] = frappe.get_all("Task",
               filters={"status": status},
               fields=["name","subject as title","description","exp_end_date as due_date",
                       "assigned_to as assignee","priority"],
               limit=50)
       context.update({"columns": columns})
     For Issue: use {"todo":"Open","inprogress":"Replied","review":"Hold","done":"Resolved"}
════════════════════════════════════════════════════════════════════════════ -->
<style>
  .kb-wrap { display:flex; gap:14px; overflow-x:auto; height:100%; padding:2px 4px 8px; font-family:inherit; align-items:flex-start; }
  /* Column */
  .kb-col { min-width:260px; max-width:280px; flex-shrink:0; display:flex; flex-direction:column; border-radius:10px; background:#f7f5fc; overflow:hidden; }
  .kb-col-hdr { padding:10px 14px; display:flex; align-items:center; justify-content:space-between; font-weight:700; font-size:12px; text-transform:uppercase; letter-spacing:.07em; }
  .kb-col-hdr.todo       { background:#e5e7eb; color:#374151; }
  .kb-col-hdr.inprogress { background:#dbeafe; color:#1e3a5f; }
  .kb-col-hdr.review     { background:#fef9c3; color:#713f12; }
  .kb-col-hdr.done       { background:#dcfce7; color:#14532d; }
  .kb-col-count { background:rgba(0,0,0,.1); border-radius:20px; padding:1px 7px; font-size:10px; }
  .kb-col-add { font-size:16px; cursor:pointer; opacity:.7; }
  .kb-col-add:hover { opacity:1; }
  /* Card list */
  .kb-list { flex:1; overflow-y:auto; padding:8px; min-height:60px; }
  .kb-list.drag-over { background:rgba(92,77,168,.06); border-radius:8px; }
  /* Card */
  .kb-card { background:#fff; border-radius:8px; box-shadow:0 1px 6px rgba(92,77,168,.10); padding:12px; margin-bottom:8px; cursor:grab; border-left:3px solid #e0d4fc; transition:transform .15s, box-shadow .15s; }
  .kb-card:hover { transform:translateY(-2px); box-shadow:0 4px 14px rgba(92,77,168,.18); }
  .kb-card:active { cursor:grabbing; }
  .kb-card.priority-high   { border-color:#dc2626; }
  .kb-card.priority-medium { border-color:#f59e0b; }
  .kb-card.priority-low    { border-color:#6b7280; }
  .kb-card-title { font-weight:700; font-size:13px; color:#1e1b3a; margin-bottom:4px; }
  .kb-card-desc  { font-size:11px; color:#9080b8; margin-bottom:8px; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }
  .kb-card-footer { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
  .kb-avatar { width:22px; height:22px; border-radius:50%; background:#5c4da8; color:#fff; font-size:9px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
  .kb-badge { padding:2px 7px; border-radius:20px; font-size:9px; font-weight:700; }
  .kb-badge.high   { background:#fee2e2; color:#7f1d1d; }
  .kb-badge.medium { background:#fef9c3; color:#713f12; }
  .kb-badge.low    { background:#f3f4f6; color:#374151; }
  .kb-due { font-size:10px; color:#9080b8; margin-left:auto; }
  .kb-due.overdue { color:#dc2626; font-weight:700; }
  .kb-tag { background:#ede9fe; color:#5c4da8; padding:1px 6px; border-radius:4px; font-size:9px; }
  .kb-drag-handle { color:#d4bcfc; font-size:12px; float:right; cursor:grab; }
  /* Add card footer */
  .kb-add-row { padding:6px 8px; }
  .kb-add-btn { width:100%; padding:7px; border:2px dashed #e0d4fc; border-radius:6px; background:transparent; color:#9080b8; font-size:12px; cursor:pointer; text-align:center; }
  .kb-add-btn:hover { background:#f5f0ff; color:#5c4da8; border-color:#a78bfa; }
</style>

<div class="kb-wrap">
  {% set col_defs = [("todo","Todo","todo"),("inprogress","In Progress","inprogress"),("review","In Review","review"),("done","Done","done")] %}
  {% for col_id, col_label, col_cls in col_defs %}
  <div class="kb-col" id="kb-col-{{ col_id }}">
    <div class="kb-col-hdr {{ col_cls }}">
      <span>{{ col_label }}</span>
      <div style="display:flex;align-items:center;gap:6px">
        <span class="kb-col-count">{{ (columns[col_id] or []) | length }}</span>
        <span class="kb-col-add" onclick="kb_add_card('{{ col_id }}')">＋</span>
      </div>
    </div>
    <div class="kb-list" id="kb-list-{{ col_id }}"
         ondragover="kb_dragover(event)" ondrop="kb_drop(event,'{{ col_id }}')">
      {% for card in (columns[col_id] or []) %}
      <div class="kb-card priority-{{ card.priority|lower if card.priority else 'low' }}"
           draggable="true"
           id="kb-card-{{ card.name }}"
           data-name="{{ card.name }}"
           data-col="{{ col_id }}"
           ondragstart="kb_dragstart(event)">
        <span class="kb-drag-handle">⠿</span>
        <div class="kb-card-title">{{ card.title or card.name }}</div>
        {% if card.description %}
        <div class="kb-card-desc">{{ card.description }}</div>
        {% endif %}
        <div class="kb-card-footer">
          {% if card.assignee %}
          <div class="kb-avatar" title="{{ card.assignee }}">{{ card.assignee[0]|upper }}</div>
          {% endif %}
          {% if card.priority %}
          <span class="kb-badge {{ card.priority|lower }}">{{ card.priority }}</span>
          {% endif %}
          {% if card.due_date %}
          <span class="kb-due">{{ card.due_date }}</span>
          {% endif %}
        </div>
      </div>
      {% else %}
      <div style="text-align:center;padding:20px;color:#d4bcfc;font-size:12px">No cards</div>
      {% endfor %}
    </div>
    <div class="kb-add-row">
      <button class="kb-add-btn" onclick="kb_add_card('{{ col_id }}')">+ Add card</button>
    </div>
  </div>
  {% endfor %}
</div>

<script>
/* ── Kanban drag-drop ────────────────────────────────────────────────────── */
var _kb_dragging = null;
function kb_dragstart(e) { _kb_dragging = e.currentTarget; e.currentTarget.style.opacity = ".5"; }
function kb_dragover(e)  { e.preventDefault(); e.currentTarget.classList.add("drag-over"); }
function kb_drop(e, col) {
    e.preventDefault();
    e.currentTarget.classList.remove("drag-over");
    if (!_kb_dragging) return;
    var name    = _kb_dragging.dataset.name;
    var old_col = _kb_dragging.dataset.col;
    if (old_col === col) { _kb_dragging.style.opacity="1"; return; }
    _kb_dragging.dataset.col = col;
    document.getElementById("kb-list-" + col).appendChild(_kb_dragging);
    _kb_dragging.style.opacity = "1";
    // Call backend to update status
    var status_map = { todo:"Open", inprogress:"Working", review:"Pending Review", done:"Completed" };
    frappe.call({
        method: "frappe.client.set_value",
        args: { doctype:"Task", name:name, fieldname:"status", value: status_map[col] || col },
        callback: r => frappe.show_alert(name + " → " + col, "green")
    });
}
document.addEventListener("dragend", function() { if (_kb_dragging) { _kb_dragging.style.opacity="1"; _kb_dragging=null; } });
document.querySelectorAll(".kb-list").forEach(l => l.addEventListener("dragleave", function() { this.classList.remove("drag-over"); }));

function kb_add_card(col) {
    frappe.prompt([
        { label:"Title",    fieldtype:"Data",   reqd:1 },
        { label:"Priority", fieldtype:"Select", options:"Low\nMedium\nHigh", default:"Medium" },
        { label:"Due Date", fieldtype:"Date" },
    ], function(v) {
        frappe.call({
            method: "frappe.client.insert",
            args: { doc: { doctype:"Task", subject:v.Title, priority:v.Priority, exp_end_date:v["Due Date"], status: {todo:"Open",inprogress:"Working",review:"Pending Review",done:"Completed"}[col]||col } },
            callback: r => { frappe.show_alert("Card created: " + r.message.name, "green"); frappe.call({ method: window._kb_method, callback: rr => { if(rr.message) $(page.main).html(rr.message); } }); }
        });
    }, "Add Card to " + col);
}
</script>
'''


def _desk_tpl_import_export(cc, title):
    """Import / Export tooling — doctype selector, CSV download, paste/upload import."""
    return f'''<!-- ══ IMPORT/EXPORT DESK PRESET ═════════════════════════════════════════════
     Python context keys expected:
       selected_doctype  str  — currently selected DocType
       doctype_fields    list — {{fieldname, label, fieldtype}}
       import_history    list — {{name, reference_doctype, import_type, status,
                                  total_records, failed_records, creation}}
     Wire up:
       page.main.on("click","#ie-download-btn", ...)  → frappe.call get_{cc.replace("-","_")} with doctype
       page.main.on("click","#ie-import-btn", ...)    → frappe.call with CSV text payload
══════════════════════════════════════════════════════════════════════════ -->
<style>
  :root{{--ie-brand:#0891b2;--ie-light:#cffafe;--ie-dark:#155e75;--ie-rad:10px;--ie-sh:0 4px 18px rgba(8,145,178,.12);}}
  .ie-wrap{{font-family:inherit;padding:0 4px}}
  .ie-card{{background:#fff;border-radius:var(--ie-rad);box-shadow:var(--ie-sh);overflow:hidden;margin-bottom:18px}}
  .ie-card-hdr{{padding:12px 18px;font-weight:700;font-size:13px;color:var(--ie-dark);background:var(--ie-light);border-bottom:1px solid #a5f3fc;display:flex;align-items:center;gap:8px}}
  .ie-card-body{{padding:16px 18px}}
  .ie-row{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:12px}}
  .ie-label{{font-size:11px;font-weight:700;color:var(--ie-dark);display:block;margin-bottom:4px}}
  .ie-sel,.ie-inp{{width:100%;padding:7px 10px;border:1px solid #cffafe;border-radius:6px;font-size:12px;background:#f0fdfe;outline:none}}
  .ie-sel:focus,.ie-inp:focus{{border-color:var(--ie-brand);box-shadow:0 0 0 2px rgba(8,145,178,.15)}}
  .ie-btn{{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:6px;font-size:12px;font-weight:700;border:none;cursor:pointer;transition:filter .15s}}
  .ie-btn:hover{{filter:brightness(1.08)}}
  .ie-btn.primary{{background:var(--ie-brand);color:#fff}}
  .ie-btn.secondary{{background:var(--ie-light);color:var(--ie-dark)}}
  .ie-btn.danger{{background:#fee2e2;color:#991b1b}}
  .ie-fields-wrap{{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}}
  .ie-field-chip{{padding:3px 10px;border-radius:20px;font-size:10px;font-weight:700;background:#e0f2fe;color:#0c4a6e;cursor:pointer;border:2px solid transparent}}
  .ie-field-chip.selected{{background:var(--ie-brand);color:#fff;border-color:var(--ie-brand)}}
  .ie-textarea{{width:100%;min-height:120px;padding:10px;border:1px solid #cffafe;border-radius:6px;font-size:11.5px;font-family:monospace;background:#f0fdfe;resize:vertical;outline:none}}
  .ie-textarea:focus{{border-color:var(--ie-brand)}}
  .ie-table{{width:100%;border-collapse:collapse;font-size:12px}}
  .ie-table th{{background:var(--ie-light);color:var(--ie-dark);padding:8px 12px;text-align:left;font-weight:700;border-bottom:2px solid #a5f3fc}}
  .ie-table td{{padding:7px 12px;border-bottom:1px solid #f0fdfe}}
  .ie-table tr:hover td{{background:#f0fdfe}}
  .ie-status{{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700}}
  .ie-status.success{{background:#dcfce7;color:#14532d}}
  .ie-status.error{{background:#fee2e2;color:#991b1b}}
  .ie-status.pending{{background:#fef9c3;color:#713f12}}
  .ie-status.partial{{background:#dbeafe;color:#1e3a5f}}
</style>

<div class="ie-wrap">

  {{#- ══ EXPORT SECTION ═══════════════════════════════════════════════════════ -#}}
  <div class="ie-card">
    <div class="ie-card-hdr">⬇️ Export Data</div>
    <div class="ie-card-body">
      <div class="ie-row">
        <div>
          <label class="ie-label">DocType</label>
          <input id="ie-doctype" class="ie-inp" value="{{{{ selected_doctype }}}}" placeholder="e.g. Sales Invoice">
        </div>
        <div>
          <label class="ie-label">Format</label>
          <select id="ie-format" class="ie-sel">
            <option value="csv">CSV</option>
            <option value="xlsx">Excel (.xlsx)</option>
          </select>
        </div>
      </div>
      <div>
        <label class="ie-label">Fields to export (click to toggle)</label>
        <div class="ie-fields-wrap" id="ie-fields-wrap">
          {{% for f in doctype_fields %}}
          <span class="ie-field-chip" data-fn="{{{{ f.fieldname }}}}" onclick="ie_toggle_field(this)">{{{{ f.label or f.fieldname }}}}</span>
          {{% endfor %}}
        </div>
      </div>
      <div style="margin-top:12px;display:flex;gap:8px">
        <button class="ie-btn primary" id="ie-select-all" onclick="ie_select_all()">Select All</button>
        <button class="ie-btn secondary" id="ie-export-btn" onclick="ie_export()">⬇️ Download</button>
      </div>
    </div>
  </div>

  {{#- ══ IMPORT SECTION ═══════════════════════════════════════════════════════ -#}}
  <div class="ie-card">
    <div class="ie-card-hdr">⬆️ Import Data</div>
    <div class="ie-card-body">
      <p style="font-size:12px;color:#0e7490;margin-bottom:10px">
        Paste CSV below (first row = headers matching field names) or upload a file.
      </p>
      <label class="ie-label">Paste CSV / JSON</label>
      <textarea id="ie-csv-input" class="ie-textarea" placeholder="name,customer,grand_total&#10;INV-0001,Example,1000"></textarea>
      <div style="display:flex;gap:8px;margin-top:10px;align-items:center">
        <label class="ie-btn secondary" style="cursor:pointer">
          📂 Upload File <input type="file" id="ie-file-input" accept=".csv,.xlsx,.json" style="display:none" onchange="ie_read_file(this)">
        </label>
        <button class="ie-btn primary" onclick="ie_import()">⬆️ Import</button>
        <button class="ie-btn secondary" onclick="ie_preview()">👁 Preview</button>
      </div>
      <div id="ie-preview-wrap" style="margin-top:12px;display:none">
        <label class="ie-label">Preview (first 5 rows)</label>
        <div id="ie-preview-tbl"></div>
      </div>
      <div id="ie-import-progress" style="display:none;margin-top:12px">
        <div style="background:#e0f2fe;border-radius:6px;height:10px;overflow:hidden">
          <div id="ie-prog-bar" style="height:100%;background:var(--ie-brand);width:0%;transition:width .3s"></div>
        </div>
        <div id="ie-prog-label" style="font-size:11px;color:#0e7490;margin-top:4px;text-align:center">Importing…</div>
      </div>
    </div>
  </div>

  {{#- ══ HISTORY ════════════════════════════════════════════════════════════ -#}}
  <div class="ie-card">
    <div class="ie-card-hdr">🕑 Import History</div>
    <div class="ie-card-body" style="padding:0">
      <table class="ie-table">
        <thead>
          <tr><th>ID</th><th>DocType</th><th>Type</th><th>Status</th><th>Total</th><th>Failed</th><th>Date</th></tr>
        </thead>
        <tbody>
          {{% for h in import_history %}}
          <tr>
            <td><a href="/app/data-import/{{{{ h.name }}}}" target="_blank">{{{{ h.name }}}}</a></td>
            <td>{{{{ h.reference_doctype }}}}</td>
            <td>{{{{ h.import_type }}}}</td>
            <td><span class="ie-status {{% if h.status=='Success' %}}success{{% elif h.status=='Error' %}}error{{% elif h.status=='Partial Success' %}}partial{{% else %}}pending{{% endif %}}">{{{{ h.status }}}}</span></td>
            <td>{{{{ h.total_records }}}}</td>
            <td>{{{{ h.failed_records }}}}</td>
            <td style="font-size:11px;color:#64748b">{{{{ h.creation }}}}</td>
          </tr>
          {{% else %}}
          <tr><td colspan="7" style="text-align:center;padding:24px;color:#94a3b8">No import history.</td></tr>
          {{% endfor %}}
        </tbody>
      </table>
    </div>
  </div>

</div>

<script>
/* ── Import/Export helpers ──────────────────────────────────────────────── */
function ie_toggle_field(el) {{ el.classList.toggle("selected"); }}
function ie_select_all() {{
    document.querySelectorAll(".ie-field-chip").forEach(c => c.classList.add("selected"));
}}
function ie_selected_fields() {{
    return [...document.querySelectorAll(".ie-field-chip.selected")].map(c => c.dataset.fn);
}}
function ie_export() {{
    var fields = ie_selected_fields();
    var doctype = document.getElementById("ie-doctype").value.trim();
    if (!doctype) {{ frappe.show_alert("Enter a DocType", "orange"); return; }}
    if (!fields.length) {{ frappe.show_alert("Select at least one field", "orange"); return; }}
    frappe.show_alert("Preparing download…", "blue");
    // Use Frappe's built-in export
    var params = new URLSearchParams({{
        doctype: doctype,
        fields: JSON.stringify(fields),
        file_type: document.getElementById("ie-format").value.toUpperCase(),
        cmd: "frappe.desk.reportview.export_query"
    }});
    window.open("/api/method/frappe.desk.reportview.export_query?" + params.toString());
}}
function ie_read_file(inp) {{
    var file = inp.files[0]; if (!file) return;
    var reader = new FileReader();
    reader.onload = e => {{ document.getElementById("ie-csv-input").value = e.target.result; }};
    reader.readAsText(file);
}}
function ie_preview() {{
    var csv = document.getElementById("ie-csv-input").value.trim();
    if (!csv) {{ frappe.show_alert("Paste CSV first", "orange"); return; }}
    var lines = csv.split("\\n").slice(0, 6);
    var cols = lines[0].split(",");
    var html = '<table class="ie-table"><thead><tr>' + cols.map(c=>`<th>${{c}}</th>`).join("") + "</tr></thead><tbody>";
    lines.slice(1).forEach(row => {{
        html += "<tr>" + row.split(",").map(c=>`<td>${{c}}</td>`).join("") + "</tr>";
    }});
    html += "</tbody></table>";
    document.getElementById("ie-preview-tbl").innerHTML = html;
    document.getElementById("ie-preview-wrap").style.display = "block";
}}
function ie_import() {{
    var csv = document.getElementById("ie-csv-input").value.trim();
    var doctype = document.getElementById("ie-doctype").value.trim();
    if (!doctype || !csv) {{ frappe.show_alert("DocType and CSV required", "orange"); return; }}
    document.getElementById("ie-import-progress").style.display = "block";
    // Animate progress (demo — replace with real progress via frappe.call)
    var prog = 0;
    var bar = document.getElementById("ie-prog-bar");
    var lbl = document.getElementById("ie-prog-label");
    var iv = setInterval(() => {{
        prog = Math.min(prog + Math.random() * 15, 90);
        bar.style.width = prog + "%";
    }}, 300);
    frappe.call({{
        method: "frappe.client.insert_many",
        args: {{ docs: [] }},  // replace with parsed docs
        callback: r => {{
            clearInterval(iv);
            bar.style.width = "100%";
            lbl.textContent = "Done!";
            frappe.show_alert("Import complete", "green");
        }},
        error: e => {{
            clearInterval(iv);
            bar.style.width = "100%";
            bar.style.background = "#dc2626";
            lbl.textContent = "Error: " + (e.message || "unknown");
        }}
    }});
}}
</script>
'''


def _desk_tpl_approval_inbox(cc, title):
    """Approval Inbox — pending workflow actions with batch approve/reject."""
    return f'''<!-- ══ APPROVAL INBOX DESK PRESET ════════════════════════════════════════════
     Python context keys expected:
       requests  list — {{name, doctype, document_name, submitted_by, creation,
                          status, workflow_state, amount, description, priority, pending_since}}
       counts    dict — {{all, pending, approved, rejected}}
     Wire backend approve/reject:
       frappe.call("frappe.model.workflow.apply_workflow",
                   {{doc: ..., action: "Approve"}})
═══════════════════════════════════════════════════════════════════════════ -->
<style>
  :root{{--ai-brand:#15803d;--ai-light:#dcfce7;--ai-dark:#14532d;--ai-rad:10px;--ai-sh:0 4px 18px rgba(21,128,61,.10);}}
  .ai-wrap{{font-family:inherit;padding:0 4px}}
  .ai-kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}}
  .ai-kpi{{background:#fff;border-radius:var(--ai-rad);box-shadow:var(--ai-sh);padding:14px 18px;border-left:4px solid var(--ai-brand)}}
  .ai-kpi.pending{{border-color:#f59e0b}}
  .ai-kpi.approved{{border-color:var(--ai-brand)}}
  .ai-kpi.rejected{{border-color:#dc2626}}
  .ai-kpi-val{{font-size:1.8rem;font-weight:900;color:#1e1b3a}}
  .ai-kpi-lbl{{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:#6b7280}}
  .ai-toolbar{{display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap}}
  .ai-tab{{padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;cursor:pointer;border:2px solid #e5e7eb;background:#fff;color:#374151;transition:all .15s}}
  .ai-tab.active,.ai-tab:hover{{background:var(--ai-brand);color:#fff;border-color:var(--ai-brand)}}
  .ai-search{{flex:1;min-width:160px;padding:7px 12px;border:1px solid #e5e7eb;border-radius:6px;font-size:12px;outline:none}}
  .ai-search:focus{{border-color:var(--ai-brand)}}
  .ai-btn-batch{{padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;border:none;cursor:pointer}}
  .ai-btn-batch.approve{{background:var(--ai-light);color:var(--ai-dark)}}
  .ai-btn-batch.reject{{background:#fee2e2;color:#991b1b}}
  /* Cards */
  .ai-card{{background:#fff;border-radius:var(--ai-rad);box-shadow:var(--ai-sh);padding:14px 16px;margin-bottom:10px;display:flex;gap:12px;align-items:flex-start;transition:box-shadow .15s}}
  .ai-card:hover{{box-shadow:0 6px 24px rgba(21,128,61,.16)}}
  .ai-chk{{width:16px;height:16px;margin-top:2px;flex-shrink:0;cursor:pointer;accent-color:var(--ai-brand)}}
  .ai-card-body{{flex:1}}
  .ai-card-title{{font-weight:700;font-size:13px;color:#1e1b3a;margin-bottom:3px}}
  .ai-card-meta{{font-size:11px;color:#6b7280;margin-bottom:7px}}
  .ai-card-footer{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
  .ai-badge{{padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700}}
  .ai-badge.open{{background:#fef9c3;color:#713f12}}
  .ai-badge.approved{{background:var(--ai-light);color:var(--ai-dark)}}
  .ai-badge.rejected{{background:#fee2e2;color:#991b1b}}
  .ai-priority.high{{color:#dc2626;font-weight:700;font-size:11px}}
  .ai-priority.medium{{color:#f59e0b;font-weight:700;font-size:11px}}
  .ai-priority.low{{color:#6b7280;font-size:11px}}
  .ai-amount{{font-weight:700;color:var(--ai-brand);font-size:12px;margin-left:auto}}
  .ai-since{{font-size:10.5px;color:#9ca3af}}
  .ai-actions{{display:flex;gap:6px;margin-left:auto}}
  .ai-action-btn{{padding:5px 12px;border-radius:5px;font-size:11px;font-weight:700;border:none;cursor:pointer}}
  .ai-action-btn.approve{{background:var(--ai-light);color:var(--ai-dark)}}
  .ai-action-btn.reject{{background:#fee2e2;color:#991b1b}}
  .ai-action-btn.view{{background:#f1f5f9;color:#334155}}
  .ai-empty{{text-align:center;padding:50px;color:#94a3b8}}
</style>

<div class="ai-wrap">

  {{#- ══ KPI ROW ════════════════════════════════════════════════════════════ -#}}
  <div class="ai-kpi-row">
    <div class="ai-kpi"><div class="ai-kpi-val">{{{{ counts.all or 0 }}}}</div><div class="ai-kpi-lbl">Total</div></div>
    <div class="ai-kpi pending"><div class="ai-kpi-val">{{{{ counts.pending or 0 }}}}</div><div class="ai-kpi-lbl">Pending</div></div>
    <div class="ai-kpi approved"><div class="ai-kpi-val">{{{{ counts.approved or 0 }}}}</div><div class="ai-kpi-lbl">Approved</div></div>
    <div class="ai-kpi rejected"><div class="ai-kpi-val">{{{{ counts.rejected or 0 }}}}</div><div class="ai-kpi-lbl">Rejected</div></div>
  </div>

  {{#- ══ TOOLBAR ═══════════════════════════════════════════════════════════ -#}}
  <div class="ai-toolbar">
    <button class="ai-tab active" data-status="all"      onclick="ai_filter_tab(this)">All</button>
    <button class="ai-tab"        data-status="Open"     onclick="ai_filter_tab(this)">Pending</button>
    <button class="ai-tab"        data-status="Approved" onclick="ai_filter_tab(this)">Approved</button>
    <button class="ai-tab"        data-status="Rejected" onclick="ai_filter_tab(this)">Rejected</button>
    <input class="ai-search" id="ai-search" placeholder="Search…" oninput="ai_search()">
    <button class="ai-btn-batch approve" onclick="ai_batch('Approved')">✅ Approve Selected</button>
    <button class="ai-btn-batch reject"  onclick="ai_batch('Rejected')">✗ Reject Selected</button>
  </div>

  {{#- ══ CARDS ═════════════════════════════════════════════════════════════ -#}}
  <div id="ai-cards-wrap">
    {{% for req in requests %}}
    <div class="ai-card" data-name="{{{{ req.name }}}}" data-status="{{{{ req.status }}}}">
      <input type="checkbox" class="ai-chk" value="{{{{ req.name }}}}">
      <div class="ai-card-body">
        <div class="ai-card-title">
          <a href="/app/{{{{ req.doctype|lower|replace(' ','-') }}}}/{{{{ req.document_name }}}}" target="_blank">{{{{ req.document_name }}}}</a>
          <span style="font-weight:400;color:#6b7280;font-size:11px"> — {{{{ req.doctype }}}}</span>
        </div>
        <div class="ai-card-meta">
          Submitted by <strong>{{{{ req.submitted_by }}}}</strong> · {{{{ req.pending_since or req.creation }}}}
          {{% if req.description %}} · {{{{ req.description }}}}{{% endif %}}
        </div>
        <div class="ai-card-footer">
          <span class="ai-badge {{{{ req.status|lower }}}}">{{{{ req.status }}}}</span>
          {{% if req.priority %}}
          <span class="ai-priority {{{{ req.priority|lower }}}}">{{{{ req.priority }}}}</span>
          {{% endif %}}
          {{% if req.amount %}}
          <span class="ai-amount">{{{{ frappe.format_value(req.amount, dict(fieldtype="Currency")) }}}}</span>
          {{% endif %}}
          <span class="ai-since">{{{{ req.workflow_state }}}}</span>
          <div class="ai-actions">
            <button class="ai-action-btn view"    onclick="ai_view('{{{{ req.doctype }}}}','{{{{ req.document_name }}}}')">View</button>
            <button class="ai-action-btn approve" onclick="ai_action('{{{{ req.name }}}}','Approved')">Approve</button>
            <button class="ai-action-btn reject"  onclick="ai_action('{{{{ req.name }}}}','Rejected')">Reject</button>
          </div>
        </div>
      </div>
    </div>
    {{% else %}}
    <div class="ai-empty">
      <div style="font-size:3rem;margin-bottom:10px">✅</div>
      <p>No pending approvals</p>
    </div>
    {{% endfor %}}
  </div>

</div>

<script>
/* ── Approval Inbox helpers ─────────────────────────────────────────────── */
var _ai_status_filter = "all";
function ai_filter_tab(btn) {{
    document.querySelectorAll(".ai-tab").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    _ai_status_filter = btn.dataset.status;
    ai_apply_filters();
}}
function ai_search() {{ ai_apply_filters(); }}
function ai_apply_filters() {{
    var q = document.getElementById("ai-search").value.toLowerCase();
    document.querySelectorAll(".ai-card").forEach(c => {{
        var statusOk = _ai_status_filter === "all" || c.dataset.status === _ai_status_filter;
        var textOk   = !q || c.textContent.toLowerCase().includes(q);
        c.style.display = statusOk && textOk ? "" : "none";
    }});
}}
function ai_view(doctype, name) {{
    frappe.set_route("Form", doctype, name);
}}
function ai_action(name, action) {{
    frappe.call({{
        method: "frappe.client.set_value",
        args: {{ doctype:"Workflow Action", name:name, fieldname:"status", value:action }},
        callback: () => {{
            var card = document.querySelector(`.ai-card[data-name="${{name}}"]`);
            if (card) {{ card.dataset.status = action; ai_apply_filters(); }}
            frappe.show_alert("{{{{ action }}}} " + name, "green");
        }}
    }});
}}
function ai_batch(action) {{
    var names = [...document.querySelectorAll(".ai-chk:checked")].map(c => c.value);
    if (!names.length) {{ frappe.show_alert("Select records first", "orange"); return; }}
    frappe.confirm(`${{action}} ${{names.length}} record(s)?`, () => {{
        names.forEach(n => ai_action(n, action));
    }});
}}
</script>
'''


def _desk_tpl_report_viewer(cc, title):
    """Report Viewer — dynamic DocType selector, filter builder, paginated table, CSV export."""
    return f'''<!-- ══ REPORT VIEWER DESK PRESET ═════════════════════════════════════════════
     Python context keys expected:
       report_title  str  — e.g. "Sales Invoice"
       columns       list — {{fieldname, label, fieldtype}}
       data          list — rows as dicts
       total_count   int
       page_no       int
       limit         int
     Pass filters from frontend via frappe.call args:
       doctype, filters (JSON), sort_by, sort_order, limit, page_no
═══════════════════════════════════════════════════════════════════════════ -->
<style>
  :root{{--rv-brand:#0369a1;--rv-light:#e0f2fe;--rv-dark:#0c4a6e;--rv-rad:10px;--rv-sh:0 4px 18px rgba(3,105,161,.10);}}
  .rv-wrap{{font-family:inherit;padding:0 4px}}
  .rv-toolbar{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:#fff;border-radius:var(--rv-rad);box-shadow:var(--rv-sh);padding:12px 16px;margin-bottom:14px}}
  .rv-dt-inp{{padding:7px 10px;border:1px solid #bae6fd;border-radius:6px;font-size:12px;background:var(--rv-light);outline:none;width:180px}}
  .rv-dt-inp:focus{{border-color:var(--rv-brand)}}
  .rv-btn{{padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;border:none;cursor:pointer;transition:filter .15s}}
  .rv-btn:hover{{filter:brightness(1.08)}}
  .rv-btn.primary{{background:var(--rv-brand);color:#fff}}
  .rv-btn.secondary{{background:var(--rv-light);color:var(--rv-dark)}}
  .rv-btn.export{{background:#f0fdf4;color:#15803d}}
  .rv-filters-wrap{{width:100%;display:none}}
  .rv-filters-wrap.open{{display:block}}
  .rv-filter-row{{display:flex;gap:6px;align-items:center;margin-bottom:6px}}
  .rv-filter-row select,.rv-filter-row input{{padding:5px 8px;border:1px solid #bae6fd;border-radius:5px;font-size:11.5px;outline:none;background:var(--rv-light)}}
  .rv-filter-row .rv-rm{{background:#fee2e2;color:#991b1b;border:none;border-radius:4px;padding:4px 8px;cursor:pointer;font-size:11px}}
  /* Table */
  .rv-table-wrap{{background:#fff;border-radius:var(--rv-rad);box-shadow:var(--rv-sh);overflow:hidden}}
  .rv-table-hdr{{padding:12px 16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--rv-light)}}
  .rv-table-title{{font-weight:700;font-size:13px;color:var(--rv-dark)}}
  .rv-count{{font-size:11px;color:#64748b}}
  .rv-table{{width:100%;border-collapse:collapse;font-size:12px}}
  .rv-table th{{background:var(--rv-light);color:var(--rv-dark);padding:9px 12px;text-align:left;font-weight:700;border-bottom:2px solid #bae6fd;cursor:pointer;white-space:nowrap}}
  .rv-table th:hover{{background:#bae6fd}}
  .rv-table th .sort-ico{{font-size:10px;margin-left:4px;opacity:.5}}
  .rv-table td{{padding:8px 12px;border-bottom:1px solid #f0f9ff;white-space:nowrap;overflow:hidden;max-width:200px;text-overflow:ellipsis}}
  .rv-table tr:hover td{{background:#f0f9ff}}
  /* Pagination */
  .rv-pagination{{display:flex;align-items:center;gap:8px;padding:10px 16px;border-top:1px solid var(--rv-light)}}
  .rv-pg-btn{{padding:5px 12px;border-radius:5px;border:1px solid #bae6fd;background:#fff;color:var(--rv-dark);font-size:12px;cursor:pointer;font-weight:700}}
  .rv-pg-btn:hover{{background:var(--rv-light)}}
  .rv-pg-btn:disabled{{opacity:.4;cursor:not-allowed}}
  .rv-pg-info{{font-size:11.5px;color:#64748b;margin:0 6px}}
  .rv-loading{{text-align:center;padding:30px;color:#94a3b8}}
</style>

<div class="rv-wrap">

  {{#- ══ TOOLBAR ════════════════════════════════════════════════════════════ -#}}
  <div class="rv-toolbar">
    <input id="rv-doctype" class="rv-dt-inp" value="{{{{ report_title }}}}" placeholder="DocType">
    <button class="rv-btn secondary" onclick="rv_toggle_filters()">🔽 Filters</button>
    <button class="rv-btn primary"   onclick="rv_run()">▶ Run</button>
    <button class="rv-btn export"    onclick="rv_export()">⬇ CSV</button>
    <select id="rv-limit" style="padding:7px;border:1px solid #bae6fd;border-radius:6px;font-size:12px;background:var(--rv-light)">
      <option>25</option><option selected>50</option><option>100</option><option>200</option>
    </select>
    <span class="rv-count" id="rv-total-label">{{{{ total_count }}}} records</span>
  </div>

  {{#- ══ FILTER BUILDER ════════════════════════════════════════════════════ -#}}
  <div id="rv-filters-wrap" class="rv-filters-wrap" style="background:#fff;border-radius:var(--rv-rad);box-shadow:var(--rv-sh);padding:12px 16px;margin-bottom:14px">
    <div id="rv-filter-rows"></div>
    <button class="rv-btn secondary" onclick="rv_add_filter()" style="font-size:11px;padding:5px 10px">+ Add Filter</button>
  </div>

  {{#- ══ TABLE ══════════════════════════════════════════════════════════════ -#}}
  <div class="rv-table-wrap">
    <div class="rv-table-hdr">
      <span class="rv-table-title" id="rv-tbl-title">{{{{ report_title }}}}</span>
    </div>
    <div id="rv-table-body">
      <table class="rv-table" id="rv-table">
        <thead>
          <tr>
            {{% for col in columns %}}
            <th onclick="rv_sort('{{{{ col.fieldname }}}}')">
              {{{{ col.label or col.fieldname }}}} <span class="sort-ico">↕</span>
            </th>
            {{% endfor %}}
          </tr>
        </thead>
        <tbody id="rv-tbody">
          {{% for row in data %}}
          <tr>
            {{% for col in columns %}}
            <td title="{{{{ row[col.fieldname] }}}}">{{{{ row[col.fieldname] or "—" }}}}</td>
            {{% endfor %}}
          </tr>
          {{% else %}}
          <tr><td colspan="{{{{ columns|length or 1 }}}}" style="text-align:center;padding:30px;color:#94a3b8">No records.</td></tr>
          {{% endfor %}}
        </tbody>
      </table>
    </div>
    <div class="rv-pagination">
      <button class="rv-pg-btn" id="rv-prev" onclick="rv_page(-1)" {{% if page_no <= 1 %}}disabled{{% endif %}}>&lsaquo; Prev</button>
      <span class="rv-pg-info" id="rv-pg-info">Page {{{{ page_no }}}} of {{{{ ((total_count / limit)|int + (1 if total_count % limit else 0)) or 1 }}}}</span>
      <button class="rv-pg-btn" id="rv-next" onclick="rv_page(1)" {{% if (page_no * limit) >= total_count %}}disabled{{% endif %}}>Next &rsaquo;</button>
    </div>
  </div>

</div>

<script>
/* ── Report Viewer ──────────────────────────────────────────────────────── */
var _rv_page = {{{{ page_no }}}};
var _rv_sort_by = "name", _rv_sort_ord = "desc";
var _rv_filters = [];
var _rv_method = "frappe_devkit.api.page_builder.get_{cc.replace("-","_")}";  // update to your fn

function rv_toggle_filters() {{
    var w = document.getElementById("rv-filters-wrap");
    w.classList.toggle("open");
    if (w.classList.contains("open") && !document.getElementById("rv-filter-rows").children.length)
        rv_add_filter();
}}
function rv_add_filter() {{
    var id = Date.now();
    var row = document.createElement("div");
    row.className = "rv-filter-row"; row.id = "rvf-" + id;
    row.innerHTML = `<input placeholder="Field" style="width:130px">
        <select><option>=</option><option>like</option><option>></option><option><</option><option>!=</option></select>
        <input placeholder="Value" style="width:130px">
        <button class="rv-rm" onclick="document.getElementById('rvf-${{id}}').remove()">✕</button>`;
    document.getElementById("rv-filter-rows").appendChild(row);
}}
function rv_build_filters() {{
    var rows = document.querySelectorAll("#rv-filter-rows .rv-filter-row");
    var filters = [];
    rows.forEach(r => {{
        var inputs = r.querySelectorAll("input, select");
        var field = inputs[0].value.trim(), op = inputs[1].value, val = inputs[2].value.trim();
        if (field && val) filters.push([field, op, val]);
    }});
    return filters;
}}
function rv_run(page) {{
    _rv_page = page || 1;
    var dt = document.getElementById("rv-doctype").value.trim();
    if (!dt) {{ frappe.show_alert("Enter DocType", "orange"); return; }}
    document.getElementById("rv-table-body").innerHTML = '<div class="rv-loading">Loading…</div>';
    frappe.call({{
        method: _rv_method,
        args: {{ doctype:dt, filters:JSON.stringify(rv_build_filters()),
                 sort_by:_rv_sort_by, sort_order:_rv_sort_ord,
                 limit:document.getElementById("rv-limit").value,
                 page_no:_rv_page }},
        callback: r => {{
            if (r.message) $(page.main).html(r.message);
        }}
    }});
}}
function rv_sort(field) {{
    if (_rv_sort_by === field) _rv_sort_ord = _rv_sort_ord === "asc" ? "desc" : "asc";
    else {{ _rv_sort_by = field; _rv_sort_ord = "asc"; }}
    rv_run(_rv_page);
}}
function rv_page(delta) {{ rv_run(_rv_page + delta); }}
function rv_export() {{
    var dt = document.getElementById("rv-doctype").value.trim();
    if (!dt) {{ frappe.show_alert("Enter DocType", "orange"); return; }}
    var params = new URLSearchParams({{ doctype:dt, file_type:"CSV",
        cmd:"frappe.desk.reportview.export_query" }});
    window.open("/api/method/frappe.desk.reportview.export_query?" + params);
}}
</script>
'''


def _desk_tpl_calendar_view(cc, title):
    """Calendar View — month grid with colour-coded events, prev/next nav, event create."""
    return f'''<!-- ══ CALENDAR VIEW DESK PRESET ═════════════════════════════════════════════
     Python context keys expected:
       current_month_name  str  — e.g. "March"
       current_year        int
       current_month       int  — 1..12
       calendar_weeks      list — [[ {{day, date, events:[{{title,color,category}}]}} ]]
     Navigation: reload page with ?year=&month= params
     Event categories get their colour from event["color"] (CSS colour string)
═══════════════════════════════════════════════════════════════════════════ -->
<style>
  :root{{--cal-brand:#9333ea;--cal-light:#f3e8ff;--cal-dark:#581c87;--cal-rad:10px;--cal-sh:0 4px 18px rgba(147,51,234,.10);}}
  .cal-wrap{{font-family:inherit;padding:0 4px}}
  .cal-header{{display:flex;align-items:center;gap:10px;background:#fff;border-radius:var(--cal-rad);box-shadow:var(--cal-sh);padding:12px 18px;margin-bottom:14px}}
  .cal-nav-btn{{background:var(--cal-light);color:var(--cal-dark);border:none;border-radius:6px;padding:6px 14px;font-size:14px;font-weight:700;cursor:pointer}}
  .cal-nav-btn:hover{{background:#e9d5ff}}
  .cal-title{{font-size:18px;font-weight:900;color:var(--cal-dark);flex:1;text-align:center}}
  .cal-btn-today{{background:var(--cal-brand);color:#fff;border:none;border-radius:6px;padding:6px 12px;font-size:12px;font-weight:700;cursor:pointer}}
  .cal-grid-wrap{{background:#fff;border-radius:var(--cal-rad);box-shadow:var(--cal-sh);overflow:hidden}}
  .cal-dow-row{{display:grid;grid-template-columns:repeat(7,1fr);border-bottom:2px solid var(--cal-light)}}
  .cal-dow{{padding:8px;text-align:center;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--cal-dark);background:var(--cal-light)}}
  .cal-week{{display:grid;grid-template-columns:repeat(7,1fr);border-bottom:1px solid #f3e8ff}}
  .cal-week:last-child{{border-bottom:none}}
  .cal-day{{min-height:90px;padding:6px;border-right:1px solid #f3e8ff;position:relative;vertical-align:top}}
  .cal-day:last-child{{border-right:none}}
  .cal-day.empty{{background:#fafafa}}
  .cal-day.today .cal-day-num{{background:var(--cal-brand);color:#fff;border-radius:50%;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center}}
  .cal-day-num{{font-size:12px;font-weight:700;color:#374151;margin-bottom:4px;display:inline-block}}
  .cal-day:hover{{background:#fdf4ff;cursor:pointer}}
  .cal-event{{display:block;padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;margin-bottom:2px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;cursor:pointer;color:#fff}}
  .cal-more{{font-size:10px;color:var(--cal-brand);font-weight:700;cursor:pointer;padding-left:2px}}
  .cal-legend{{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;background:#fff;border-radius:8px;padding:8px 14px;box-shadow:var(--cal-sh)}}
  .cal-legend-item{{display:flex;align-items:center;gap:5px;font-size:11px;color:#374151}}
  .cal-legend-dot{{width:10px;height:10px;border-radius:50%}}
</style>

<div class="cal-wrap">

  {{#- ══ HEADER / NAV ══════════════════════════════════════════════════════ -#}}
  <div class="cal-header">
    <button class="cal-nav-btn" onclick="cal_nav(-1)">‹</button>
    <span class="cal-title">{{{{ current_month_name }}}} {{{{ current_year }}}}</span>
    <button class="cal-nav-btn" onclick="cal_nav(1)">›</button>
    <button class="cal-btn-today" onclick="cal_today()">Today</button>
    <button class="cal-btn-today" style="background:#f3e8ff;color:var(--cal-dark)" onclick="cal_add_event()">+ Event</button>
  </div>

  {{#- ══ GRID ════════════════════════════════════════════════════════════ -#}}
  <div class="cal-grid-wrap">
    <div class="cal-dow-row">
      {{% for dow in ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"] %}}
      <div class="cal-dow">{{{{ dow }}}}</div>
      {{% endfor %}}
    </div>
    {{% for week in calendar_weeks %}}
    <div class="cal-week">
      {{% for cell in week %}}
      {{% if cell.day %}}
      <div class="cal-day{{% if cell.date == frappe.utils.today() %}} today{{% endif %}}"
           onclick="cal_day_click('{{{{ cell.date }}}}')">
        <span class="cal-day-num">{{{{ cell.day }}}}</span>
        {{% for ev in cell.events[:3] %}}
        <span class="cal-event"
              style="background:{{{{ ev.color or '#9333ea' }}}}"
              title="{{{{ ev.title }}}}"
              onclick="cal_event_click(event,'{{{{ ev.name or '' }}}}','{{{{ ev.category or '' }}}}')">
          {{{{ ev.title }}}}
        </span>
        {{% endfor %}}
        {{% if cell.events|length > 3 %}}
        <span class="cal-more">+{{{{ cell.events|length - 3 }}}} more</span>
        {{% endif %}}
      </div>
      {{% else %}}
      <div class="cal-day empty"></div>
      {{% endif %}}
      {{% endfor %}}
    </div>
    {{% endfor %}}
  </div>

  {{#- ══ LEGEND ════════════════════════════════════════════════════════════ -#}}
  <div class="cal-legend">
    <span style="font-size:11px;font-weight:700;color:#374151;margin-right:4px">Categories:</span>
    <span class="cal-legend-item"><span class="cal-legend-dot" style="background:#9333ea"></span>Task</span>
    <span class="cal-legend-item"><span class="cal-legend-dot" style="background:#0369a1"></span>Event</span>
    <span class="cal-legend-item"><span class="cal-legend-dot" style="background:#15803d"></span>Holiday</span>
    <span class="cal-legend-item"><span class="cal-legend-dot" style="background:#dc2626"></span>Deadline</span>
  </div>

</div>

<script>
/* ── Calendar helpers ────────────────────────────────────────────────────── */
var _cal_year  = {{{{ current_year }}}};
var _cal_month = {{{{ current_month }}}};

function cal_nav(delta) {{
    _cal_month += delta;
    if (_cal_month < 1)  {{ _cal_month = 12; _cal_year--; }}
    if (_cal_month > 12) {{ _cal_month = 1;  _cal_year++; }}
    window.location.search = `?year=${{_cal_year}}&month=${{_cal_month}}`;
}}
function cal_today() {{
    var now = new Date();
    window.location.search = `?year=${{now.getFullYear()}}&month=${{now.getMonth()+1}}`;
}}
function cal_day_click(date) {{
    frappe.msgprint(`Date: ${{date}}`);
}}
function cal_event_click(ev, name, cat) {{
    ev.stopPropagation();
    if (name && cat) frappe.set_route("Form", cat, name);
}}
function cal_add_event() {{
    frappe.prompt([
        {{ label:"Title",    fieldtype:"Data", reqd:1 }},
        {{ label:"Date",     fieldtype:"Date", reqd:1 }},
        {{ label:"Category", fieldtype:"Select", options:"Task\\nEvent\\nHoliday\\nDeadline", default:"Task" }},
    ], v => {{
        frappe.call({{
            method: "frappe.client.insert",
            args: {{ doc: {{ doctype:"Task", subject:v.Title, exp_end_date:v.Date }} }},
            callback: r => {{
                frappe.show_alert("Event created: " + r.message.name, "green");
                cal_today();
            }}
        }});
    }}, "Add Event");
}}
</script>
'''


def _desk_tpl_audit_trail(cc, title):
    """Audit Trail — filterable Version log with diff viewer and user filter."""
    return f'''<!-- ══ AUDIT TRAIL DESK PRESET ═══════════════════════════════════════════════
     Python context keys expected:
       audit_logs  list — {{name, doctype, docname, user, timestamp, action, changes}}
                          changes: [{{field, old, new}}]
     Filters applied server-side by re-calling get_{cc.replace("-","_")}(user=, doctype=,
       from_date=, to_date=, action=)
═══════════════════════════════════════════════════════════════════════════ -->
<style>
  :root{{--at-brand:#374151;--at-light:#f3f4f6;--at-accent:#6b7280;--at-rad:10px;--at-sh:0 4px 18px rgba(55,65,81,.08);}}
  .at-wrap{{font-family:inherit;padding:0 4px}}
  .at-filters{{display:flex;gap:8px;flex-wrap:wrap;background:#fff;border-radius:var(--at-rad);box-shadow:var(--at-sh);padding:12px 16px;margin-bottom:14px;align-items:flex-end}}
  .at-filter-group{{display:flex;flex-direction:column;gap:3px}}
  .at-label{{font-size:10.5px;font-weight:700;color:var(--at-accent)}}
  .at-inp{{padding:6px 10px;border:1px solid #e5e7eb;border-radius:6px;font-size:12px;outline:none;background:var(--at-light)}}
  .at-inp:focus{{border-color:var(--at-brand)}}
  .at-btn{{padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;border:none;cursor:pointer;align-self:flex-end}}
  .at-btn.primary{{background:var(--at-brand);color:#fff}}
  .at-btn.secondary{{background:var(--at-light);color:var(--at-brand)}}
  /* Timeline */
  .at-timeline{{position:relative;padding-left:28px}}
  .at-timeline::before{{content:"";position:absolute;left:10px;top:0;bottom:0;width:2px;background:linear-gradient(to bottom,#e5e7eb,transparent)}}
  .at-entry{{position:relative;margin-bottom:14px}}
  .at-entry::before{{content:"";position:absolute;left:-22px;top:6px;width:10px;height:10px;border-radius:50%;background:var(--at-brand);border:2px solid #fff;box-shadow:0 0 0 2px var(--at-brand)}}
  .at-entry.create::before{{background:#15803d}}
  .at-entry.delete::before{{background:#dc2626}}
  .at-entry.update::before{{background:#0369a1}}
  .at-card{{background:#fff;border-radius:var(--at-rad);box-shadow:var(--at-sh);padding:12px 16px;cursor:pointer;transition:box-shadow .15s}}
  .at-card:hover{{box-shadow:0 6px 22px rgba(55,65,81,.14)}}
  .at-card-hdr{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px}}
  .at-action-badge{{padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700}}
  .at-action-badge.create{{background:#dcfce7;color:#14532d}}
  .at-action-badge.update{{background:#dbeafe;color:#1e3a5f}}
  .at-action-badge.delete{{background:#fee2e2;color:#991b1b}}
  .at-docname{{font-weight:700;font-size:13px;color:#1e1b3a}}
  .at-doctype{{font-size:11px;color:#6b7280}}
  .at-time{{font-size:10.5px;color:#9ca3af;margin-left:auto}}
  .at-user{{font-size:11.5px;color:#374151}}
  .at-changes{{margin-top:8px;display:none;border-top:1px solid #f3f4f6;padding-top:8px}}
  .at-changes.open{{display:block}}
  .at-change-row{{display:grid;grid-template-columns:140px 1fr 1fr;gap:6px;font-size:11px;padding:3px 0;border-bottom:1px solid #f9fafb}}
  .at-change-field{{color:#6b7280;font-weight:700}}
  .at-change-old{{color:#dc2626;text-decoration:line-through;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .at-change-new{{color:#15803d;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .at-empty{{text-align:center;padding:50px;color:#94a3b8}}
  .at-expand{{font-size:10px;color:#6b7280;float:right;cursor:pointer;padding:0 4px}}
</style>

<div class="at-wrap">

  {{#- ══ FILTERS ═══════════════════════════════════════════════════════════ -#}}
  <div class="at-filters">
    <div class="at-filter-group">
      <label class="at-label">User</label>
      <input id="at-user" class="at-inp" placeholder="user@example.com" style="width:160px">
    </div>
    <div class="at-filter-group">
      <label class="at-label">DocType</label>
      <input id="at-doctype" class="at-inp" placeholder="Sales Invoice" style="width:140px">
    </div>
    <div class="at-filter-group">
      <label class="at-label">Action</label>
      <select id="at-action" class="at-inp">
        <option value="">All</option>
        <option>Create</option><option>Update</option><option>Delete</option><option>Submit</option>
      </select>
    </div>
    <div class="at-filter-group">
      <label class="at-label">From</label>
      <input id="at-from" type="date" class="at-inp">
    </div>
    <div class="at-filter-group">
      <label class="at-label">To</label>
      <input id="at-to" type="date" class="at-inp">
    </div>
    <button class="at-btn primary" onclick="at_run()">🔍 Search</button>
    <button class="at-btn secondary" onclick="at_clear()">✕ Clear</button>
  </div>

  {{#- ══ TIMELINE ══════════════════════════════════════════════════════════ -#}}
  <div class="at-timeline" id="at-timeline">
    {{% for log in audit_logs %}}
    <div class="at-entry {{{{ log.action|lower }}}}">
      <div class="at-card" onclick="at_toggle('at-chg-{{{{ loop.index }}}}')">
        <div class="at-card-hdr">
          <span class="at-action-badge {{{{ log.action|lower }}}}">{{{{ log.action }}}}</span>
          <span class="at-docname">{{{{ log.docname }}}}</span>
          <span class="at-doctype">{{{{ log.doctype }}}}</span>
          <span class="at-time">{{{{ log.timestamp }}}}</span>
        </div>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span class="at-user">👤 {{{{ log.user }}}}</span>
          {{% if log.changes %}}
          <span style="font-size:10.5px;color:#6b7280">{{{{ log.changes|length }}}} field(s) changed <span class="at-expand">▼</span></span>
          {{% endif %}}
        </div>
        {{% if log.changes %}}
        <div id="at-chg-{{{{ loop.index }}}}" class="at-changes">
          <div class="at-change-row" style="font-weight:700;color:#374151;border-bottom:2px solid #e5e7eb">
            <span>Field</span><span>Before</span><span>After</span>
          </div>
          {{% for ch in log.changes %}}
          <div class="at-change-row">
            <span class="at-change-field">{{{{ ch.field }}}}</span>
            <span class="at-change-old">{{{{ ch.old or "—" }}}}</span>
            <span class="at-change-new">{{{{ ch.new or "—" }}}}</span>
          </div>
          {{% endfor %}}
        </div>
        {{% endif %}}
      </div>
    </div>
    {{% else %}}
    <div class="at-empty">
      <div style="font-size:2.5rem;margin-bottom:10px">🔍</div>
      <p>No audit logs found.</p>
    </div>
    {{% endfor %}}
  </div>

</div>

<script>
/* ── Audit Trail helpers ────────────────────────────────────────────────── */
function at_toggle(id) {{
    var el = document.getElementById(id);
    if (el) el.classList.toggle("open");
}}
function at_run() {{
    var args = {{
        user:      document.getElementById("at-user").value,
        doctype:   document.getElementById("at-doctype").value,
        action:    document.getElementById("at-action").value,
        from_date: document.getElementById("at-from").value,
        to_date:   document.getElementById("at-to").value,
    }};
    frappe.call({{
        method: "frappe_devkit.api.page_builder.get_{cc.replace("-","_")}",  // update to your fn
        args: args,
        callback: r => {{ if (r.message) $(page.main).html(r.message); }}
    }});
}}
function at_clear() {{
    ["at-user","at-doctype","at-from","at-to"].forEach(id => document.getElementById(id).value="");
    document.getElementById("at-action").value = "";
    at_run();
}}
</script>
'''


def _desk_tpl_notification_center(cc, title):
    """Notification Hub — grouped read/unread notifications with bulk mark-as-read."""
    return f'''<!-- ══ NOTIFICATION CENTER DESK PRESET ═══════════════════════════════════════
     Python context keys expected:
       notification_groups  list — [{{date_label, items:[{{name,subject,type,is_read,
                                      from_user,age,document_type,document_name}}]}}]
       unread_count         int
     Tab filter passed via frappe.call arg "tab" (all|unread|mentions|system|workflow)
═══════════════════════════════════════════════════════════════════════════ -->
<style>
  :root{{--nc-brand:#b45309;--nc-light:#fef3c7;--nc-dark:#92400e;--nc-rad:10px;--nc-sh:0 4px 18px rgba(180,83,9,.10);}}
  .nc-wrap{{font-family:inherit;padding:0 4px;max-width:820px}}
  .nc-header{{display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap}}
  .nc-title{{font-size:20px;font-weight:900;color:var(--nc-dark);flex:1}}
  .nc-badge{{background:var(--nc-brand);color:#fff;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:700}}
  .nc-btn{{padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;border:none;cursor:pointer}}
  .nc-btn.primary{{background:var(--nc-brand);color:#fff}}
  .nc-btn.secondary{{background:var(--nc-light);color:var(--nc-dark)}}
  .nc-tabs{{display:flex;gap:4px;background:#fff;border-radius:var(--nc-rad);box-shadow:var(--nc-sh);padding:6px;margin-bottom:14px;flex-wrap:wrap}}
  .nc-tab{{padding:6px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;border:none;background:transparent;color:#6b7280;transition:all .15s}}
  .nc-tab.active,.nc-tab:hover{{background:var(--nc-brand);color:#fff}}
  /* Groups */
  .nc-group-label{{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--nc-dark);padding:6px 2px;margin-bottom:6px}}
  /* Notification item */
  .nc-item{{display:flex;gap:12px;align-items:flex-start;background:#fff;border-radius:8px;box-shadow:var(--nc-sh);padding:12px 14px;margin-bottom:8px;cursor:pointer;border-left:3px solid transparent;transition:all .15s}}
  .nc-item:hover{{box-shadow:0 6px 22px rgba(180,83,9,.14);transform:translateX(2px)}}
  .nc-item.unread{{border-left-color:var(--nc-brand);background:#fffbf0}}
  .nc-item.read{{opacity:.75}}
  .nc-icon{{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}}
  .nc-icon.mention{{background:#dbeafe}}
  .nc-icon.alert{{background:var(--nc-light)}}
  .nc-icon.workflow{{background:#dcfce7}}
  .nc-icon.default{{background:#f3f4f6}}
  .nc-body{{flex:1}}
  .nc-subject{{font-size:13px;font-weight:700;color:#1e1b3a;margin-bottom:3px}}
  .nc-item.read .nc-subject{{font-weight:400}}
  .nc-meta{{font-size:11px;color:#6b7280}}
  .nc-from{{font-weight:600;color:#374151}}
  .nc-actions{{display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0}}
  .nc-age{{font-size:10px;color:#9ca3af;white-space:nowrap}}
  .nc-mark-btn{{font-size:10px;color:var(--nc-brand);background:var(--nc-light);border:none;border-radius:4px;padding:3px 7px;cursor:pointer;white-space:nowrap}}
  .nc-type-badge{{padding:2px 7px;border-radius:20px;font-size:9.5px;font-weight:700}}
  .nc-type-badge.mention{{background:#dbeafe;color:#1e3a5f}}
  .nc-type-badge.alert{{background:var(--nc-light);color:var(--nc-dark)}}
  .nc-type-badge.workflow{{background:#dcfce7;color:#14532d}}
  .nc-empty{{text-align:center;padding:50px;color:#94a3b8}}
</style>

<div class="nc-wrap">

  {{#- ══ HEADER ════════════════════════════════════════════════════════════ -#}}
  <div class="nc-header">
    <span class="nc-title">🔔 Notifications</span>
    {{% if unread_count %}}
    <span class="nc-badge">{{{{ unread_count }}}} unread</span>
    {{% endif %}}
    <button class="nc-btn primary"   onclick="nc_mark_all()">✓ Mark all read</button>
    <button class="nc-btn secondary" onclick="nc_reload()">↻ Refresh</button>
  </div>

  {{#- ══ TABS ══════════════════════════════════════════════════════════════ -#}}
  <div class="nc-tabs">
    <button class="nc-tab active" data-tab="all"      onclick="nc_tab(this)">All</button>
    <button class="nc-tab"        data-tab="unread"   onclick="nc_tab(this)">Unread</button>
    <button class="nc-tab"        data-tab="mentions" onclick="nc_tab(this)">@Mentions</button>
    <button class="nc-tab"        data-tab="system"   onclick="nc_tab(this)">System</button>
    <button class="nc-tab"        data-tab="workflow" onclick="nc_tab(this)">Workflow</button>
  </div>

  {{#- ══ NOTIFICATION GROUPS ═══════════════════════════════════════════════ -#}}
  {{% if notification_groups %}}
    {{% for group in notification_groups %}}
    <div class="nc-group-label">{{{{ group.date_label }}}}</div>
    {{% for n in group.items %}}
    <div class="nc-item {{'unread' if not n.is_read else 'read'}}"
         data-name="{{{{ n.name }}}}"
         data-type="{{{{ n.type|lower }}}}"
         onclick="nc_open('{{{{ n.document_type }}}}','{{{{ n.document_name }}}}','{{{{ n.name }}}}')">
      <div class="nc-icon {{{{ 'mention' if n.type=='Mention' else 'workflow' if n.type=='Workflow Action' else 'alert' if n.type=='Alert' else 'default' }}}}">
        {{% if n.type == 'Mention' %}}💬
        {{% elif n.type == 'Workflow Action' %}}✅
        {{% elif n.type == 'Alert' %}}⚠️
        {{% else %}}🔔{{% endif %}}
      </div>
      <div class="nc-body">
        <div class="nc-subject">{{{{ n.subject }}}}</div>
        <div class="nc-meta">
          From <span class="nc-from">{{{{ n.from_user or "System" }}}}</span>
          {{% if n.document_type %}} · {{{{ n.document_type }}}}{{% endif %}}
          {{% if n.document_name %}} — {{{{ n.document_name }}}}{{% endif %}}
        </div>
      </div>
      <div class="nc-actions">
        <span class="nc-age">{{{{ n.age or "" }}}}</span>
        <span class="nc-type-badge {{{{ 'mention' if n.type=='Mention' else 'workflow' if n.type=='Workflow Action' else 'alert' }}}}">{{{{ n.type }}}}</span>
        {{% if not n.is_read %}}
        <button class="nc-mark-btn" onclick="nc_mark(event,'{{{{ n.name }}}}')">Mark read</button>
        {{% endif %}}
      </div>
    </div>
    {{% endfor %}}
    {{% endfor %}}
  {{% else %}}
  <div class="nc-empty">
    <div style="font-size:2.5rem;margin-bottom:10px">🔔</div>
    <p>No notifications</p>
  </div>
  {{% endif %}}

</div>

<script>
/* ── Notification Center helpers ────────────────────────────────────────── */
function nc_tab(btn) {{
    document.querySelectorAll(".nc-tab").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    var tab = btn.dataset.tab;
    frappe.call({{
        method: "frappe_devkit.api.page_builder.get_{cc.replace("-","_")}",  // update to your fn
        args: {{ tab: tab }},
        callback: r => {{ if (r.message) $(page.main).html(r.message); }}
    }});
}}
function nc_open(doctype, docname, name) {{
    // Mark as read then navigate
    if (name) frappe.call({{ method:"frappe.client.set_value",
        args:{{ doctype:"Notification Log", name:name, fieldname:"read", value:1 }} }});
    if (doctype && docname) frappe.set_route("Form", doctype, docname);
}}
function nc_mark(ev, name) {{
    ev.stopPropagation();
    frappe.call({{
        method: "frappe.client.set_value",
        args: {{ doctype:"Notification Log", name:name, fieldname:"read", value:1 }},
        callback: () => {{
            var el = document.querySelector(`.nc-item[data-name="${{name}}"]`);
            if (el) {{ el.classList.remove("unread"); el.classList.add("read"); }}
            frappe.show_alert("Marked as read", "green");
        }}
    }});
}}
function nc_mark_all() {{
    frappe.confirm("Mark all notifications as read?", () => {{
        frappe.call({{
            method: "frappe.client.set_value",
            args: {{ doctype:"Notification Log", name:"all", fieldname:"read", value:1 }},
            callback: () => {{
                document.querySelectorAll(".nc-item.unread").forEach(el => {{
                    el.classList.remove("unread"); el.classList.add("read");
                    var btn = el.querySelector(".nc-mark-btn");
                    if (btn) btn.remove();
                }});
                frappe.show_alert("All notifications marked as read", "green");
            }}
        }});
    }});
}}
function nc_reload() {{ window.location.reload(); }}
</script>
'''


def _desk_tpl_bulk_ops(cc, title):
    """Bulk Operations — select-all table with action chooser and progress bar."""
    return f'''<!-- ══ BULK OPS DESK PRESET ══════════════════════════════════════════════════
     Python context keys expected:
       records  list — {{name, status, owner, creation, grand_total}}
     Action handler (server-side):
       @frappe.whitelist()
       def bulk_action_{cc.replace("-","_")}(**kwargs):
           names  = frappe.parse_json(kwargs.get("names", "[]"))
           action = kwargs.get("action")   # submit | cancel | delete | assign | export
           ...
═══════════════════════════════════════════════════════════════════════════ -->
<style>
  :root{{--bo-brand:#dc2626;--bo-light:#fee2e2;--bo-dark:#991b1b;--bo-rad:10px;--bo-sh:0 4px 18px rgba(220,38,38,.08);}}
  .bo-wrap{{font-family:inherit;padding:0 4px}}
  .bo-toolbar{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:#fff;border-radius:var(--bo-rad);box-shadow:var(--bo-sh);padding:12px 16px;margin-bottom:14px}}
  .bo-search{{flex:1;min-width:160px;padding:7px 12px;border:1px solid #fecaca;border-radius:6px;font-size:12px;outline:none;background:#fff9f9}}
  .bo-search:focus{{border-color:var(--bo-brand)}}
  .bo-action-sel{{padding:7px 10px;border:1px solid #fecaca;border-radius:6px;font-size:12px;outline:none;background:#fff9f9;color:#374151}}
  .bo-btn{{padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;border:none;cursor:pointer;transition:filter .15s}}
  .bo-btn:hover{{filter:brightness(1.08)}}
  .bo-btn.run{{background:var(--bo-brand);color:#fff}}
  .bo-btn.run:disabled{{background:#fca5a5;cursor:not-allowed}}
  .bo-btn.secondary{{background:var(--bo-light);color:var(--bo-dark)}}
  .bo-selection-bar{{background:var(--bo-light);border:1px solid #fecaca;border-radius:6px;padding:7px 14px;font-size:12px;font-weight:700;color:var(--bo-dark);display:none;align-items:center;gap:8px}}
  .bo-selection-bar.visible{{display:flex}}
  /* Table */
  .bo-table-wrap{{background:#fff;border-radius:var(--bo-rad);box-shadow:var(--bo-sh);overflow:hidden}}
  .bo-table{{width:100%;border-collapse:collapse;font-size:12px}}
  .bo-table th{{background:var(--bo-light);color:var(--bo-dark);padding:9px 12px;text-align:left;font-weight:700;border-bottom:2px solid #fecaca}}
  .bo-table th:first-child{{width:36px}}
  .bo-table td{{padding:8px 12px;border-bottom:1px solid #fff5f5}}
  .bo-table tr:hover td{{background:#fff9f9}}
  .bo-table tr.selected td{{background:#fff5f5}}
  .bo-chk{{accent-color:var(--bo-brand);width:15px;height:15px;cursor:pointer}}
  .bo-status{{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700}}
  .bo-status.draft{{background:#f3f4f6;color:#374151}}
  .bo-status.submitted{{background:#dcfce7;color:#14532d}}
  .bo-status.cancelled{{background:#fee2e2;color:#991b1b}}
  .bo-status.open{{background:#fef9c3;color:#713f12}}
  /* Progress */
  .bo-progress-wrap{{display:none;background:#fff;border-radius:var(--bo-rad);box-shadow:var(--bo-sh);padding:16px 18px;margin-top:14px}}
  .bo-progress-wrap.visible{{display:block}}
  .bo-prog-label{{font-size:12px;font-weight:700;color:var(--bo-dark);margin-bottom:8px}}
  .bo-prog-bar-bg{{background:#fecaca;border-radius:6px;height:12px;overflow:hidden}}
  .bo-prog-bar{{height:100%;background:var(--bo-brand);width:0%;border-radius:6px;transition:width .3s}}
  .bo-prog-counts{{display:flex;gap:12px;margin-top:8px;font-size:11px}}
  .bo-prog-success{{color:#15803d;font-weight:700}}
  .bo-prog-fail{{color:#dc2626;font-weight:700}}
  .bo-empty{{text-align:center;padding:40px;color:#94a3b8}}
</style>

<div class="bo-wrap">

  {{#- ══ TOOLBAR ═══════════════════════════════════════════════════════════ -#}}
  <div class="bo-toolbar">
    <input class="bo-search" id="bo-search" placeholder="Search records…" oninput="bo_filter()">
    <select id="bo-action" class="bo-action-sel">
      <option value="">— choose action —</option>
      <option value="submit">Submit</option>
      <option value="cancel">Cancel</option>
      <option value="delete">Delete</option>
      <option value="assign">Assign</option>
      <option value="export">Export CSV</option>
    </select>
    <button class="bo-btn run" id="bo-run-btn" onclick="bo_run()" disabled>▶ Run on Selected</button>
    <button class="bo-btn secondary" onclick="bo_select_all()">Select All</button>
    <button class="bo-btn secondary" onclick="bo_deselect_all()">Deselect All</button>
  </div>

  {{#- ══ SELECTION BAR ═════════════════════════════════════════════════════ -#}}
  <div id="bo-selection-bar" class="bo-selection-bar">
    <span id="bo-sel-count">0</span> record(s) selected
    <button class="bo-btn secondary" style="padding:4px 10px;font-size:11px" onclick="bo_deselect_all()">✕ Clear</button>
  </div>

  {{#- ══ TABLE ══════════════════════════════════════════════════════════════ -#}}
  <div class="bo-table-wrap">
    <table class="bo-table">
      <thead>
        <tr>
          <th><input type="checkbox" class="bo-chk" id="bo-chk-all" onchange="bo_toggle_all(this)"></th>
          <th>Name</th>
          <th>Status</th>
          <th>Owner</th>
          <th>Amount</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody id="bo-tbody">
        {{% for rec in records %}}
        <tr id="bo-row-{{{{ rec.name }}}}" data-name="{{{{ rec.name }}}}">
          <td><input type="checkbox" class="bo-chk bo-row-chk" value="{{{{ rec.name }}}}" onchange="bo_on_chk()"></td>
          <td><a href="#" onclick="frappe.set_route('Form','{cc}','{{{{ rec.name }}}}');return false">{{{{ rec.name }}}}</a></td>
          <td>
            <span class="bo-status {{{{ 'submitted' if rec.docstatus==1 else 'cancelled' if rec.docstatus==2 else 'draft' }}}}">
              {{{{ rec.status or ("Submitted" if rec.docstatus==1 else "Cancelled" if rec.docstatus==2 else "Draft") }}}}
            </span>
          </td>
          <td>{{{{ rec.owner }}}}</td>
          <td>{{{{ frappe.format_value(rec.grand_total, dict(fieldtype="Currency")) if rec.grand_total else "—" }}}}</td>
          <td style="color:#6b7280;font-size:11px">{{{{ rec.creation }}}}</td>
        </tr>
        {{% else %}}
        <tr><td colspan="6" class="bo-empty">No records.</td></tr>
        {{% endfor %}}
      </tbody>
    </table>
  </div>

  {{#- ══ PROGRESS ══════════════════════════════════════════════════════════ -#}}
  <div id="bo-progress-wrap" class="bo-progress-wrap">
    <div class="bo-prog-label" id="bo-prog-label">Processing…</div>
    <div class="bo-prog-bar-bg"><div class="bo-prog-bar" id="bo-prog-bar"></div></div>
    <div class="bo-prog-counts">
      <span class="bo-prog-success">✓ <span id="bo-prog-ok">0</span> succeeded</span>
      <span class="bo-prog-fail">✗ <span id="bo-prog-fail">0</span> failed</span>
    </div>
  </div>

</div>

<script>
/* ── Bulk Ops helpers ───────────────────────────────────────────────────── */
function bo_get_selected() {{
    return [...document.querySelectorAll(".bo-row-chk:checked")].map(c => c.value);
}}
function bo_on_chk() {{
    var sel = bo_get_selected();
    var selBar = document.getElementById("bo-selection-bar");
    selBar.classList.toggle("visible", sel.length > 0);
    document.getElementById("bo-sel-count").textContent = sel.length;
    document.getElementById("bo-run-btn").disabled = sel.length === 0;
}}
function bo_toggle_all(chk) {{
    document.querySelectorAll(".bo-row-chk").forEach(c => {{
        var row = c.closest("tr");
        if (row.style.display !== "none") {{ c.checked = chk.checked; }}
    }});
    bo_on_chk();
}}
function bo_select_all() {{
    document.querySelectorAll(".bo-row-chk").forEach(c => c.checked = true);
    document.getElementById("bo-chk-all").checked = true;
    bo_on_chk();
}}
function bo_deselect_all() {{
    document.querySelectorAll(".bo-row-chk, #bo-chk-all").forEach(c => c.checked = false);
    bo_on_chk();
}}
function bo_filter() {{
    var q = document.getElementById("bo-search").value.toLowerCase();
    document.querySelectorAll("#bo-tbody tr").forEach(row => {{
        row.style.display = !q || row.textContent.toLowerCase().includes(q) ? "" : "none";
    }});
}}
function bo_run() {{
    var names  = bo_get_selected();
    var action = document.getElementById("bo-action").value;
    if (!names.length) {{ frappe.show_alert("Select at least one record", "orange"); return; }}
    if (!action)       {{ frappe.show_alert("Choose an action", "orange"); return; }}

    frappe.confirm(`Run "${{action}}" on ${{names.length}} record(s)?`, () => {{
        var prog = document.getElementById("bo-progress-wrap");
        prog.classList.add("visible");
        document.getElementById("bo-prog-bar").style.width = "0%";
        document.getElementById("bo-prog-ok").textContent   = "0";
        document.getElementById("bo-prog-fail").textContent = "0";

        frappe.call({{
            method: "frappe_devkit.api.page_builder.bulk_action_{cc.replace("-","_")}",  // update to your fn
            args: {{ names: JSON.stringify(names), action: action }},
            callback: r => {{
                if (!r.message) return;
                var ok   = (r.message.success || []).length;
                var fail = (r.message.failed  || []).length;
                document.getElementById("bo-prog-bar").style.width  = "100%";
                document.getElementById("bo-prog-ok").textContent   = ok;
                document.getElementById("bo-prog-fail").textContent = fail;
                document.getElementById("bo-prog-label").textContent =
                    `Done — ${{ok}} succeeded, ${{fail}} failed`;
                if (ok)   frappe.show_alert(`${{ok}} record(s) processed`, "green");
                if (fail) frappe.show_alert(`${{fail}} record(s) failed`, "red");
                // Grey-out processed rows
                (r.message.success || []).forEach(n => {{
                    var row = document.getElementById("bo-row-" + n);
                    if (row) row.style.opacity = ".4";
                }});
            }},
            error: e => {{
                document.getElementById("bo-prog-label").textContent = "Error: " + (e.message || "unknown");
                document.getElementById("bo-prog-bar").style.background = "#dc2626";
            }}
        }});
    }});
}}
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
    elif preset == 'dashboard':
        return _desk_tpl_dashboard(cc, title)
    elif preset == 'list_tool':
        return _desk_tpl_list_tool(cc, title)
    elif preset == 'form_tool':
        return _desk_tpl_form_tool(cc, title)
    elif preset == 'analytics':
        return _desk_tpl_analytics(cc, title)
    elif preset == 'settings':
        return _desk_tpl_settings(cc, title)
    elif preset == 'wizard':
        return _desk_tpl_wizard(cc, title)
    elif preset == 'kanban':
        return _desk_tpl_kanban(cc, title)
    elif preset == 'import_export':
        return _desk_tpl_import_export(cc, title)
    elif preset == 'approval_inbox':
        return _desk_tpl_approval_inbox(cc, title)
    elif preset == 'report_viewer':
        return _desk_tpl_report_viewer(cc, title)
    elif preset == 'calendar_view':
        return _desk_tpl_calendar_view(cc, title)
    elif preset == 'audit_trail':
        return _desk_tpl_audit_trail(cc, title)
    elif preset == 'notification_center':
        return _desk_tpl_notification_center(cc, title)
    elif preset == 'bulk_ops':
        return _desk_tpl_bulk_ops(cc, title)
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
