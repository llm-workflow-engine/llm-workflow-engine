from setuptools import find_packages, setup
import re
from os import path

FILE_DIR = path.dirname(path.abspath(path.realpath(__file__)))

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    install_requirement = f.readlines()

with open(path.join(FILE_DIR, 'chatgpt_wrapper', 'version.py')) as f:
    version = re.match(r'^__version__ = "([\w\.]+)"$', f.read().strip())[1]

setup(
    name="chatGPT",
    version=version,
    author="Mahmoud Mabrouk",
    author_email="mahmoudmabrouk.mail@gmail.com",
    description="A simple Python class for interacting with OpenAI's chatGPT using Playwright",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mmabrouk/chatgpt-wrapper",
    packages=find_packages(),
    install_requires=install_requirement,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "chatgpt = chatgpt_wrapper.main:main",
        ],
        "chatgpt_wrapper_plugins": [],
    },
    scripts=["postinstall.sh"],
)
