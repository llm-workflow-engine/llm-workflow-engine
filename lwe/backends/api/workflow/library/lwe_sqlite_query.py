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
short_description: Run a query or multiple queries in a transaction against a SQLite database
description:
    - This module runs a query or multiple queries in a transaction against a specified SQLite database and stores any returned data in a structured format.
options:
    db:
      description:
          - The path to the SQLite database file.
      type: str
      required: true
    query:
      description:
          - The SQL query to execute. Can be a string for a single query or a list of strings for multiple queries in a transaction.
      type: raw
      required: true
    query_params:
      description:
          - Optional query params to pass to a parameterized query. Should be a list for a single query or a list of lists for multiple queries.
      type: raw
      required: false
author:
    - Chad Phillips (@thehunmonkgroup)
"""

EXAMPLES = r"""
  - name: Run a single SELECT query against a SQLite database
    lwe_sqlite_query:
      db: "/path/to/your/database.db"
      query: "SELECT * FROM your_table WHERE id = ?"
      query_params:
        - 1

  - name: Run multiple queries in a transaction
    lwe_sqlite_query:
      db: "/path/to/your/database.db"
      query:
        - "INSERT INTO table1 (column1, column2) VALUES (?, ?)"
        - "UPDATE table2 SET column1 = ? WHERE id = ?"
      query_params:
        - ["value1", "value2"]
        - ["new_value", 1]
"""

RETURN = r"""
  data:
      description: The data returned from the query or queries.
      type: list
      returned: success
  row_count:
      description: The total number of rows affected or returned from all queries.
      type: int
      returned: success
"""


def run_single_query(cursor, query, params=()):
    cursor.execute(query, params)
    if not query.lower().strip().startswith(("select")):
        return [], cursor.rowcount
    data = [dict(row) for row in cursor.fetchall()]
    return data, len(data)


def run_query(db, query, params=()):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    total_data = []
    total_row_count = 0
    try:
        if isinstance(query, str):
            data, row_count = run_single_query(cursor, query, params)
            total_data.extend(data)
            total_row_count += row_count
            conn.commit()
        else:
            conn.execute('BEGIN TRANSACTION')
            for q, p in zip(query, params):
                data, row_count = run_single_query(cursor, q, p)
                total_data.extend(data)
                total_row_count += row_count
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    return total_data, total_row_count


def main():
    result = dict(changed=False, response=dict())

    module = AnsibleModule(
        argument_spec=dict(
            db=dict(type="str", required=True),
            query=dict(type="raw", required=True),
            query_params=dict(type="raw", required=False, default=[]),
        ),
        supports_check_mode=True,
    )
    db = module.params["db"]
    query = module.params["query"]
    query_params = module.params["query_params"]

    if module.check_mode:
        module.exit_json(**result)

    # Validate input
    if isinstance(query, list):
        if not isinstance(query_params, list):
            module.fail_json(msg="query_params must be a list when query is a list")
        if len(query) != len(query_params):
            module.fail_json(msg="query and query_params must have the same length")
        if not all(isinstance(p, list) for p in query_params):
            module.fail_json(msg="Each item in query_params must be a list when query is a list")
    else:
        if not isinstance(query_params, list):
            module.fail_json(msg="query_params must be a list")

    try:
        log.debug(f"Running query on database: {db}: query: {query}, params: {query_params}")
        data, row_count = run_query(db, query, query_params)
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
