#!/usr/bin/python

import sqlite3
from ansible.module_utils.basic import AnsibleModule

from lwe.core.config import Config
from lwe.core.logger import Logger

config = Config()
config.set("debug.log.enabled", True)
log = Logger("lwe_sqlite_query", config)

DOCUMENTATION = r"""
---
module: lwe_sqlite_query
short_description: Run a query against a SQLite database
description:
    - This module runs a query against a specified SQLite database and stores any returned data in a structured format.
options:
    db:
      description:
          - The path to the SQLite database file.
      type: str
      required: true
    query:
      description:
          - The SQL query to execute.
      type: str
      required: true
    query_params:
      description:
          - Optional list of query params to pass to a parameterized query.
      type: list
      required: false
author:
    - Chad Phillips (@thehunmonkgroup)
"""

EXAMPLES = r"""
  - name: Run a SELECT query against a SQLite database
    lwe_sqlite_query:
      db: "/path/to/your/database.db"
      query: "SELECT * FROM your_table WHERE id = ?"
      query_params:
        - 1
"""

RETURN = r"""
  data:
      description: The data returned from the query.
      type: list
      returned: success
  row_count:
      description: The number of rows returned from the query.
      type: int
      returned: success
"""


def run_query(db, query, params=()):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    if not query.lower().strip().startswith(("select")):
        conn.commit()
    data = [dict(row) for row in cursor.fetchall()]
    row_count = len(data)
    conn.close()
    return data, row_count


def main():
    result = dict(changed=False, response=dict())

    module = AnsibleModule(
        argument_spec=dict(
            db=dict(type="str", required=True),
            query=dict(type="str", required=True),
            query_params=dict(type="list", required=False, default=[]),
        ),
        supports_check_mode=True,
    )
    db = module.params["db"]
    query = module.params["query"]
    query_params = module.params["query_params"]

    if module.check_mode:
        module.exit_json(**result)

    try:
        log.debug(f"Running query on database: {db}: query: {query}, params: {query_params}")
        data, row_count = run_query(db, query, tuple(query_params))
        result["changed"] = True
        result["data"] = data
        result["row_count"] = row_count
        module.exit_json(**result)
    except Exception as e:
        result["failed"] = True
        message = f"Failed to run query: {query}, error: {e}"
        log.error(message)
        module.fail_json(msg=message, **result)


if __name__ == "__main__":
    main()
