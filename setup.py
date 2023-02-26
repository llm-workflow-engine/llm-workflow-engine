from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    install_requirement = f.readlines()

setup(
    name="chatGPT",
    version="0.3.17",
    author="Mahmoud Mabrouk / extended Christian Schnapka",
    author_email="mahmoudmabrouk.mail@gmail.com",
    description="A simple Python class for interacting with OpenAI's chatGPT using Playwright",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nolem/chatgpt-wrapper-with-inline-code",
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
            "chatgpt = chatgpt_wrapper.main:main"
        ]
    },
    scripts=["postinstall.sh"],
)
