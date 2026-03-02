"""
setup.py

Beschrijving: Setup script (backwards compatibility)
Applicatie: networkmanager
Versie: 1.0.0
Auteur: Barremans
"""

"""
setup.py - Package setup (backwards compatibility)
"""

from setuptools import setup, find_packages
from pathlib import Path

version = "1.0.0"
try:
    with open("app/version.py", "r") as f:
        exec(f.read())
        version = __version__
except Exception:
    pass

readme_file = Path("README.md")
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

requirements = []
req_file = Path("requirements.txt")
if req_file.exists():
    with open(req_file, "r") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="networkmanager",
    version=version,
    author="Barremans",
    description="Een Python applicatie",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests*"]),
    install_requires=requirements,
    python_requires=">=3.11",
    entry_points={
        "console_scripts": [
            "networkmanager=app.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "i18n": ["locales/*.json"],
    },
)
