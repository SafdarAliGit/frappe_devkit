import frappe
import os
import shutil
import subprocess
import datetime

ALLOWED_EXT = {
    '.py', '.js', '.html', '.css', '.json', '.txt', '.md',
    '.cfg', '.ini', '.toml', '.yaml', '.yml', '.sh', '.sql',
    '.ts', '.jsx', '.tsx', '.less', '.scss', '.xml', '.env',
}
EXCLUDED_DIRS = {
    '__pycache__', '.git', 'node_modules', '.eggs', 'dist',
    'build', '.tox', 'venv', 'env', '.venv', '.mypy_cache',
    '.pytest_cache', 'htmlcov', '.coverage', 'public',
}
HISTORY_KEEP = 50  # max snapshots per file


def _bench():
    return frappe.utils.get_bench_path()


def _app_base(app_name):
    """Return realpath of app directory, throws if not valid."""
    apps_root = os.path.join(_bench(), "apps")
    candidate = os.path.realpath(os.path.join(apps_root, app_name))
    apps_real = os.path.realpath(apps_root)
    if not candidate.startswith(apps_real + os.sep) and candidate != apps_real:
        frappe.throw("Invalid app name")
    if not os.path.isdir(candidate):
        frappe.throw(f"App not found: {app_name}")
    return candidate


def _safe_path(app_name, rel_path):
    """Resolve a relative file path inside app, raise if escaping."""
    base = _app_base(app_name)
    full = os.path.realpath(os.path.join(base, rel_path))
    if not full.startswith(base + os.sep) and full != base:
        frappe.throw("Access denied")
    return full


