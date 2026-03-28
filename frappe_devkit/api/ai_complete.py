"""
AI Code Completion API for Frappe DevKit Studio.

Provides inline code completions (ghost text) powered by Anthropic Claude.
Requires ANTHROPIC_API_KEY in site_config.json or environment variable.

site_config.json:
  { "anthropic_api_key": "sk-ant-..." }
"""
import frappe


def _api_key():
    key = frappe.conf.get("anthropic_api_key") or frappe.conf.get("ANTHROPIC_API_KEY")
    if not key:
        import os
        key = os.environ.get("ANTHROPIC_API_KEY", "")
    return key


def _lang_context(lang):
    ctx = {
        "python": (
            "You are an expert Frappe/ERPNext Python developer. "
            "Complete the Python code. Return ONLY the completion text (no markdown, no explanation). "
            "Keep completions concise (1-5 lines). Use Frappe idioms: frappe.db.*, frappe.get_doc, etc."
        ),
        "javascript": (
            "You are an expert Frappe/ERPNext JavaScript developer. "
            "Complete the JS code. Return ONLY the completion text (no markdown, no explanation). "
            "Keep completions concise (1-5 lines). Use Frappe JS idioms: frm.*, frappe.call, etc."
        ),
        "sql": (
            "You are an expert MariaDB/MySQL developer familiar with Frappe table naming (tab prefix). "
            "Complete the SQL query. Return ONLY the completion text (no markdown, no explanation). "
            "Keep completions concise (1-5 lines)."
        ),
        "html": (
            "You are an expert Jinja2/HTML developer for Frappe web templates. "
            "Complete the template. Return ONLY the completion text (no markdown, no explanation). "
            "Keep completions concise (1-5 lines)."
        ),
        "json": (
            "You are an expert in Frappe fixture JSON format. "
            "Complete the JSON. Return ONLY the completion text (no markdown, no explanation). "
            "Keep completions concise (1-3 lines)."
        ),
    }
    return ctx.get(lang, (
        "Complete the code. Return ONLY the completion text (no markdown, no explanation). "
        "Keep completions concise (1-5 lines)."
    ))


@frappe.whitelist()
def get_completion(prefix, suffix, lang, max_tokens=None):
    """
    Return an AI inline code completion for the given prefix/suffix context.

    prefix    : code before the cursor (last 2000 chars)
    suffix    : code after the cursor (next 500 chars)
    lang      : python | javascript | sql | html | json
    max_tokens: max tokens to generate (default 120)
    """
    key = _api_key()
    if not key:
        return {"completion": "", "provider": "none", "error": "No API key configured"}

    prefix  = (prefix or "")[-2000:]
    suffix  = (suffix or "")[:500]
    lang    = (lang or "python").lower()
    n_toks  = min(int(max_tokens or 120), 256)

    system_prompt = _lang_context(lang)

    user_message = (
        f"Complete the following {lang} code. "
        f"Return ONLY the completion that comes immediately after the cursor marker <CURSOR>. "
        f"Do not repeat code before the marker. Do not include any explanation.\n\n"
        f"```{lang}\n{prefix}<CURSOR>{suffix}\n```"
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=n_toks,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        completion = response.content[0].text if response.content else ""
        # Strip markdown fences if model added them
        if completion.startswith("```"):
            lines = completion.splitlines()
            inner = [l for l in lines[1:] if not l.startswith("```")]
            completion = "\n".join(inner)
        return {"completion": completion.rstrip(), "provider": "claude-haiku"}
    except ImportError:
        return {"completion": "", "provider": "none", "error": "anthropic package not installed. Run: pip install anthropic"}
    except Exception as e:
        frappe.log_error(str(e), "AI Complete")
        return {"completion": "", "provider": "none", "error": str(e)[:200]}
