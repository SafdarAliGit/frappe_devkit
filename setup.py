from setuptools import setup, find_packages

setup(
    name="frappe_devkit",
    version="1.0.0",
    description="Personal Frappe/ERPNext developer assistant",
    author="Safdar",
    author_email="",
    license="MIT",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["frappe"],
)
