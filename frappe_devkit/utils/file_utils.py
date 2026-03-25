import os
import json
import frappe


def get_bench_path():
    return frappe.utils.get_bench_path()


def get_app_path(app_name):
    return os.path.join(get_bench_path(), "apps", app_name)


def get_module_path(app_name, module_name):
    module_folder = module_name.lower().replace(" ", "_")
    return os.path.join(get_app_path(app_name), app_name, module_folder)


def get_doctype_path(app_name, module_name, doctype_name):
    dt_folder = doctype_name.lower().replace(" ", "_")
    return os.path.join(get_module_path(app_name, module_name), "doctype", dt_folder)


def get_report_path(app_name, module_name, report_name):
    rp_folder = report_name.lower().replace(" ", "_")
    return os.path.join(get_module_path(app_name, module_name), "report", rp_folder)


def write_file(path, content, overwrite=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and not overwrite:
        return False
    with open(path, "w") as f:
        f.write(content)
    return True


def write_json(path, data, overwrite=False):
    return write_file(path, json.dumps(data, indent="\t", default=str), overwrite)


def ensure_init_py(directory):
    init_path = os.path.join(directory, "__init__.py")
    if not os.path.exists(init_path):
        os.makedirs(directory, exist_ok=True)
        with open(init_path, "w") as f:
            f.write("")


def read_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


def read_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r") as f:
        return f.read()


def append_to_file(path, content):
    if not os.path.exists(path):
        return write_file(path, content)
    with open(path, "a") as f:
        f.write(content)
    return True
