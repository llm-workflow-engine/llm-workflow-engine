# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import re
from os import path
from datetime import datetime

current_year = datetime.now().year
authors = [
    "Chad Phillips",
    "Mahmoud Mabrouk",
]

ROOT_DIR = path.dirname(path.dirname(path.abspath(path.realpath(__file__))))

with open(path.join(ROOT_DIR, 'lwe', 'version.py')) as f:
    version = re.match(r'^__version__ = "([\w\.]+)"$', f.read().strip())[1]

project = 'LLM Workflow Engine'
copyright = '%s, %s' % (current_year, ", ".join(authors))
author = ", ".join(authors)
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_static_path = ['_static']
html_theme = 'alabaster'
html_theme_options = {
    # 'logo': 'images/cog-brain-trimmed.png',
    'logo': 'images/lwe-logo.png',
    'logo_name': False,
    'fixed_sidebar': True,
    'show_powered_by': False,
    'show_relbars': True,
    'sidebar_collapse': True,
    'github_button': True,
    'github_repo': 'llm-workflow-engine',
    'github_user': 'llm-workflow-engine',

}
html_sidebars = {
    '**': [
        'about.html',
        'searchbox.html',
        'navigation.html',
        'relations.html',
        'donate.html',
    ]
}
html_css_files = [
    'css/custom.css',
]