def _ext_ok(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in ALLOWED_EXT


@frappe.whitelist()
def get_apps():
    """Return list of all apps in bench."""
    apps_root = os.path.join(_bench(), "apps")
    apps = []
    try:
        for name in sorted(os.listdir(apps_root)):
            apath = os.path.join(apps_root, name)
            if os.path.isdir(apath) and not name.startswith('.'):
                has_hooks = os.path.exists(os.path.join(apath, "hooks.py"))
                apps.append({"name": name, "has_hooks": has_hooks})
    except PermissionError:
        pass
    return apps


@frappe.whitelist()
def get_file_tree(app_name, path=""):
    """Return one level of files/folders for the given path inside app."""
    base = _app_base(app_name)
    scan_dir = base if not path else _safe_path(app_name, path)

    items = []
    try:
        entries = sorted(os.scandir(scan_dir), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return []

    for entry in entries:
        name = entry.name
        if name.startswith('.'):
            continue
        rel = os.path.relpath(entry.path, base)
        if entry.is_dir(follow_symlinks=False):
            if name in EXCLUDED_DIRS or name.endswith('.egg-info'):
                continue
            items.append({"name": name, "path": rel, "type": "dir"})
        else:
            ext = os.path.splitext(name)[1].lower()
            if ext in ALLOWED_EXT:
                items.append({"name": name, "path": rel, "type": "file", "ext": ext.lstrip('.')})
    return items


@frappe.whitelist()
def read_file(app_name, file_path):
    """Return file content."""
    full = _safe_path(app_name, file_path)
    if not os.path.isfile(full):
        frappe.throw(f"File not found: {file_path}")
    if not _ext_ok(full):
        frappe.throw("File type not allowed")
    with open(full, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    ext = os.path.splitext(full)[1].lower()
    return {
        "content": content,
        "path": file_path,
        "name": os.path.basename(full),
        "size": os.path.getsize(full),
        "language": _get_language(ext),
    }


@frappe.whitelist()
def write_file(app_name, file_path, content):
    """Overwrite file with new content, saving history snapshot first."""
    full = _safe_path(app_name, file_path)
    if not _ext_ok(full):
        frappe.throw("File type not allowed")
    # Auto-save history before overwriting
    if os.path.isfile(full):
        try:
            with open(full, 'r', encoding='utf-8', errors='replace') as f:
                old_content = f.read()
            _save_to_history(app_name, file_path, old_content)
        except Exception:
            pass
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    return {"ok": True}


@frappe.whitelist()
def create_file(app_name, file_path, content=""):
    """Create a new file (must not already exist)."""
    full = _safe_path(app_name, file_path)
    if not _ext_ok(full):
        frappe.throw("File type not allowed")
    if os.path.exists(full):
        frappe.throw(f"File already exists: {file_path}")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    return {"ok": True}


@frappe.whitelist()
def rename_file(app_name, old_path, new_path):
    """Rename/move a file within the app."""
    old_full = _safe_path(app_name, old_path)
    new_full = _safe_path(app_name, new_path)
    if not os.path.exists(old_full):
        frappe.throw(f"File not found: {old_path}")
    if os.path.exists(new_full):
        frappe.throw(f"Destination already exists: {new_path}")
    os.makedirs(os.path.dirname(new_full), exist_ok=True)
    os.rename(old_full, new_full)
    return {"ok": True}


@frappe.whitelist()
def delete_file(app_name, file_path):
    """Delete a file."""
    full = _safe_path(app_name, file_path)
    if not os.path.isfile(full):
        frappe.throw(f"File not found: {file_path}")
    os.remove(full)
    return {"ok": True}


@frappe.whitelist()
def copy_item(app_name, src_path, dest_path):
    """Copy a file or folder to dest_path inside the app. Dest must not already exist."""
    src_full = _safe_path(app_name, src_path)
    dest_full = _safe_path(app_name, dest_path)
    if not os.path.exists(src_full):
        frappe.throw(f"Source not found: {src_path}")
    if os.path.exists(dest_full):
        frappe.throw(f"Destination already exists: {dest_path}")
    os.makedirs(os.path.dirname(dest_full), exist_ok=True)
    if os.path.isdir(src_full):
        shutil.copytree(src_full, dest_full)
    else:
        shutil.copy2(src_full, dest_full)
    return {"ok": True, "is_dir": os.path.isdir(dest_full)}


@frappe.whitelist()
def delete_dir(app_name, dir_path):
    """Delete a directory and all its contents."""
    full = _safe_path(app_name, dir_path)
    if not os.path.isdir(full):
        frappe.throw(f"Directory not found: {dir_path}")
    shutil.rmtree(full)
    return {"ok": True}


@frappe.whitelist()
def search_files(app_name, query, file_types="py,js,html,css,json"):
    """Full-text search across app files. Returns up to 200 matches."""
    base = _app_base(app_name)
    exts = {f".{e.strip()}" for e in file_types.split(",") if e.strip()}
    results = []
    q_lower = query.lower()

    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs
                   if d not in EXCLUDED_DIRS
                   and not d.endswith('.egg-info')
                   and not d.startswith('.')]
        for fname in sorted(files):
            if os.path.splitext(fname)[1].lower() not in exts:
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, base)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    for i, line in enumerate(f, 1):
                        if q_lower in line.lower():
                            idx = line.lower().find(q_lower)
                            results.append({
                                "file": rel,
                                "line": i,
                                "content": line.rstrip()[:200],
                                "match_start": idx,
                                "match_end": idx + len(query),
                            })
                            if len(results) >= 200:
                                return results
            except Exception:
                pass
    return results


@frappe.whitelist()
def get_git_status(app_name):
    """Return porcelain git status for app."""
    base = _app_base(app_name)
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=base, capture_output=True, text=True, timeout=10
        )
        changes = {}
        for line in r.stdout.splitlines():
            if len(line) >= 4:
                code = line[:2].strip()
                path = line[3:].strip()
                changes[path] = code
        branch_r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=base, capture_output=True, text=True, timeout=5
        )
        return {"changes": changes, "branch": branch_r.stdout.strip()}
    except Exception as e:
        return {"changes": {}, "branch": "", "error": str(e)}


@frappe.whitelist()
def get_git_diff(app_name, file_path=""):
    """Return git diff for file or all changes."""
    base = _app_base(app_name)
    cmd = ["git", "diff", "HEAD"]
    if file_path:
        cmd.append(file_path)
    try:
        r = subprocess.run(cmd, cwd=base, capture_output=True, text=True, timeout=15)
        return {"diff": r.stdout}
    except Exception as e:
        return {"diff": "", "error": str(e)}


@frappe.whitelist()
def format_python(content):
    """Format Python code using autopep8, black, or built-in ast normalization."""
    # Try autopep8 first
    try:
        import autopep8
        formatted = autopep8.fix_code(content, options={'aggressive': 1})
        return {"content": formatted, "ok": True, "formatter": "autopep8"}
    except ImportError:
        pass

    # Try black
    try:
        import black
        formatted = black.format_str(content, mode=black.Mode())
        return {"content": formatted, "ok": True, "formatter": "black"}
    except ImportError:
        pass
    except Exception as e:
        return {"content": content, "ok": False, "error": f"black: {e}"}

    # Fallback: re-indent using tokenize (fixes indentation only)
    try:
        import tokenize, io, textwrap
        # Just verify it's valid Python; return as-is if valid
        compile(content, '<string>', 'exec')
        return {"content": content, "ok": True, "formatter": "none (valid python, no formatter installed)"}
    except SyntaxError as e:
        return {"content": content, "ok": False, "error": f"Syntax error: {e}"}
    except Exception:
        pass

    return {"content": content, "ok": False, "error": "No Python formatter available (install autopep8 or black)"}


