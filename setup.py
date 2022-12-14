from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
    
setup(
    name="chatGPT",
    version="0.3.6",
    author="Mahmoud Mabrouk",
    author_email="mahmoudmabrouk.mail@gmail.com",
    description="A simple Python class for interacting with OpenAI's chatGPT using Playwright",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/openai/playwright-chatbot",
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
            "chatgpt = chatgpt_wrapper.chatgpt:main"
        ]
    },
    scripts=["postinstall.sh"],
)
