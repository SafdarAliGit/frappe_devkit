import frappe


def after_install():
    # Remove any previously created DevKit Studio workspace
    _remove_workspace()
    frappe.db.commit()
    print("")
    print("=" * 60)
    print("  Frappe DevKit v1.0.0 installed!")
    print("  Access at: <your-site>/devkit-studio")
    print("=" * 60)
    print("")


def before_uninstall():
    _remove_workspace()
    frappe.db.commit()


def _remove_workspace():
    try:
        if frappe.db.exists("Workspace", "DevKit Studio"):
            frappe.delete_doc("Workspace", "DevKit Studio",
                              ignore_permissions=True, force=True)
    except Exception:
        pass