def _get_language(ext):
    return {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'javascript', '.tsx': 'typescript',
        '.html': 'html', '.css': 'css', '.less': 'less', '.scss': 'scss',
        '.json': 'json', '.md': 'markdown', '.txt': 'plaintext',
        '.sh': 'shell', '.yaml': 'yaml', '.yml': 'yaml',
        '.toml': 'ini', '.cfg': 'ini', '.ini': 'ini',
        '.sql': 'sql', '.xml': 'xml',
    }.get(ext, 'plaintext')


# ─────────────────────────────────────────────────────────────────────────────
# Local History
# ─────────────────────────────────────────────────────────────────────────────

def _history_dir(app_name, file_path):
    """Returns directory where history snapshots are stored for this file."""
    bench = _bench()
    norm_path = file_path.strip('/').strip('\\')
    return os.path.join(bench, '.devkit_history', app_name, norm_path)


def _save_to_history(app_name, file_path, content):
    """Internal: save content snapshot to history (called before every write)."""
    hdir = _history_dir(app_name, file_path)
    os.makedirs(hdir, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    with open(os.path.join(hdir, f'{ts}.snap'), 'w', encoding='utf-8') as f:
        f.write(content)
    # Trim to keep only the last HISTORY_KEEP snapshots
    try:
        snaps = sorted(s for s in os.listdir(hdir) if s.endswith('.snap'))
        for old in snaps[:-HISTORY_KEEP]:
            os.remove(os.path.join(hdir, old))
    except Exception:
        pass


@frappe.whitelist()
def get_history(app_name, file_path):
    """Return list of history snapshots for a file, newest first."""
    _safe_path(app_name, file_path)  # validate
    hdir = _history_dir(app_name, file_path)
    if not os.path.isdir(hdir):
        return []
    snaps = sorted((s for s in os.listdir(hdir) if s.endswith('.snap')), reverse=True)
    result = []
    for s in snaps[:HISTORY_KEEP]:
        ts_raw = s[:-5]  # remove .snap
        try:
            dt = datetime.datetime.strptime(ts_raw, '%Y%m%d_%H%M%S_%f')
            label = dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            label = ts_raw
        result.append({
            'id': ts_raw,
            'label': label,
            'size': os.path.getsize(os.path.join(hdir, s)),
        })
    return result


@frappe.whitelist()
def get_history_content(app_name, file_path, snapshot_id):
    """Return content of a history snapshot."""
    import re
    _safe_path(app_name, file_path)  # validate app + file
    if not re.match(r'^\d{8}_\d{6}_\d+$', snapshot_id):
        frappe.throw("Invalid snapshot ID")
    hdir = _history_dir(app_name, file_path)
    snap_path = os.path.join(hdir, f'{snapshot_id}.snap')
    real_snap = os.path.realpath(snap_path)
    real_hdir = os.path.realpath(hdir)
    if not real_snap.startswith(real_hdir + os.sep):
        frappe.throw("Access denied")
    if not os.path.isfile(real_snap):
        frappe.throw("Snapshot not found")
    with open(real_snap, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


# ─────────────────────────────────────────────────────────────────────────────
# Git — Full Operations
# ─────────────────────────────────────────────────────────────────────────────

def _git(app_name, cmd, timeout=30):
    """Run a git command in the app's directory."""
    base = _app_base(app_name)
    r = subprocess.run(cmd, cwd=base, capture_output=True, text=True, timeout=timeout)
    return r


@frappe.whitelist()
def git_stage_file(app_name, file_path):
    r = _git(app_name, ['git', 'add', '--', file_path])
    if r.returncode != 0:
        frappe.throw(r.stderr or 'git add failed')
    return {"ok": True}


@frappe.whitelist()
def git_unstage_file(app_name, file_path):
    r = _git(app_name, ['git', 'restore', '--staged', '--', file_path])
    if r.returncode != 0:
        frappe.throw(r.stderr or 'git restore --staged failed')
    return {"ok": True}


@frappe.whitelist()
def git_discard_file(app_name, file_path):
    r = _git(app_name, ['git', 'checkout', '--', file_path])
    if r.returncode != 0:
        frappe.throw(r.stderr or 'git checkout failed')
    return {"ok": True}


@frappe.whitelist()
def git_commit(app_name, message, stage_all=True):
    base = _app_base(app_name)
    if frappe.utils.cint(stage_all):
        r = subprocess.run(['git', 'add', '-A'], cwd=base, capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            frappe.throw(r.stderr or 'git add -A failed')
    r = subprocess.run(['git', 'commit', '-m', message],
                       cwd=base, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        frappe.throw(r.stderr or r.stdout or 'git commit failed')
    return {"ok": True, "output": r.stdout}


@frappe.whitelist()
def git_push(app_name, remote='origin', branch=''):
    cmd = ['git', 'push', remote]
    if branch:
        cmd.append(branch)
    r = _git(app_name, cmd, timeout=60)
    if r.returncode != 0:
        frappe.throw(r.stderr or 'git push failed')
    return {"ok": True, "output": (r.stdout + r.stderr).strip()}


@frappe.whitelist()
def git_pull(app_name, remote='origin', branch=''):
    cmd = ['git', 'pull', remote]
    if branch:
        cmd.append(branch)
    r = _git(app_name, cmd, timeout=60)
    if r.returncode != 0:
        frappe.throw(r.stderr or 'git pull failed')
    return {"ok": True, "output": (r.stdout + r.stderr).strip()}


@frappe.whitelist()
def git_log(app_name, limit=20):
    r = _git(app_name, [
        'git', 'log', f'--max-count={int(limit)}',
        '--pretty=format:%H|%an|%ae|%ar|%s'
    ], timeout=15)
    result = []
    for line in r.stdout.splitlines():
        parts = line.split('|', 4)
        if len(parts) == 5:
            result.append({
                'hash': parts[0][:8],
                'full_hash': parts[0],
                'author': parts[1],
                'email': parts[2],
                'time': parts[3],
                'message': parts[4],
            })
    return result


@frappe.whitelist()
def git_branches(app_name):
    r = _git(app_name, ['git', 'branch', '-a', '--format=%(refname:short)|%(HEAD)'])
    branches = []
    for line in r.stdout.splitlines():
        parts = line.split('|')
        name = parts[0].strip()
        is_current = len(parts) > 1 and parts[1].strip() == '*'
        if name:
            branches.append({'name': name, 'current': is_current})
    return branches


@frappe.whitelist()
def git_checkout(app_name, branch, create=False):
    cmd = ['git', 'checkout']
    if frappe.utils.cint(create):
        cmd.append('-b')
    cmd.append(branch)
    r = _git(app_name, cmd, timeout=30)
    if r.returncode != 0:
        frappe.throw(r.stderr or 'git checkout failed')
    return {"ok": True, "output": (r.stderr + r.stdout).strip()}


@frappe.whitelist()
def git_stash(app_name, action='save', message=''):
    if action == 'save':
        cmd = ['git', 'stash', 'push', '-m', message or 'devkit stash']
    elif action == 'pop':
        cmd = ['git', 'stash', 'pop']
    elif action == 'list':
        cmd = ['git', 'stash', 'list']
    else:
        frappe.throw('Unknown stash action')
    r = _git(app_name, cmd, timeout=30)
    if r.returncode != 0:
        frappe.throw(r.stderr or f'git stash {action} failed')
    return {"ok": True, "output": (r.stdout + r.stderr).strip()}


# ─────────────────────────────────────────────────────────────────────────────
# Claude AI Integration  (per-user API key, protected by Frappe login)
# ─────────────────────────────────────────────────────────────────────────────

_CLAUDE_DEFAULT_KEY = 'devkit_claude_api_key'


def _encrypt(text):
    """Encrypt using site key; falls back to plaintext on older installs."""
    try:
        from frappe.utils.password import encrypt as _enc
        return _enc(text)
    except Exception:
        return text


def _decrypt(text):
    """Decrypt using site key; falls back to plaintext on older installs."""
    try:
        from frappe.utils.password import decrypt as _dec
        return _dec(text)
    except Exception:
        return text


def _get_user_claude_key():
    """
    Resolve the active API key for the current request.
    Priority: per-user stored key  >  global site_config key.
    """
    enc = frappe.db.get_default(_CLAUDE_DEFAULT_KEY, parent=frappe.session.user)
    if enc:
        return _decrypt(enc)
    return frappe.conf.get('claude_api_key', '')


@frappe.whitelist()
def get_claude_status():
    """
    Return connection status for the current Frappe user.
    Shows which account is connected and a masked key preview.
    """
    user = frappe.session.user
    enc = frappe.db.get_default(_CLAUDE_DEFAULT_KEY, parent=user)
    has_user_key = bool(enc)
    has_global_key = bool(frappe.conf.get('claude_api_key', ''))

    if has_user_key:
        source = 'user'
        full_key = _decrypt(enc)
        masked = (full_key[:7] + '…' + full_key[-4:]) if len(full_key) > 11 else '***'
    elif has_global_key:
        source = 'global'
        gk = frappe.conf.get('claude_api_key', '')
        masked = (gk[:7] + '…' + gk[-4:]) if len(gk) > 11 else '***'
    else:
        source = 'none'
        masked = ''

    return {
        "configured": source != 'none',
        "source": source,          # 'user' | 'global' | 'none'
        "user": user,
        "user_full_name": frappe.db.get_value("User", user, "full_name") or user,
        "masked_key": masked,
    }


@frappe.whitelist()
def set_claude_api_key(api_key):
    """
    Save the Claude API key for the currently logged-in Frappe user.
    The key is encrypted and stored in the user's personal defaults,
    so it is fully isolated per account.
    """
    api_key = (api_key or '').strip()
    if not api_key:
        return {"ok": False, "error": "API key cannot be empty"}
    if not api_key.startswith('sk-ant-'):
        return {"ok": False, "error": "Invalid key format — Anthropic keys start with sk-ant-"}
    frappe.db.set_default(_CLAUDE_DEFAULT_KEY, _encrypt(api_key), parent=frappe.session.user)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def clear_claude_api_key():
    """Remove the current user's Claude API key."""
    frappe.db.set_default(_CLAUDE_DEFAULT_KEY, '', parent=frappe.session.user)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def claude_chat(message, code_context='', language='', file_path='', messages='[]', action=''):
    """Call Claude API for AI code assistance. Supports multi-turn conversation and targeted actions."""
    import json, urllib.request, urllib.error

    api_key = _get_user_claude_key()
    if not api_key:
        return {
            "ok": False,
            "error": "No Claude API key found. Connect your Anthropic account in the Claude panel.",
        }

    try:
        history = json.loads(messages) if messages else []
    except Exception:
        history = []

    # Action-specific system prompts for Windsurf-like targeted assistance
    _action_prompts = {
        'explain': (
            "You are an expert code explainer. Provide clear, structured explanations. "
            "Break down complex logic step by step. Highlight patterns, purpose, and any gotchas."
        ),
        'refactor': (
            "You are an expert code refactoring assistant. Improve code quality, readability, "
            "and maintainability. Apply SOLID principles, reduce duplication, use idiomatic patterns. "
            "Always show the complete refactored code followed by a summary of changes."
        ),
        'fix': (
            "You are an expert debugger. Identify ALL bugs, logic errors, and potential issues. "
            "For each issue: describe the problem, explain why it's wrong, provide the fix. "
            "Show the corrected complete code."
        ),
        'tests': (
            "You are an expert test engineer. Write comprehensive, well-structured tests. "
            "Cover: happy paths, edge cases, error conditions, boundary values. "
            "Use appropriate testing frameworks for the language. Include setup/teardown if needed."
        ),
        'docs': (
            "You are a technical documentation expert. Add clear, accurate docstrings and comments. "
            "Document: purpose, parameters (with types), return values, exceptions, side effects. "
            "Add inline comments for non-obvious logic. Follow language conventions (PEP257, JSDoc, etc)."
        ),
        'optimize': (
            "You are a performance optimization expert. Analyze time/space complexity. "
            "Identify bottlenecks and inefficiencies. Provide optimized version with Big-O analysis. "
            "Explain each optimization clearly."
        ),
        'complete': (
            "You are an expert code completion assistant. Continue the code naturally, "
            "matching the existing style, patterns, and conventions exactly. "
            "Complete the implementation fully and correctly."
        ),
    }

    base_system = (
        "You are an elite developer assistant integrated in DevKit, a Frappe/ERPNext IDE. "
        "You have deep expertise in Python, JavaScript, TypeScript, HTML, CSS, JSON, "
        "Frappe framework, ERPNext customization, and web development best practices. "
        "Always use fenced code blocks with the correct language tag for all code. "
        "Be direct and practical — show working code, not pseudocode."
    )

    system_prompt = _action_prompts.get(action, base_system) if action else base_system
    if action and action in _action_prompts:
        system_prompt = base_system + "\n\n" + _action_prompts[action]

    # Build user content
    if code_context:
        user_content = (
            f"File: `{file_path or 'unknown'}` ({language or 'text'})\n\n"
            f"```{language or 'text'}\n{code_context[:12000]}\n```\n\n{message}"
        )
    else:
        user_content = message

    # Build messages array using conversation history
    if history:
        api_messages = [m for m in history if m.get('role') in ('user', 'assistant')]
        if api_messages and api_messages[-1]['role'] == 'user':
            api_messages[-1]['content'] = user_content
        else:
            api_messages.append({'role': 'user', 'content': user_content})
    else:
        api_messages = [{'role': 'user', 'content': user_content}]

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 8096,
            "system": system_prompt,
            "messages": api_messages[-20:],
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return {"ok": True, "content": data['content'][0]['text']}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            err_msg = json.loads(body).get('error', {}).get('message', body)
        except Exception:
            err_msg = body[:300]
        return {"ok": False, "error": f"API error {e.code}: {err_msg}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Claude Inline Code Completion  — fast FIM completions using Claude Haiku
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def claude_complete(prefix, suffix='', language=''):
    """
    Fast inline code completion (fill-in-middle) using Claude Haiku.
    Returns only the raw code to insert at the cursor — no markdown, no explanation.
    """
    import json, urllib.request, urllib.error, re

    api_key = _get_user_claude_key()
    if not api_key:
        return {"ok": False, "completion": ""}

    prefix = (prefix or '')[-3000:]   # last 3000 chars of prefix
    suffix = (suffix or '')[:500]     # first 500 chars of suffix
    lang   = language or 'code'

    system_prompt = (
        "You are an expert inline code completion engine embedded in a code editor. "
        "Your ONLY job is to output the code that should be inserted at the cursor. "
        "Rules:\n"
        "- Output RAW CODE ONLY — no explanation, no markdown, no code fences.\n"
        "- Complete naturally from where the cursor is, matching the existing style.\n"
        "- Keep completions concise: 1-15 lines is ideal.\n"
        "- If completing a function/class, finish it properly.\n"
        "- Never repeat code already present before the cursor.\n"
        "- If nothing useful can be completed, output nothing."
    )

    user_msg = (
        f"Language: {lang}\n\n"
        f"Code before cursor:\n{prefix}\n\n"
        f"Code after cursor:\n{suffix}\n\n"
        f"Output only the completion to insert at the cursor:"
    )

    try:
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_msg}],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data     = json.loads(resp.read().decode("utf-8"))
            raw      = data["content"][0]["text"].strip()
            # Strip any accidental markdown fences
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "",        raw)
            return {"ok": True, "completion": raw.strip()}

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            err_msg = json.loads(body).get("error", {}).get("message", body)
        except Exception:
            err_msg = body[:200]
        return {"ok": False, "completion": "", "error": f"API {e.code}: {err_msg}"}
    except Exception as e:
        return {"ok": False, "completion": "", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Gemini Code AI — free inline completions (Google AI Studio key, no credit card)
# Free tier: 15 RPM · 1 M tokens/day  → plenty for inline completions
# ─────────────────────────────────────────────────────────────────────────────

_GEMINI_BASE = 'https://generativelanguage.googleapis.com/v1beta/models'

# Models ordered by preference: highest free-tier RPM first.
# gemini-1.5-flash-8b: 1500 RPM free — perfect for inline completions.
# The first model that responds without 404 will be cached for the session.
_GEMINI_CANDIDATES = [
    'gemini-1.5-flash-8b',
    'gemini-2.0-flash-lite',
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-1.5-pro',
]
_gemini_model_cache = {}   # api_key_prefix -> resolved model name


def _gemini_post(api_key, payload, timeout=15):
    """POST to Gemini generateContent. Auto-selects the best available model."""
    import urllib.request, urllib.error, json

    key_prefix = api_key[:12]
    model = _gemini_model_cache.get(key_prefix)

    if model:
        # Use cached model directly
        url = f'{_GEMINI_BASE}/{model}:generateContent?key={api_key}'
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))

    # No cached model — probe candidates in order
    last_err = None
    for candidate in _GEMINI_CANDIDATES:
        url = f'{_GEMINI_BASE}/{candidate}:generateContent?key={api_key}'
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data,
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                _gemini_model_cache[key_prefix] = candidate  # cache winner
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                last_err = e
                continue   # model not available — try next
            raise          # 400/403/429 etc. → propagate
    raise last_err or RuntimeError('No Gemini model available')


@frappe.whitelist()
def gemini_verify(api_key):
    """Quick ping to verify the API key works. Used by the frontend on first save."""
    import urllib.error
    try:
        payload = {
            'contents': [{'parts': [{'text': 'Reply with just: ok'}]}],
            'generationConfig': {'maxOutputTokens': 4, 'temperature': 0},
        }
        _gemini_post(api_key, payload, timeout=10)
        return {'ok': True}
    except urllib.error.HTTPError as e:
        # 429 = rate-limited → key is valid, just too many requests right now
        if e.code == 429:
            return {'ok': True}
        body = e.read().decode('utf-8', errors='replace')
        try:
            import json
            err_detail = json.loads(body).get('error', {}).get('message', body)
        except Exception:
            err_detail = body[:200]
        if e.code == 400 or 'API_KEY_INVALID' in err_detail:
            msg = 'Invalid API key — check it in Google AI Studio'
        elif e.code == 403:
            msg = 'Key not authorised — enable Generative Language API in Google Cloud Console'
        else:
            msg = f'HTTP {e.code}: {err_detail}'
        return {'ok': False, 'error': msg}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@frappe.whitelist()
def gemini_complete(prefix, suffix='', language='', api_key=''):
    """
    Inline FIM-style code completion via Gemini 2.0 Flash.
    Called by the Monaco inline completions provider on every pause in typing.
    """
    import urllib.error
    if not api_key:
        return {'ok': False, 'error': 'No API key', 'completion': ''}

    lang_label = language or 'code'

    # Clean FIM prompt — avoid XML tags which Gemini echoes back in the response
    prompt = (
        f"You are a {lang_label} code completion engine.\n"
        f"Continue the code EXACTLY where it is cut off. "
        f"Output ONLY the completion text — no explanation, no markdown fences, "
        f"no repeating of the existing code.\n\n"
        f"=== CODE BEFORE CURSOR ===\n{prefix}\n"
        f"=== CODE AFTER CURSOR ===\n{suffix}\n"
        f"=== COMPLETION (insert at cursor) ==="
    )

    try:
        payload = {
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {
                'temperature': 0.05,
                'topP': 0.9,
                'maxOutputTokens': 150,
                'stopSequences': ['=== CODE', '\n\n\n'],
            },
        }
        data = _gemini_post(api_key, payload, timeout=12)
        candidates = data.get('candidates', [])
        if not candidates:
            return {'ok': True, 'completion': ''}
        # finishReason 'STOP' or 'MAX_TOKENS' are both usable
        finish = candidates[0].get('finishReason', 'STOP')
        if finish not in ('STOP', 'MAX_TOKENS'):
            return {'ok': True, 'completion': ''}
        parts = candidates[0].get('content', {}).get('parts', [])
        text = parts[0].get('text', '').strip() if parts else ''
        # Strip any stray markdown fences Gemini occasionally adds
        if text.startswith('```'):
            lines = text.splitlines()
            text = '\n'.join(lines[1:-1] if lines and lines[-1].strip() == '```' else lines[1:])
        return {'ok': True, 'completion': text}
    except urllib.error.HTTPError as e:
        # 429 = rate-limited — silently skip, no ghost text shown
        if e.code == 429:
            return {'ok': True, 'completion': ''}
        return {'ok': False, 'error': f'HTTP {e.code}', 'completion': ''}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'completion': ''}


