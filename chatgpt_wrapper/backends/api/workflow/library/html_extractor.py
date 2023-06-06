#!/usr/bin/python

import os
import requests
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ansible.module_utils.basic import AnsibleModule

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger

config = Config()
config.set('debug.log.enabled', True)
log = Logger(__name__, config)

DOCUMENTATION = r'''
---
module: html_extractor
short_description: Extract main text content from an HTML file or URL
description:
    - This module extracts the main text content from a given HTML file or URL, excluding header and footer.
options:
    path:
      description:
          - The path to the HTML file or the URL to the HTML content.
      type: path
      required: true
author:
    - Chad Phillips (@thehunmonkgroup)
'''

EXAMPLES = r'''
  - name: Extract content from a local HTML file
    html_extractor:
      path: "/path/to/your/html_file.html"

  - name: Extract content from a URL
    html_extractor:
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

def extract_main_content(content):
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
    if parsed_url.scheme in ['http', 'https']:
        try:
            response = requests.get(path)
            response.raise_for_status()
            content = response.text
        except Exception as e:
            log.error("Error downloading content from URL: %s", str(e))
            module.fail_json(msg="Error downloading content from URL: {}".format(str(e)))
    else:
        if not os.path.isfile(path):
            log.error("File not found: %s", path)
            module.fail_json(msg="File not found: {}".format(path))
        with open(path, 'r') as f:
            content = f.read()
    try:
        extracted_content = extract_main_content(content)
    except Exception as e:
        log.error("Error extracting content: %s", str(e))
        module.fail_json(msg="Error extracting content: {}".format(str(e)))
    result['content'] = extracted_content
    result['length'] = len(extracted_content)
    log.info("Content extracted successfully")
    module.exit_json(**result)

if __name__ == '__main__':
    main()
