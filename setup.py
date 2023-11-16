from setuptools import find_packages, setup
import re
from os import path

FILE_DIR = path.dirname(path.abspath(path.realpath(__file__)))

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt") as f:
    install_requirement = f.readlines()

with open(path.join(FILE_DIR, "lwe", "version.py")) as f:
    version = re.match(r'^__version__ = "([\w\.]+)"$', f.read().strip())[1]

setup(
    name="llm-workflow-engine",
    version=version,
    author="Mahmoud Mabrouk, Chad Phillips",
    author_email="mahmoudmabrouk.mail@gmail.com",
    description="CLI tool and workflow manager for common LLMs, with a focus on OpenAI's models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/llm-workflow-engine/llm-workflow-engine",
    packages=find_packages(),
    package_data={
        "lwe": [
            "backends/api/schema/alembic.ini",
            "backends/api/schema/alembic/*",
            "backends/api/schema/alembic/**/*",
            "examples/*",
            "examples/**/*",
            "functions/*",
            "functions/**/*",
            "presets/*",
            "presets/**/*",
            "templates/*",
            "templates/**/*",
            "workflows/*",
            "workflows/**/*",
        ],
    },
    install_requires=install_requirement,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "lwe = lwe.main:main",
        ],
        "lwe_plugins": [],
    },
    scripts=[],
)