# ─────────────────────────────────────────────────────────────────────────────
# Ollama (free local AI) helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ollama_request(endpoint, path, payload=None, timeout=10):
    """Make a request to Ollama server. Returns parsed JSON or raises."""
    import urllib.request, json
    url = endpoint.rstrip('/') + path
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data,
                                     headers={'Content-Type': 'application/json'})
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


@frappe.whitelist()
def get_ollama_models(endpoint='http://localhost:11434'):
    """List models available in the local Ollama instance."""
    try:
        data = _ollama_request(endpoint, '/api/tags', timeout=5)
        models = [m['name'] for m in data.get('models', [])]
        return {'ok': True, 'models': models}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@frappe.whitelist()
def ollama_chat(message, code_context='', language='', file_path='',
                messages='[]', endpoint='http://localhost:11434',
                model='deepseek-coder'):
    """Send a chat message to Ollama. Supports multi-turn conversation."""
    import json

    try:
        history = json.loads(messages) if messages else []
    except Exception:
        history = []

    system_prompt = (
        "You are an expert developer assistant integrated in DevKit, "
        "a Frappe/ERPNext development tool. Help with Python, JavaScript, "
        "TypeScript, HTML, CSS, JSON, and Frappe framework patterns. "
        "Be concise and practical. When showing code examples, use fenced code blocks."
    )

    if code_context:
        user_content = (
            f"File: `{file_path or 'unknown'}` ({language or 'text'})\n\n"
            f"```{language or 'text'}\n{code_context[:8000]}\n```\n\n{message}"
        )
    else:
        user_content = message

    if history:
        api_messages = [m for m in history if m.get('role') in ('user', 'assistant')]
        if api_messages and api_messages[-1]['role'] == 'user':
            api_messages[-1]['content'] = user_content
        else:
            api_messages.append({'role': 'user', 'content': user_content})
    else:
        api_messages = [{'role': 'user', 'content': user_content}]

    try:
        payload = {
            'model': model,
            'messages': [{'role': 'system', 'content': system_prompt}] + api_messages[-20:],
            'stream': False,
        }
        data = _ollama_request(endpoint, '/api/chat', payload=payload, timeout=120)
        content = data.get('message', {}).get('content', '')
        return {'ok': True, 'content': content}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@frappe.whitelist()
