#!/usr/bin/env bash

# Convenience script to handle preparing for PyPi release, and printing out the
# commands to execute it.

execute() {
  local update_build_release_packages="pip install --upgrade wheel build twine"
  local clean="rm -rfv dist/ build/"
  local build="python -m build"
  local test_pypi_upload="python -m twine upload --repository testpypi dist/*"
  local pypi_upload="python -m twine upload --skip-existing dist/*"

  echo "Updating build and release packages with command:"
  echo "  ${update_build_release_packages}"
  ${update_build_release_packages}

  if [ $? -eq 0 ]; then
    echo "Cleaning build environment with command:"
    echo "  ${clean}"
    ${clean}
    if [ $? -eq 0 ]; then
      echo "Building release with command:"
      echo "  ${build}"
      ${build}
      if [ $? -eq 0 ]; then
        echo "Build successful"
        echo
        echo "Test release with command:"
        echo "  ${test_pypi_upload}"
        echo
        echo "Release with command:"
        echo "  ${pypi_upload}"
      fi
    fi
  fi
}

if [ -d vit ] && [ -r setup.py ]; then
  execute
else
  echo "ERROR: must run script from repository root"
fi
