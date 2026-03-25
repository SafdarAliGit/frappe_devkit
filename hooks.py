app_name        = "frappe_devkit"
app_title       = "Frappe DevKit"
app_publisher   = "Safdar"
app_description = "Personal Frappe/ERPNext developer assistant — scaffold DocTypes, Reports, Apps, Fixtures, Hooks and more"
app_email       = ""
app_license     = "MIT"
app_version     = "1.0.0"
app_icon        = "octicon octicon-tools"
app_color       = "#5c4da8"

required_apps = ["frappe"]

after_install    = "frappe_devkit.setup.after_install"
before_uninstall = "frappe_devkit.setup.before_uninstall"