def terminal_complete(partial='', cwd=''):
    """Return path/file completions for the last word in *partial*.

    Called on Tab keypress from the terminal panel.  Returns up to 40 matches,
    sorted with directories first.
    """
    import glob as _glob

    bench_path = os.path.realpath(_bench())

    def _work_dir():
        if not cwd:
            return bench_path
        candidate = os.path.realpath(os.path.join(bench_path, cwd))
        if candidate.startswith(bench_path) and os.path.isdir(candidate):
            return candidate
        return bench_path

    work_dir = _work_dir()

    # Determine the word being completed (last whitespace-delimited token)
    if not partial:
        word = ''
    elif partial[-1] == ' ':
        word = ''
    else:
        word = partial.split()[-1] if partial.split() else ''

    # Resolve base directory and prefix for the word
    if '/' in word:
        dir_part, prefix = word.rsplit('/', 1)
        if word.startswith('/'):
            base_dir = os.path.realpath('/' + dir_part.lstrip('/'))
        else:
            base_dir = os.path.realpath(os.path.join(work_dir, dir_part))
        dir_prefix = dir_part + '/'
    else:
        base_dir = work_dir
        prefix = word
        dir_prefix = ''

    # Security: keep within bench
    if not (base_dir == bench_path or base_dir.startswith(bench_path + os.sep)):
        return {'completions': []}

    try:
        entries = sorted(os.listdir(base_dir), key=lambda x: (not os.path.isdir(os.path.join(base_dir, x)), x.lower()))
    except OSError:
        return {'completions': []}

    completions = []
    for entry in entries:
        if not entry.startswith(prefix):
            continue
        if entry.startswith('.') and not prefix.startswith('.'):
            continue  # hide dotfiles unless explicitly typed
        full = os.path.join(base_dir, entry)
        rel = dir_prefix + entry
        if os.path.isdir(full):
            rel += '/'
        completions.append(rel)
        if len(completions) >= 40:
            break

    return {'completions': completions}


