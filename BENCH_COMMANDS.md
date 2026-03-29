# Frappe Bench — Complete Developer Command Reference

> All commands assume bench is already installed and you are inside the bench directory (e.g. `~/bench15_exp`).
> Commands prefixed with `--site` target a specific site. Use `--site all` to apply to every site.

---

## Table of Contents

1. [Site Lifecycle](#1-site-lifecycle)
2. [App Management](#2-app-management)
3. [Database Operations](#3-database-operations)
4. [Backup & Restore](#4-backup--restore)
5. [Production & Server Setup](#5-production--server-setup)
6. [Nginx Configuration](#6-nginx-configuration)
7. [SSL / HTTPS](#7-ssl--https)
8. [Multi-Tenancy & Custom Domains](#8-multi-tenancy--custom-domains)
9. [Scheduler & Background Workers](#9-scheduler--background-workers)
10. [User Management](#10-user-management)
11. [Cache & Assets](#11-cache--assets)
12. [Config Management](#12-config-management)
13. [Database Console](#13-database-console)
14. [Data Import / Export](#14-data-import--export)
15. [Testing](#15-testing)
16. [Utilities & Diagnostics](#16-utilities--diagnostics)
17. [Quick Reference Cheatsheet](#17-quick-reference-cheatsheet)

---

## 1. Site Lifecycle

### Create a Site

```bash
bench new-site mysite.local
```

Creates a new site folder under `./sites/`, a new database, and installs Frappe.

```bash
# With custom credentials
bench new-site mysite.local \
  --admin-password secret \
  --db-root-password rootpass

# With a specific database name and user
bench new-site mysite.local \
  --db-name custom_db \
  --db-user custom_user \
  --db-password dbpass \
  --db-host localhost \
  --db-port 3306

# PostgreSQL instead of MariaDB
bench new-site mysite.local --db-type postgres

# Install an app immediately after site creation
bench new-site mysite.local --install-app erpnext

# Force create even if site/db already exists
bench new-site mysite.local --force

# Initialize from existing SQL dump
bench new-site mysite.local --source_sql /path/to/dump.sql
```

> **Guide:** Use `--admin-password` and `--db-root-password` in scripts so bench does not prompt interactively. Always use `--db-type postgres` explicitly when running on PostgreSQL to avoid the MariaDB default.

---

### Set Default Site

```bash
bench use mysite.local
```

Sets the default site so you can omit `--site` on subsequent commands.

> **Guide:** Useful in single-site benches. In multi-site setups, always specify `--site` explicitly to avoid running commands on the wrong site.

---

### Drop / Remove a Site

```bash
bench drop-site mysite.local --db-root-password rootpass
```

Takes a backup, drops the database, and moves the site folder to `./archived_sites/`.

```bash
# Skip backup before dropping
bench drop-site mysite.local --db-root-password rootpass --no-backup

# Archive to a custom path
bench drop-site mysite.local --db-root-password rootpass \
  --archived-sites-path /mnt/old-sites

# Force drop even if errors occur
bench drop-site mysite.local --db-root-password rootpass --force
```

> **Guide:** Never use `--no-backup` in production unless you have a recent backup already. The `archived_sites` folder retains the file structure so you can restore later.

---

### Reinstall a Site (Wipe & Fresh Install)

```bash
bench --site mysite.local reinstall \
  --yes \
  --mariadb-root-password rootpass \
  --admin-password adminpass
```

Wipes all data and reinstalls all currently installed apps from scratch. MariaDB only.

> **Guide:** Use for development resets. Never run this on production — it destroys all data permanently.

---

### Maintenance Mode

```bash
bench --site mysite.local set-maintenance-mode on
bench --site mysite.local set-maintenance-mode off
```

Shows a maintenance page to users. Use before running migrations or upgrades.

> **Guide:** Always enable maintenance mode before a `bench update` or `migrate` on a live site so users see a proper message instead of errors.

---

## 2. App Management

### Get an App from Git

```bash
bench get-app https://github.com/frappe/erpnext
bench get-app https://github.com/frappe/erpnext --branch version-15
bench get-app /path/to/local/app        # From local filesystem
```

Clones the repository into `./apps/` and registers it.

> **Guide:** Always specify `--branch` to lock to a tested version. Using the default branch in production can pull in untested changes.

---

### Install an App on a Site

```bash
bench --site mysite.local install-app erpnext
```

Installs an app (already in `./apps/`) onto a specific site. Runs schema migrations.

---

### Uninstall an App from a Site

```bash
bench --site mysite.local uninstall-app erpnext
```

Removes the app's data and schema from the site. The app code stays in `./apps/`.

---

### Remove an App from the Bench

```bash
bench remove-app erpnext
```

Deletes the app code from `./apps/` and rebuilds assets. The app must be uninstalled from all sites first.

---

### List Installed Apps

```bash
bench --site mysite.local list-apps      # Apps on a specific site
bench version                            # All apps and their versions in the bench
```

---

### Update Apps

```bash
bench update                             # Full update: pull + build + migrate + restart
bench update --pull                      # Pull latest code only
bench update --build                     # Rebuild assets only
bench update --patch                     # Run patches/migrations only
bench update --restart                   # Restart services only
bench update --reset                     # Discard local changes before pulling
bench update --app frappe                # Update only the frappe app
```

> **Guide:** Run `bench update` during low-traffic hours. On production, combine with maintenance mode:
> ```bash
> bench --site all set-maintenance-mode on
> bench update
> bench --site all set-maintenance-mode off
> ```

---

### Exclude / Include App from Updates

```bash
bench exclude-app erpnext               # Skip this app during bench update
bench include-app erpnext               # Re-enable updates for this app
```

---

### Manage Remote URLs

```bash
bench remote-urls                        # Show all apps' git remotes
bench remote-set-url erpnext https://github.com/your-fork/erpnext
bench remote-reset-url erpnext          # Reset back to official Frappe repo
```

---

### Switch Branch

```bash
bench switch-to-branch version-15 erpnext frappe
bench switch-to-develop                  # Switch Frappe + ERPNext to develop
```

> **Guide:** After switching branches, always run `bench update --patch --build` to apply any new migrations and rebuild assets.

---

## 3. Database Operations

### Run Migrations

```bash
bench --site mysite.local migrate
```

Applies all pending patches, syncs DB schema, fixtures, and search index.

```bash
bench --site mysite.local migrate --skip-search-index    # Faster, skip search rebuild
bench --site mysite.local migrate --skip-failing         # Skip broken patches (dev only)
```

> **Guide:** Run `migrate` after every `bench update`, app install, or app upgrade. In production, enable maintenance mode first.

---

### Clean Up Orphaned Tables

```bash
# Preview what would be removed (safe — no changes)
bench --site mysite.local trim-database --dry-run

# Remove tables with no matching DocType
bench --site mysite.local trim-database

# Output as JSON (useful for logging)
bench --site mysite.local trim-database --format json
```

> **Guide:** Run `--dry-run` first every time. Orphaned tables appear after uninstalling apps without a proper migration.

---

### Clean Up Orphaned Columns

```bash
# Preview orphaned columns
bench --site mysite.local trim-tables --dry-run

# Remove columns with no matching DocType field
bench --site mysite.local trim-tables
```

> **Guide:** Reduces backup size and query overhead. Always dry-run first. Back up before running without `--dry-run`.

---

### Change Table Engine / Row Format (MariaDB, v14+)

```bash
# Convert all tables to DYNAMIC row format
bench --site mysite.local transform-database --table all --row_format DYNAMIC

# Change a specific table to InnoDB
bench --site mysite.local transform-database \
  --table 'tabSales Invoice' --engine InnoDB

# Stop on first error
bench --site mysite.local transform-database --table all --row_format DYNAMIC --failfast
```

> **Guide:** Use `DYNAMIC` row format to support large index keys (Barracuda format). Required if MariaDB throws "Row size too large" errors.

---

## 4. Backup & Restore

### Backup a Site

```bash
bench --site mysite.local backup
```

Saves a compressed `.sql.gz` to `./sites/mysite.local/private/backups/`.

```bash
# Include public and private uploaded files
bench --site mysite.local backup --with-files

# Include files and compress as .tgz
bench --site mysite.local backup --with-files --compress

# Save to a specific directory
bench --site mysite.local backup --backup-path /mnt/backups

# Partial backup — only specific DocTypes
bench --site mysite.local backup --only 'ToDo,Note,Task'

# Partial backup — exclude specific DocTypes
bench --site mysite.local backup --exclude 'Error Log,Access Log,Activity Log'

# Backup all sites in this bench
bench backup-all-sites
bench backup-all-sites --with-files
```

> **Guide:** Schedule automated backups via:
> ```bash
> bench setup backups
> ```
> This adds a cron entry. For off-site storage, mount `/mnt/backups` as an S3 bucket or NFS share before backing up.

---

### Restore a Site

```bash
bench --site mysite.local restore /path/to/backup.sql.gz
```

Restores database from a backup file.

```bash
# Restore with files
bench --site mysite.local restore /path/to/backup.sql.gz \
  --with-public-files /path/to/public-files.tar \
  --with-private-files /path/to/private-files.tar

# Restore with custom admin password
bench --site mysite.local restore /path/to/backup.sql.gz \
  --admin-password newpassword

# Install additional apps after restore
bench --site mysite.local restore /path/to/backup.sql.gz \
  --install-app payments

# Force restore (ignore version warnings)
bench --site mysite.local restore /path/to/backup.sql.gz --force
```

> **Guide:** After restoring, always run `bench --site mysite.local migrate` to ensure the schema is up to date with the current codebase.

---

### Partial Restore (Specific DocTypes)

```bash
bench --site mysite.local partial-restore -v /path/to/partial_backup.sql.gz
```

Restores only the tables included in a partial backup (`--only` or `--exclude` backup).

---

### Set Up Automated Backups

```bash
bench setup backups
```

Adds a cron job that backs up all sites daily.

---

## 5. Production & Server Setup

### Full Production Setup

```bash
sudo bench setup production $USER
```

Configures Nginx, Supervisor, and fail2ban in one command. Run once on a fresh server.

> **Guide:** `$USER` must be the Linux user that owns the bench. This sets up:
> - Nginx reverse proxy with correct socket paths
> - Supervisor to manage Frappe workers and web processes
> - fail2ban to block brute-force attempts

---

### Disable Production Mode

```bash
bench disable-production
```

Removes Nginx and Supervisor configs. Use when switching back to development mode.

---

### Supervisor

```bash
bench setup supervisor                   # Generate Supervisor config
bench setup supervisor --skip-redis      # Supervisor config without Redis section

# Reload Supervisor after config changes
sudo supervisorctl reload

# Restart all Frappe processes
sudo supervisorctl restart frappe:

# Restart a specific process
sudo supervisorctl restart frappe:frappe-web

# Check status of all processes
sudo supervisorctl status
```

> **Guide:** Run `bench setup supervisor` again after adding a new site or changing worker counts, then reload supervisor.

---

### Systemd (alternative to Supervisor)

```bash
bench setup systemd                      # Generate systemd unit files

sudo systemctl daemon-reload
sudo systemctl enable frappe-web         # Enable on boot
sudo systemctl start frappe-web
sudo systemctl restart frappe-web
sudo systemctl status frappe-web
```

---

### Firewall & Security

```bash
bench setup firewall                     # Configure UFW firewall rules
bench setup fail2ban                     # Configure fail2ban intrusion prevention
bench setup ssh-port [port]              # Change SSH port (updates firewall too)
bench setup sudoers $(whoami)            # Allow bench to restart services without sudo password
```

---

## 6. Nginx Configuration

```bash
# Generate / regenerate Nginx config
bench setup nginx

# Validate config syntax and reload Nginx
bench setup reload-nginx

# Manually reload Nginx
sudo service nginx reload                # Debian/Ubuntu (SysV)
sudo systemctl reload nginx             # systemd

# Test Nginx config without reloading
sudo nginx -t

# Assign a specific port to a site
bench set-nginx-port mysite.local 8080

# Set URL root for a site
bench set-url-root mysite.local https://mysite.local
```

> **Guide:** Run `bench setup nginx` every time you:
> - Add or remove a site
> - Change a domain or port
> - Install or renew an SSL certificate
> - Enable/disable multitenancy
>
> Always follow with `sudo service nginx reload` (or `bench setup reload-nginx` which does both).

---

## 7. SSL / HTTPS

### Let's Encrypt (Recommended — Automatic)

```bash
# Issue certificate and configure Nginx automatically
sudo -H bench setup lets-encrypt mysite.local

# With a custom domain pointing to this site
sudo -H bench setup lets-encrypt mysite.local \
  --custom-domain mydomain.com

# Manual renewal (auto-renewal is added as a cron by bench)
sudo bench renew-lets-encrypt

# Wildcard certificate (multi-tenant bench)
bench setup wildcard-ssl
```

> **Guide:** Requirements for Let's Encrypt:
> - The domain must be publicly resolvable (DNS A record pointing to this server)
> - Port 80 must be open
> - DNS multitenancy must be enabled (`bench config dns_multitenant on`)
>
> Bench automatically adds a monthly cron for renewal. Check with `crontab -l`.

---

### Certbot (Standalone — Alternative)

```bash
# Auto-detect domains from Nginx config and issue certs
sudo certbot --nginx

# Issue cert for a specific domain
sudo certbot --nginx -d mysite.local -d www.mysite.local

# Issue cert only (do not modify Nginx config)
sudo certbot certonly --nginx -d mysite.local

# Renew all certificates
sudo certbot renew

# Dry-run renewal (test without issuing)
sudo certbot renew --dry-run

# List all managed certificates
sudo certbot certificates

# Revoke and delete a certificate
sudo certbot delete --cert-name mysite.local
```

> **Guide:** Use `bench setup lets-encrypt` when possible — it integrates with bench's Nginx config. Use `certbot` directly when you manage Nginx outside of bench or need more control over cert options.

---

### Manual SSL Certificate

```bash
# 1. Generate a private key and CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout mydomain.com.key \
  -out mydomain.com.csr

# 2. After receiving the cert from your CA, bundle the chain
cat your_certificate.crt intermediate.crt root.crt >> certificate_bundle.crt

# 3. Move files to a secure location
sudo mkdir -p /etc/nginx/conf.d/ssl
sudo mv mydomain.com.key /etc/nginx/conf.d/ssl/private.key
sudo mv certificate_bundle.crt /etc/nginx/conf.d/ssl/certificate_bundle.crt

# 4. Lock down the private key
sudo chown root /etc/nginx/conf.d/ssl/private.key
sudo chmod 600 /etc/nginx/conf.d/ssl/private.key

# 5. Register paths in bench
bench set-ssl-certificate mysite.local /etc/nginx/conf.d/ssl/certificate_bundle.crt
bench set-ssl-key mysite.local /etc/nginx/conf.d/ssl/private.key

# 6. Regenerate Nginx config and reload
bench setup nginx
sudo service nginx reload
```

> **Guide:** Manual certs require manual renewal. Set a calendar reminder 30 days before expiry. Check expiry with:
> ```bash
> openssl x509 -enddate -noout -in /etc/nginx/conf.d/ssl/certificate_bundle.crt
> ```

---

## 8. Multi-Tenancy & Custom Domains

### Enable DNS Multi-Tenancy

```bash
bench config dns_multitenant on          # Each site served by its own domain
bench config dns_multitenant off         # Single site or port-based routing
```

> **Guide:** Enable this before creating multiple sites. Each site's name must match its DNS hostname (e.g. site named `erp.company.com` served at `erp.company.com`).

---

### Port-Based Multi-Tenancy (No DNS required)

```bash
bench set-nginx-port site1.local 8080
bench set-nginx-port site2.local 8081
bench setup nginx
sudo service nginx reload
```

---

### Custom Domains

```bash
# Add a custom domain alias to an existing site
bench setup add-domain mydomain.com --site mysite.local

# Remove a custom domain
bench setup remove-domain mydomain.com

# Detect and sync domain changes
bench setup sync-domains

# After any domain change — always regenerate and reload
bench setup nginx
sudo service nginx reload
```

> **Guide:** After `add-domain`, set up SSL for the new domain too:
> ```bash
> sudo -H bench setup lets-encrypt mysite.local --custom-domain mydomain.com
> ```

---

## 9. Scheduler & Background Workers

### Scheduler Control

```bash
bench --site mysite.local enable-scheduler
bench --site mysite.local disable-scheduler

bench --site mysite.local scheduler pause      # Temporary pause
bench --site mysite.local scheduler resume
bench --site mysite.local scheduler disable    # Persistent disable
bench --site mysite.local scheduler enable
```

---

### Worker Processes

```bash
bench worker                             # Start a default worker
bench worker --queue short               # Start a short-queue worker
bench worker --queue long                # Start a long-queue worker
bench schedule                           # Start the scheduler process
```

---

### Job Management

```bash
bench --site mysite.local show-pending-jobs      # View queued jobs
bench --site mysite.local purge-jobs             # Clear all pending jobs
bench --site mysite.local ready-for-migration    # Check if jobs are pending before upgrade
bench --site mysite.local trigger-scheduler-event all   # Run all scheduled events now
bench --site mysite.local trigger-scheduler-event daily # Run daily events now
```

---

### Diagnostics

```bash
bench doctor                             # Show worker and scheduler health across all sites
```

> **Guide:** Run `bench doctor` when background jobs are stuck or emails are not sending. It shows which workers are alive and which queues have backlogs.

---

## 10. User Management

```bash
# Add a System Manager user
bench --site mysite.local add-system-manager email@example.com

# Add a user with specific first/last name
bench --site mysite.local add-user email@example.com \
  --first-name John \
  --last-name Doe

# Disable a user account
bench --site mysite.local disable-user email@example.com

# Reset Administrator password
bench --site mysite.local set-admin-password newpassword

# Set password for any user
bench --site mysite.local set-password email@example.com newpassword

# Force-log out all active users (all sessions destroyed)
bench --site mysite.local destroy-all-sessions
```

> **Guide:** Use `destroy-all-sessions` before a major update or when a security breach is suspected. Users will need to log in again.

---

## 11. Cache & Assets

### Cache

```bash
bench --site mysite.local clear-cache           # Clear application cache
bench --site all clear-cache                    # Clear cache on all sites
bench --site mysite.local clear-website-cache   # Clear website/portal page cache
```

> **Guide:** Clear cache after deploying code changes or when users see stale data. It is safe to run anytime with no data loss.

---

### Assets (JS/CSS)

```bash
bench build                              # Build all app assets
bench build --app frappe                 # Build a single app
bench build --app frappe --force         # Force full rebuild
bench watch                              # Watch for changes and auto-rebuild (dev only)
```

> **Guide:** Run `bench build` after:
> - Changing any `.js` or `.css` files
> - Installing or updating an app
> - Running `bench update`
>
> Do NOT use `bench watch` in production — it is a dev-only hot-reload tool.

---

### Search Index

```bash
bench --site mysite.local rebuild-global-search
```

> **Guide:** Run if global search returns no or incorrect results. Also run after a large data import.

---

## 12. Config Management

### Site Config

```bash
# View current effective config
bench --site mysite.local show-config

# Set a single config value
bench --site mysite.local set-config key value

# Set a JSON value (dict, list)
bench --site mysite.local set-config backup \
  '{"includes": ["ToDo","Note"]}' --parse

# Apply to all sites
bench --site all set-config developer_mode 0
```

---

### Common / Global Config

```bash
# Set global config (applies to all sites unless overridden)
bench set-config -g developer_mode 1
bench set-config -g allow_tests 1
bench set-config -g server_script_enabled 1

# Using the config subcommand
bench config set-common-config -c developer_mode 1
bench config remove-common-config developer_mode
```

---

### Bench-Level Config

| Command | Description |
|---|---|
| `bench config dns_multitenant on/off` | Toggle DNS multitenancy |
| `bench config serve_default_site on/off` | Serve default site on port 80 |
| `bench config http_timeout [seconds]` | Set Gunicorn HTTP timeout |
| `bench config update_bench_on_update on/off` | Auto-update bench CLI on `bench update` |
| `bench config restart_supervisor_on_update on/off` | Auto-restart supervisor after update |
| `bench config restart_systemd_on_update on/off` | Auto-restart systemd units after update |

---

### Redis & DB Host

```bash
bench set-mariadb-host hostname
bench set-redis-cache-host hostname:port
bench set-redis-queue-host hostname:port
bench set-redis-socketio-host hostname:port
bench setup redis                        # Regenerate Redis config files
```

---

## 13. Database Console

```bash
# Open interactive MariaDB shell for a site
bench --site mysite.local mariadb
bench --site mysite.local db-console    # Alias (auto-detects MariaDB or Postgres)

# Open interactive PostgreSQL shell
bench --site mysite.local postgres

# Run a one-off SQL query
bench --site mysite.local mariadb --execute "SELECT name FROM tabUser LIMIT 10;"
```

> **Guide:** Use the bench console instead of logging into MySQL/psql directly — it automatically selects the correct database, user, and credentials from `site_config.json`.

---

## 14. Data Import / Export

### Import

```bash
bench --site mysite.local data-import \
  --doctype Customer \
  --file /path/to/customers.csv

bench --site mysite.local import-doc /path/to/document.json    # Single doc from JSON
bench --site mysite.local import-csv /path/to/data.csv         # Raw CSV import
```

---

### Export

```bash
bench --site mysite.local export-csv \
  --doctype Customer \
  --path /path/to/export.csv

bench --site mysite.local export-doc Customer "CUST-0001"      # Export single doc
bench --site mysite.local export-json --doctype Customer        # Export as JSON
bench --site mysite.local export-fixtures --app myapp           # Export app fixture data
```

---

### Bulk Rename

```bash
bench --site mysite.local bulk-rename Customer /path/to/rename.csv
```

CSV format: `old_name,new_name` per row.

---

## 15. Testing

```bash
# Enable test mode first (required)
bench --site mysite.local set-config allow_tests true

# Run all tests for a site
bench --site mysite.local run-tests

# Run tests for a specific app
bench --site mysite.local run-tests --app erpnext

# Run a specific test module
bench --site mysite.local run-tests \
  --app erpnext \
  --module erpnext.accounts.doctype.sales_invoice.test_sales_invoice

# Run tests in parallel (CI)
bench --site mysite.local run-parallel-tests --app erpnext

# Run Cypress UI tests
bench --site mysite.local run-ui-tests --app frappe

# Open Jupyter for interactive exploration
bench --site mysite.local jupyter
```

> **Guide:** Never leave `allow_tests true` enabled on production — it exposes test endpoints. Disable after testing:
> ```bash
> bench --site mysite.local set-config allow_tests false
> ```

---

## 16. Utilities & Diagnostics

### Execute Python Methods

```bash
bench --site mysite.local execute frappe.clear_cache
bench --site mysite.local execute frappe.db.count --args '["User"]'
bench --site mysite.local execute frappe.db.get_value \
  --kwargs '{"doctype":"User","filters":{"name":"Administrator"},"fieldname":"email"}'
```

---

### Permissions

```bash
bench --site mysite.local reset-perms   # Reset all DocType permissions to app defaults
```

---

### Patches

```bash
bench --site mysite.local run-patch frappe.patches.v14.drop_data_import_legacy
```

> **Guide:** Use when a specific patch failed during `migrate` and needs to be re-run manually.

---

### Realtime & Events

```bash
bench --site mysite.local publish-realtime [event] [message]
bench --site mysite.local trigger-scheduler-event [event]
```

---

### Misc

```bash
bench --site mysite.local browse                          # Open site in default browser
bench add-to-hosts mysite.local                          # Add site to /etc/hosts
bench --site mysite.local add-to-email-queue admin@example.com  # Queue a test email
bench --site mysite.local reload-doctype [DocType]       # Reload DocType schema
bench --site mysite.local reload-doc [module] [doctype] [name]  # Reload specific doc
bench --site mysite.local request [api-path]             # Make authenticated API request
bench ngrok                                               # Create a public tunnel URL (dev)
bench console                                             # IPython console with Frappe context
```

---

## 17. Quick Reference Cheatsheet

### Every-Day Development

```bash
bench start                                          # Start all processes
bench --site mysite.local clear-cache               # Clear cache
bench build --app myapp                             # Rebuild JS/CSS
bench --site mysite.local migrate                   # Apply migrations
bench --site mysite.local mariadb                   # DB console
bench --site mysite.local execute frappe.clear_cache
```

### Every-Day Production Operations

```bash
bench --site mysite.local backup --with-files       # Backup
bench backup-all-sites                              # Backup all
bench doctor                                        # Health check
bench --site mysite.local show-pending-jobs         # Check job queue
sudo supervisorctl status                           # Process status
sudo nginx -t && sudo service nginx reload          # Validate + reload Nginx
```

### Safe Update Workflow (Production)

```bash
bench --site all set-maintenance-mode on
bench update
bench --site all set-maintenance-mode off
bench --site all clear-cache
```

### Add a New Site with SSL

```bash
bench new-site newsite.example.com --admin-password secret
bench --site newsite.example.com install-app erpnext
bench config dns_multitenant on                            # if not already
bench setup nginx
sudo service nginx reload
sudo -H bench setup lets-encrypt newsite.example.com
```

### Restore from Backup

```bash
bench new-site restored.local --admin-password secret
bench --site restored.local restore /path/to/backup.sql.gz \
  --with-public-files /path/to/public.tar \
  --with-private-files /path/to/private.tar
bench --site restored.local migrate
```

### Fix Nginx After Any Change

```bash
bench setup nginx
sudo nginx -t                            # Verify config is valid before reloading
sudo service nginx reload
```

### Emergency: Clear Everything Stuck

```bash
bench --site mysite.local purge-jobs
bench --site mysite.local clear-cache
sudo supervisorctl restart frappe:
bench doctor
```

---

*Reference: [docs.frappe.io/framework](https://docs.frappe.io/framework/user/en/introduction)*
