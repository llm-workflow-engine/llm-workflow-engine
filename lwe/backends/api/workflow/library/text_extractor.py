#!/usr/bin/python

import os
import re
import requests
import tempfile
from urllib.parse import urlparse

import kreuzberg
import pymupdf4llm
import fitz
fitz.TOOLS.mupdf_display_errors(False)

from ansible.module_utils.basic import AnsibleModule

from lwe.core.config import Config
from lwe.core.logger import Logger

config = Config()
config.set("debug.log.enabled", True)
log = Logger("text_extractor", config)

KREUZBERG_SUPPORTED_FILE_EXTENSIONS = [
    # Microsoft Office formats
    ".docx",
    ".pptx",
    ".xlsx",
    # OpenDocument formats
    ".odt",
    ".ods",
    ".odp",
    ".odg",
    ".odc",
    ".odf",
    ".odi",
    ".odm",
    # Rich Text Format
    ".rtf",
    # Markdown
    ".md",
    # Text files
    ".txt",
    ".csv",
    # HTML and XML formats
    ".html",
    ".htm",
    ".xhtml",
    ".xml",
    # Email formats
    ".eml",
    ".msg",
]

PYMUPDF_SUPPORTED_EXTENSIONS = [
    ".pdf",
    ".xps",
    ".oxps",
    ".epub",
    ".cbz",
    ".fb2"
]


DOCUMENTATION = r"""
---
module: text_extractor
short_description: Extract text content from a file or URL
description:
    - This module extracts the main text content from a given file or URL
    - For URLs, it extracts the main text content from the page, excluding header and footer.
    - For files, see the SUPPORTED_FILE_EXTENSIONS variables in the module code.
options:
    path:
      description:
          - The path to the file or the URL of the HTML content.
      type: path
      required: true
    max_length:
      description:
          - Limit the return of the extracted content to this length.
      type: int
      required: false
    default_extension:
      description:
          - Default file extension to use if the file has no extension.
      type: str
      default: ".pdf"
author:
    - Chad Phillips (@thehunmonkgroup)
"""

EXAMPLES = r"""
  - name: Extract content from a local PDF file
    text_extractor:
      path: "/path/to/your/file.pdf"

  - name: Extract content from a URL
    text_extractor:
      path: "https://example.com/sample.html"
      max_length: 3000

  - name: Extract content from a file with no extension
    text_extractor:
      path: "/path/to/your/file"
      default_extension: ".txt"
"""

RETURN = r"""
  content:
      description: The extracted main text content from the file or URL.
      type: str
      returned: success
  length:
      description: The length of the extracted main text content.
      type: int
      returned: success
"""


def extract_text_pymupdf(path):
    return pymupdf4llm.to_markdown(path)


def extract_text_kreuzberg(path):
    return kreuzberg.extract_file_sync(path)


def get_file_extension(path, default_extension):
    file_extension = default_extension
    for ext in set(KREUZBERG_SUPPORTED_FILE_EXTENSIONS + PYMUPDF_SUPPORTED_EXTENSIONS):
        if path.lower().endswith(ext):
            file_extension = ext
            break
    return file_extension


def main():
    result = dict(changed=False, response=dict())
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="path", required=True),
            max_length=dict(type="int", required=False),
            default_extension=dict(type="str", default=".pdf"),
        ),
        supports_check_mode=True,
    )
    path = module.params["path"]
    max_length = module.params["max_length"]
    default_extension = module.params["default_extension"].lower()
    if not default_extension.startswith("."):
        default_extension = f".{default_extension}"

    if module.check_mode:
        module.exit_json(**result)

    parsed_url = urlparse(path)
    is_url = parsed_url.scheme in ["http", "https"]
    cleanup_tmpfile_path = None
    if is_url:
        log.debug(f"Downloading content from URL: {path}")
        try:
            response = requests.get(path)
            response.raise_for_status()
            content = response.text
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".html") as f:
                f.write(content)
                path = cleanup_tmpfile_path = f.name
        except Exception as e:
            message = f"Error downloading content from URL {path}: {str(e)}"
            log.error(message)
            module.fail_json(msg=message)
    if not os.access(path, os.R_OK):
        message = f"File not found or not readable: {path}"
        log.error(message)
        module.fail_json(msg=message)

    file_extension = get_file_extension(path, default_extension)

    if file_extension in PYMUPDF_SUPPORTED_EXTENSIONS:
        log.debug(f"Extracting content from {path} with pymupdf4llm")
        try:
            content = extract_text_pymupdf(path)
        except Exception as e:
            message = f"Error extracting {path} content with pymupdf4llm: {str(e)}"
            log.error(message)
            module.fail_json(msg=message)
    elif file_extension in KREUZBERG_SUPPORTED_FILE_EXTENSIONS:
        log.debug(f"Extracting content from {path} with kreuzberg")
        try:
            extraction = extract_text_kreuzberg(path)
            content = extraction.content
        except Exception as e:
            message = f"Error extracting {file_extension} content with kreuzberg: {str(e)}"
            log.error(message)
            module.fail_json(msg=message)
    else:
        log.warning(f"Unsupported file extension: {file_extension}, trying to read as UTF-8")
        # Last ditch, try to read the file as UTF-8.
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            # Get rid of any non-ascii characters.
            content = re.sub(r"[^\x00-\x7F]+", "", f.read())

    if max_length:
        content = content[:max_length]
    if cleanup_tmpfile_path:
        os.remove(cleanup_tmpfile_path)
    result["content"] = content
    result["length"] = len(content)
    log.info("Content extracted successfully")
    module.exit_json(**result)


if __name__ == "__main__":
    main()
