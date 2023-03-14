#!/usr/bin/env bash

SCRIPT_NAME=`basename $0`

usage() {
  echo "
${SCRIPT_NAME} <commit>

Simple script to generate pretty changelog entries from git commits for use in
a markdown list.

  commit: The git tag or commit hash to generate the log from.
"
}

if [ $# -ne 1 ]; then
  usage
  exit 1
fi

git log --no-merges --date=format:"%a %b %d %Y" --pretty="* **%ad:** %s" ${1}..
