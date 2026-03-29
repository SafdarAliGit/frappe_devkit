"""
Server Manager API for Frappe DevKit Studio.

Covers bench-level and system-level operations:
  - Nginx: setup, reload, port assignment, domain management
  - SSL: Let's Encrypt (auto), certbot (manual), custom certificate
  - Production: setup production, supervisor, systemd, fail2ban, firewall
  - Bench: update, restart, build, doctor
  - Multi-tenancy: DNS config, add/remove custom domains
  - Config: bench config, Redis/DB host settings, common_site_config

NOTE: Commands marked [SUDO] require the bench user to have passwordless sudo
configured. Run once: bench setup sudoers <user>
"""

import os
import json
import subprocess
import frappe


# ─── helpers ──────────────────────────────────────────────────────────────────
def _bench():
    return frappe.utils.get_bench_path()

def _sites():
    return os.path.join(_bench(), "sites")

def _run(cmd, cwd=None, timeout=120, env=None):
    """Run a command in the bench directory. Returns {returncode, stdout, stderr}."""
    r = subprocess.run(
        cmd,
        cwd=cwd or _bench(),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return {"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}

def _ok(msg, **kw):
    return {"status": "success", "message": msg, **kw}

def _err(msg, **kw):
    return {"status": "error", "message": msg, **kw}

def _result(label, r):
    if r["returncode"] == 0:
        return _ok(label, stdout=r["stdout"], stderr=r["stderr"])
    return _err(f"Failed: {label}", stdout=r["stdout"], stderr=r["stderr"])

def _read_txt(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


# ══════════════════════════════════════════════════════════════════════════════
# NGINX
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def setup_nginx():
    """
    bench setup nginx
    Regenerate the Nginx configuration file from bench's template.
    Must be run after:
    - Adding or removing a site
    - Changing a domain or port
    - Installing or renewing an SSL certificate
    - Enabling/disabling multitenancy
    Always follow with reload_nginx().
    """
    r = _run(["bench", "setup", "nginx"])
    return _result("Setup Nginx config", r)


@frappe.whitelist()
def reload_nginx():
    """
    bench setup reload-nginx
    Validate Nginx config syntax and reload the service.
    Equivalent to: nginx -t && service nginx reload
    """
    r = _run(["bench", "setup", "reload-nginx"])
    return _result("Reload Nginx", r)


@frappe.whitelist()
def test_nginx():
    """
    sudo nginx -t
    Test Nginx configuration syntax without reloading.
    Safe to call anytime — makes no changes.
    """
    try:
        r = _run(["sudo", "nginx", "-t"])
    except subprocess.TimeoutExpired:
        return _err("nginx -t timed out")
    return _result("Test Nginx config", r)


@frappe.whitelist()
def set_nginx_port(site, port):
    """
    bench set-nginx-port <site> <port>
    Assign a specific port to a site (port-based multi-tenancy).
    Run setup_nginx() + reload_nginx() after this.
    """
    try:
        port = int(port)
    except (ValueError, TypeError):
        return _err("Port must be a valid integer")
    r = _run(["bench", "set-nginx-port", site, str(port)])
    return _result(f"Set Nginx port {port} for '{site}'", r)


@frappe.whitelist()
def set_url_root(site, url):
    """
    bench set-url-root <site> <url>
    Set the canonical URL root for a site.
    Run setup_nginx() after this.
    """
    r = _run(["bench", "set-url-root", site, url])
    return _result(f"Set URL root '{url}' for '{site}'", r)


# ══════════════════════════════════════════════════════════════════════════════
# SSL / HTTPS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def setup_lets_encrypt(site, custom_domain=""):
    """
    sudo -H bench setup lets-encrypt <site>
    Issue a free Let's Encrypt certificate and configure Nginx automatically.

    Requirements:
    - DNS A record must resolve to this server
    - Port 80 must be publicly accessible
    - DNS multitenancy must be enabled: bench config dns_multitenant on

    Bench automatically adds a monthly cron for renewal.
    [SUDO] Requires passwordless sudo for the bench user.
    """
    cmd = ["sudo", "-H", "bench", "setup", "lets-encrypt", site]
    if custom_domain:
        cmd += ["--custom-domain", custom_domain]
    try:
        r = _run(cmd, timeout=180)
    except subprocess.TimeoutExpired:
        return _err("Let's Encrypt setup timed out")
    return _result(f"Let's Encrypt for '{site}'", r)


@frappe.whitelist()
def renew_lets_encrypt():
    """
    sudo bench renew-lets-encrypt
    Manually renew all Let's Encrypt certificates.
    Bench sets up auto-renewal via cron, but this forces immediate renewal.
    [SUDO] Requires passwordless sudo for the bench user.
    """
    try:
        r = _run(["sudo", "bench", "renew-lets-encrypt"], timeout=180)
    except subprocess.TimeoutExpired:
        return _err("Let's Encrypt renewal timed out")
    return _result("Renew Let's Encrypt certificates", r)


@frappe.whitelist()
def setup_wildcard_ssl():
    """
    bench setup wildcard-ssl
    Issue a wildcard SSL certificate for a multi-tenant bench
    where all sites share a common parent domain (*.example.com).
    """
    try:
        r = _run(["bench", "setup", "wildcard-ssl"], timeout=180)
    except subprocess.TimeoutExpired:
        return _err("Wildcard SSL setup timed out")
    return _result("Setup wildcard SSL", r)


@frappe.whitelist()
def certbot_issue(domain, extra_domains="", cert_only=0):
    """
    sudo certbot --nginx -d <domain>
    Issue a certificate using Certbot with the Nginx plugin.
    extra_domains: comma-separated additional SANs (e.g. www.example.com)
    cert_only=1: issue cert without modifying Nginx config.
    [SUDO] Requires passwordless sudo.
    """
    # Build base command: certonly = issue cert without writing nginx config changes
    subcommand = ["certonly", "--nginx"] if int(cert_only) else ["--nginx"]
    cmd = ["sudo", "certbot"] + subcommand + [
        "-d", domain, "--non-interactive", "--agree-tos",
        "--email", "admin@" + domain,
    ]
    if extra_domains:
        for d in extra_domains.split(","):
            d = d.strip()
            if d:
                cmd += ["-d", d]
    try:
        r = _run(cmd, timeout=180)
    except subprocess.TimeoutExpired:
        return _err("Certbot timed out")
    return _result(f"Certbot issue for '{domain}'", r)


@frappe.whitelist()
def certbot_renew(dry_run=0):
    """
    sudo certbot renew [--dry-run]
    Renew all Certbot-managed certificates.
    Use dry_run=1 to test without making changes.
    [SUDO] Requires passwordless sudo.
    """
    cmd = ["sudo", "certbot", "renew"]
    if int(dry_run):
        cmd.append("--dry-run")
    try:
        r = _run(cmd, timeout=180)
    except subprocess.TimeoutExpired:
        return _err("Certbot renew timed out")
    return _result("Certbot renew", r)


@frappe.whitelist()
def certbot_list():
    """
    sudo certbot certificates
    List all certificates managed by Certbot with their expiry dates.
    [SUDO] Requires passwordless sudo.
    """
    r = _run(["sudo", "certbot", "certificates"])
    return _result("Certbot list certificates", r)


@frappe.whitelist()
def certbot_delete(cert_name):
    """
    sudo certbot delete --cert-name <name>
    Remove a certificate from Certbot's management.
    [SUDO] Requires passwordless sudo.
    """
    r = _run(["sudo", "certbot", "delete", "--cert-name", cert_name,
              "--non-interactive"])
    return _result(f"Certbot delete '{cert_name}'", r)


@frappe.whitelist()
def set_ssl_certificate(site, cert_path):
    """
    bench set-ssl-certificate <site> <cert_path>
    Register a manually obtained SSL certificate file path with bench.
    Follow with setup_nginx() + reload_nginx().
    """
    if not os.path.isfile(cert_path):
        return _err(f"Certificate file not found: {cert_path}")
    r = _run(["bench", "set-ssl-certificate", site, cert_path])
    return _result(f"Set SSL certificate for '{site}'", r)


@frappe.whitelist()
def set_ssl_key(site, key_path):
    """
    bench set-ssl-key <site> <key_path>
    Register the private key path for a manually obtained SSL certificate.
    Follow with setup_nginx() + reload_nginx().
    """
    if not os.path.isfile(key_path):
        return _err(f"Key file not found: {key_path}")
    r = _run(["bench", "set-ssl-key", site, key_path])
    return _result(f"Set SSL key for '{site}'", r)


@frappe.whitelist()
def check_ssl_expiry(cert_path):
    """
    openssl x509 -enddate -noout -in <cert_path>
    Check the expiry date of an SSL certificate file.
    """
    if not os.path.isfile(cert_path):
        return _err(f"Certificate file not found: {cert_path}")
    r = _run(["openssl", "x509", "-enddate", "-noout", "-in", cert_path])
    return _result(f"SSL expiry for '{cert_path}'", r)


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTION SETUP
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def setup_production(user=""):
    """
    sudo bench setup production <user>
    Full one-command production setup:
    - Generates Nginx reverse proxy config
    - Sets up Supervisor to manage Frappe workers
    - Configures fail2ban for intrusion prevention
    Run once on a fresh server. <user> must be the Linux user owning the bench.
    [SUDO] Requires passwordless sudo.
    """
    if not user:
        user = os.environ.get("USER", "frappe")
    try:
        r = _run(["sudo", "bench", "setup", "production", user], timeout=300)
    except subprocess.TimeoutExpired:
        return _err("setup production timed out")
    return _result(f"Setup production for user '{user}'", r)


@frappe.whitelist()
def disable_production():
    """
    bench disable-production
    Remove Nginx and Supervisor configs.
    Use when switching back to development mode.
    """
    r = _run(["bench", "disable-production"])
    return _result("Disable production mode", r)


# ══════════════════════════════════════════════════════════════════════════════
# SUPERVISOR
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def setup_supervisor(skip_redis=0):
    """
    bench setup supervisor
    Regenerate the Supervisor config file.
    Run after adding a new site or changing worker counts.
    Follow with supervisor_action('reload').
    """
    cmd = ["bench", "setup", "supervisor"]
    if int(skip_redis):
        cmd.append("--skip-redis")
    r = _run(cmd)
    return _result("Setup Supervisor config", r)


@frappe.whitelist()
def supervisor_action(action, process="frappe:"):
    """
    sudo supervisorctl <action> [process]
    action: reload | restart | start | stop | status | reread | update
    process: defaults to 'frappe:' (all Frappe processes).
             Use a specific name like 'frappe:frappe-web' for single process.
    [SUDO] Requires passwordless sudo.
    """
    valid = {"reload", "restart", "start", "stop", "status", "reread", "update"}
    if action not in valid:
        return _err(f"Invalid action '{action}'. Valid: {', '.join(sorted(valid))}")

    if action in ("status", "reload", "reread", "update"):
        cmd = ["sudo", "supervisorctl", action]
    else:
        cmd = ["sudo", "supervisorctl", action, process]

    r = _run(cmd, timeout=60)
    return _result(f"Supervisor {action} '{process}'", r)


@frappe.whitelist()
def supervisor_status():
    """sudo supervisorctl status — show all Frappe process states."""
    r = _run(["sudo", "supervisorctl", "status"])
    processes = []
    for line in r["stdout"].splitlines():
        parts = line.split()
        if parts:
            processes.append({
                "name": parts[0],
                "state": parts[1] if len(parts) > 1 else "",
                "detail": " ".join(parts[2:]) if len(parts) > 2 else "",
            })
    return _result("Supervisor status", r) | {"processes": processes}


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEMD
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def setup_systemd():
    """
    bench setup systemd
    Generate systemd unit files for Frappe services.
    Alternative to Supervisor for process management on modern Linux.
    """
    r = _run(["bench", "setup", "systemd"])
    return _result("Setup systemd unit files", r)


@frappe.whitelist()
def systemd_action(action, unit="frappe-web"):
    """
    sudo systemctl <action> <unit>
    action: start | stop | restart | reload | status | enable | disable
    unit: frappe-web | frappe-worker | frappe-schedule | (any systemd unit name)
    [SUDO] Requires passwordless sudo.
    """
    valid = {"start", "stop", "restart", "reload", "status", "enable", "disable",
             "daemon-reload"}
    if action not in valid:
        return _err(f"Invalid action '{action}'. Valid: {', '.join(sorted(valid))}")

    if action == "daemon-reload":
        cmd = ["sudo", "systemctl", "daemon-reload"]
    else:
        cmd = ["sudo", "systemctl", action, unit]

    r = _run(cmd, timeout=60)
    return _result(f"Systemd {action} '{unit}'", r)


# ══════════════════════════════════════════════════════════════════════════════
# SECURITY: FIREWALL & FAIL2BAN
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def setup_firewall():
    """
    bench setup firewall
    Configure UFW firewall rules for a Frappe production server.
    Opens: 22 (SSH), 80 (HTTP), 443 (HTTPS). Blocks everything else.
    [SUDO] Requires passwordless sudo.
    """
    r = _run(["bench", "setup", "firewall"])
    return _result("Setup firewall (UFW)", r)


@frappe.whitelist()
def setup_fail2ban():
    """
    bench setup fail2ban
    Configure fail2ban to block brute-force login attempts.
    Protects Nginx and SSH from repeated failed auth attempts.
    """
    r = _run(["bench", "setup", "fail2ban"])
    return _result("Setup fail2ban", r)


@frappe.whitelist()
def setup_sudoers(user=""):
    """
    bench setup sudoers <user>
    Allow the bench user to restart Nginx and Supervisor without a sudo password.
    Run this once so server management commands work without manual sudo prompts.
    """
    if not user:
        user = os.environ.get("USER", "frappe")
    r = _run(["bench", "setup", "sudoers", user])
    return _result(f"Setup sudoers for '{user}'", r)


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-TENANCY & CUSTOM DOMAINS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def set_dns_multitenant(enable=1):
    """
    bench config dns_multitenant on|off
    Enable DNS-based multitenancy: each site served by its own domain.
    Disable for single-site or port-based routing.
    Run setup_nginx() + reload_nginx() after changing this.
    """
    mode = "on" if int(enable) else "off"
    r = _run(["bench", "config", "dns_multitenant", mode])
    return _result(f"DNS multitenancy {mode}", r)


@frappe.whitelist()
def add_domain(site, domain):
    """
    bench setup add-domain <domain> --site <site>
    Add a custom domain alias to an existing site.
    After this: run setup_nginx() + reload_nginx() + setup_lets_encrypt().
    """
    r = _run(["bench", "setup", "add-domain", domain, "--site", site])
    return _result(f"Add domain '{domain}' → '{site}'", r)


@frappe.whitelist()
def remove_domain(domain):
    """
    bench setup remove-domain <domain>
    Remove a custom domain from a site.
    Run setup_nginx() + reload_nginx() after.
    """
    r = _run(["bench", "setup", "remove-domain", domain])
    return _result(f"Remove domain '{domain}'", r)


@frappe.whitelist()
def sync_domains():
    """
    bench setup sync-domains
    Detect domain configuration changes and update Nginx accordingly.
    """
    r = _run(["bench", "setup", "sync-domains"])
    return _result("Sync domains", r)


# ══════════════════════════════════════════════════════════════════════════════
# BENCH CONFIG
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def bench_config(key, value):
    """
    bench config <key> <value>
    Set a bench-level configuration value.

    Common keys:
      serve_default_site on|off  — serve default site on port 80
      http_timeout <seconds>     — set Gunicorn HTTP timeout
      update_bench_on_update on|off
      restart_supervisor_on_update on|off
      restart_systemd_on_update on|off
    """
    r = _run(["bench", "config", key, str(value)])
    return _result(f"Bench config: {key} = {value}", r)


@frappe.whitelist()
def set_common_config(key, value):
    """
    bench config set-common-config -c <key> <value>
    Set a value in bench/sites/common_site_config.json.
    Applies to all sites unless overridden in site_config.json.
    """
    r = _run(["bench", "config", "set-common-config", "-c", key, str(value)])
    return _result(f"Common config: {key} = {value}", r)


@frappe.whitelist()
def remove_common_config(key):
    """
    bench config remove-common-config <key>
    Remove a key from common_site_config.json.
    """
    r = _run(["bench", "config", "remove-common-config", key])
    return _result(f"Remove common config key '{key}'", r)


# ══════════════════════════════════════════════════════════════════════════════
# REDIS & DATABASE HOST
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def set_mariadb_host(host):
    """bench set-mariadb-host <host> — point bench at an external MariaDB server."""
    r = _run(["bench", "set-mariadb-host", host])
    return _result(f"Set MariaDB host to '{host}'", r)


@frappe.whitelist()
def set_redis_host(redis_type, host):
    """
    Set a Redis host for a specific role.
    redis_type: cache | queue | socketio
    host format: hostname:port (e.g. redis-server:6379)
    """
    type_map = {
        "cache":   ["bench", "set-redis-cache-host", host],
        "queue":   ["bench", "set-redis-queue-host", host],
        "socketio":["bench", "set-redis-socketio-host", host],
    }
    if redis_type not in type_map:
        return _err(f"Invalid redis_type '{redis_type}'. Valid: cache, queue, socketio")
    r = _run(type_map[redis_type])
    return _result(f"Set Redis {redis_type} host to '{host}'", r)


@frappe.whitelist()
def setup_redis():
    """
    bench setup redis
    Regenerate Redis configuration files from bench's template.
    Run after changing Redis host settings.
    """
    r = _run(["bench", "setup", "redis"])
    return _result("Setup Redis config", r)


# ══════════════════════════════════════════════════════════════════════════════
# BENCH OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def bench_update(pull=0, build=0, patch=0, restart=0, reset=0, app=""):
    """
    bench update [options]
    Full update: pull latest code, rebuild assets, run migrations, restart workers.

    Selective flags (any combination):
      pull=1    — only pull latest code
      build=1   — only rebuild JS/CSS assets
      patch=1   — only run patches/migrations
      restart=1 — only restart services
      reset=1   — discard local uncommitted changes before pulling

    app: limit update to a specific app (e.g. 'erpnext')

    Recommended production workflow:
      1. set_maintenance_mode(site, 1)
      2. bench_update()
      3. set_maintenance_mode(site, 0)
    """
    cmd = ["bench", "update"]
    if int(pull):
        cmd.append("--pull")
    if int(build):
        cmd.append("--build")
    if int(patch):
        cmd.append("--patch")
    if int(restart):
        cmd.append("--restart")
    if int(reset):
        cmd.append("--reset")
    if app:
        cmd += ["--app", app]

    try:
        r = _run(cmd, timeout=900)
    except subprocess.TimeoutExpired:
        return _err("bench update timed out (>15 min)")
    return _result("Bench update", r)


@frappe.whitelist()
def bench_restart():
    """
    bench restart
    Restart all web, supervisor, and systemd process units.
    """
    try:
        r = _run(["bench", "restart"], timeout=120)
    except subprocess.TimeoutExpired:
        return _err("bench restart timed out")
    return _result("Bench restart", r)


@frappe.whitelist()
def bench_doctor():
    """
    bench doctor
    Diagnostic report: worker health, scheduler status, queue backlogs for all sites.
    Run when background jobs are stuck or emails are not sending.
    """
    r = _run(["bench", "doctor"], timeout=60)
    return _result("Bench doctor", r)


@frappe.whitelist()
def setup_backups_cron():
    """
    bench setup backups
    Add a system cron job that backs up all sites daily.
    Safe to run multiple times — idempotent.
    """
    r = _run(["bench", "setup", "backups"])
    return _result("Setup automated backup cron", r)


@frappe.whitelist()
def setup_requirements():
    """
    bench setup requirements
    Install/update all Python and Node.js dependencies for all apps.
    Run after adding a new app or after a dependency change.
    """
    try:
        r = _run(["bench", "setup", "requirements"], timeout=300)
    except subprocess.TimeoutExpired:
        return _err("setup requirements timed out")
    return _result("Setup requirements", r)


@frappe.whitelist()
def setup_env():
    """
    bench setup env
    Recreate the Python virtual environment.
    Use when the virtualenv is broken or after a Python version change.
    """
    try:
        r = _run(["bench", "setup", "env"], timeout=300)
    except subprocess.TimeoutExpired:
        return _err("setup env timed out")
    return _result("Setup Python virtual environment", r)


@frappe.whitelist()
def get_bench_info():
    """
    Collect key bench diagnostics in one call:
    - bench version
    - all sites and their installed apps
    - all apps in bench with versions
    - common_site_config.json (safe keys only)
    """
    bench_path = _bench()
    info = {}

    # bench version
    rv = _run(["bench", "--version"])
    info["bench_version"] = rv["stdout"].strip() or rv["stderr"].strip()

    # sites
    sites = []
    sites_path = _sites()
    if os.path.exists(sites_path):
        for name in sorted(os.listdir(sites_path)):
            sp = os.path.join(sites_path, name)
            cfg_p = os.path.join(sp, "site_config.json")
            if not os.path.isdir(sp) or not os.path.exists(cfg_p):
                continue
            try:
                with open(cfg_p) as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
            sites.append({
                "site": name,
                "db_type": cfg.get("db_type", "mariadb"),
                "installed": _read_txt(os.path.join(sp, "apps.txt")),
            })
    info["sites"] = sites

    # apps
    apps = []
    apps_dir = os.path.join(bench_path, "apps")
    if os.path.exists(apps_dir):
        for item in sorted(os.listdir(apps_dir)):
            if os.path.exists(os.path.join(apps_dir, item, item, "hooks.py")):
                apps.append(item)
    info["apps"] = apps

    # common config (safe)
    common_cfg_path = os.path.join(sites_path, "common_site_config.json")
    if os.path.exists(common_cfg_path):
        try:
            with open(common_cfg_path) as f:
                common_cfg = json.load(f)
            info["common_config"] = {k: v for k, v in common_cfg.items()
                                     if k not in ("db_password",)}
        except Exception:
            info["common_config"] = {}

    return _ok("Bench info", **info)
