#!/usr/bin/python

import os
import re
import requests
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextBoxHorizontal

from ansible.module_utils.basic import AnsibleModule

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger

config = Config()
config.set('debug.log.enabled', True)
log = Logger(__name__, config)

DOCUMENTATION = r'''
---
module: text_extractor
short_description: Extract text content from a file or URL
description:
    - This module extracts the main text content from a given file or URL
    - For URLs, it extracts the main text content from the page, excluding header and footer.
    - For files, PDFs and text-based files are supported.
options:
    path:
      description:
          - The path to the file or the URL of the HTML content.
      type: path
      required: true
author:
    - Chad Phillips (@thehunmonkgroup)
'''

EXAMPLES = r'''
  - name: Extract content from a local HTML file
    text_extractor:
      path: "/path/to/your/html_file.html"

  - name: Extract content from a URL
    text_extractor:
      path: "https://example.com/sample.html"
'''

RETURN = r'''
  content:
      description: The extracted main text content from the HTML.
      type: str
      returned: success
  length:
      description: The length of the extracted main text content.
      type: int
      returned: success
'''

def extract_text_from_pdf(pdf_file):
    laparams = LAParams(line_margin=0.5, all_texts=True)
    pages = []
    for page_layout in extract_pages(pdf_file, laparams=laparams):
        text = []
        for element in page_layout:
            if isinstance(element, LTTextBoxHorizontal):
                text.append(element.get_text())
        pages.append(''.join(text))
    return "\n\n".join(pages)

def extract_text_from_html(content):
    log.debug("Parsing HTML content")
    soup = BeautifulSoup(content, 'html.parser')
    log.debug("Removing header and footer")
    if soup.header:
        soup.header.decompose()
    if soup.footer:
        soup.footer.decompose()
    log.debug("Extracting main text content")
    text_content = ''.join(soup.stripped_strings)
    return text_content

def main():
    result = dict(
        changed=False,
        response=dict()
    )
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type='path', required=True),
        ),
        supports_check_mode=True,
    )
    path = module.params['path']

    if module.check_mode:
        module.exit_json(**result)

    parsed_url = urlparse(path)
    is_url = parsed_url.scheme in ['http', 'https']
    if is_url:
        try:
            response = requests.get(path)
            response.raise_for_status()
            content = response.text
        except Exception as e:
            message = f"Error downloading content from URL {path}: {str(e)}"
            log.error(message)
            module.fail_json(msg=message)
    else:
        if not os.access(path, os.R_OK):
            message = f"File not found or not readable: {path}"
            log.error(message)
            module.fail_json(msg=message)
        if path.endswith(".pdf"):
            try:
                content = extract_text_from_pdf(path)
            except Exception as e:
                message = f"Error extracting PDF content: {str(e)}"
                log.error(message)
                module.fail_json(msg=message)
        else:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                # Get rid of any non-ascii characters.
                content = re.sub(r'[^\x00-\x7F]+', '', f.read())
    if is_url or path.endswith(".html"):
        try:
            extracted_content = extract_text_from_html(content)
        except Exception as e:
            message = f"Error extracting HTML content: {str(e)}"
            log.error(message)
            module.fail_json(msg=message)
    else:
        extracted_content = content
    result['content'] = extracted_content
    result['length'] = len(extracted_content)
    log.info("Content extracted successfully")
    module.exit_json(**result)

if __name__ == '__main__':
    main()