@frappe.whitelist()
def run_terminal_command(command='', cwd='', _resolve_cwd=''):
    """Run a shell command inside the bench directory and return stdout/stderr.

    ``cwd`` is a path relative to the bench root (or absolute, validated to stay
    inside the bench).  ``_resolve_cwd`` is used internally by the cd helper: when
    set the command is ignored and the function just resolves the new working dir.
    """
    bench_path = os.path.realpath(_bench())

    # Resolve the working directory
    def _resolve(base, rel):
        if not rel:
            return base
        if os.path.isabs(rel):
            candidate = os.path.realpath(rel)
        else:
            candidate = os.path.realpath(os.path.join(base, rel))
        # Must stay inside bench
        if not (candidate.startswith(bench_path + os.sep) or candidate == bench_path):
            return None
        if not os.path.isdir(candidate):
            return None
        return candidate

    work_dir = _resolve(bench_path, cwd) if cwd else bench_path
    if work_dir is None:
        work_dir = bench_path

    # cd helper: just validate + return new cwd
    if _resolve_cwd:
        new_dir = _resolve(work_dir, _resolve_cwd)
        if new_dir is None:
            return {'ok': False, 'error': f'cd: {_resolve_cwd}: No such file or directory'}
        rel = os.path.relpath(new_dir, bench_path)
        return {'ok': True, 'cwd': '' if rel == '.' else rel, 'stdout': '', 'stderr': '', 'exit_code': 0}

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        rel_cwd = os.path.relpath(work_dir, bench_path)
        return {
            'ok': True,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode,
            'cwd': '' if rel_cwd == '.' else rel_cwd,
        }
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'Command timed out (60 s)'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


@frappe.whitelist()
def ollama_complete(prefix, suffix='', language='', endpoint='http://localhost:11434',
                    model='deepseek-coder'):
    """Fill-in-the-middle code completion via Ollama. Used for inline ghost-text."""
    import json

    # Use FIM format — deepseek-coder / qwen2.5-coder / starcoder2 all support this
    fim_prompt = f"<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>"

    try:
        payload = {
            'model': model,
            'prompt': fim_prompt,
            'stream': False,
            'options': {
                'temperature': 0.1,
                'top_p': 0.9,
                'num_predict': 128,
                'stop': ['\n\n', '<|fim_middle|>', '<|fim_prefix|>', '<|fim_suffix|>',
                         '<|endoftext|>', '```'],
            },
            'raw': True,
        }
        data = _ollama_request(endpoint, '/api/generate', payload=payload, timeout=30)
        completion = data.get('response', '').rstrip()
        return {'ok': True, 'completion': completion}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'completion': ''}
