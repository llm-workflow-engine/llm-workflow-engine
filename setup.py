from setuptools import find_packages, setup

from chatgpt_wrapper.main import VERSION

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="chatGPT",
    version=VERSION,
    author="Mahmoud Mabrouk",
    author_email="mahmoudmabrouk.mail@gmail.com",
    description="A simple Python class for interacting with OpenAI's chatGPT using Playwright",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mmabrouk/chatgpt-wrapper",
    packages=find_packages(),
    install_requires=[
        "playwright",
        "rich",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "chatgpt = chatgpt_wrapper.main:main"
        ]
    },
    scripts=["postinstall.sh"],
)
