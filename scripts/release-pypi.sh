#!/usr/bin/env bash

# Convenience script to handle preparing for PyPi release, and printing out the
# commands to execute it.

clean() {
  echo "Cleaning build environment"
  rm -rfv dist/ build/
  find . -depth -name __pycache__ -type d -exec rm -rfv {} \;
}

execute() {
  local update_build_release_packages="pip install --upgrade build twine validate-pyproject"
  local validate="validate-pyproject pyproject.toml"
  local build="python -m build"
  local check_dist="twine check dist/*"
  local test_pypi_upload="python -m twine upload --repository testpypi dist/*"
  local pypi_upload="python -m twine upload --skip-existing dist/*"
  # Uncomment the following line if you want to sign releases
  # local pypi_upload="python -m twine upload --skip-existing --sign dist/*"

  echo "Updating build and release packages with command:"
  echo "  ${update_build_release_packages}"
  ${update_build_release_packages}

  if [ $? -eq 0 ]; then
    echo "Validating pyproject.toml with command:"
    echo "  ${validate}"
    ${validate}
    if [ $? -eq 0 ]; then
      echo "Building release with command:"
      echo "  ${build}"
      ${build}
      if [ $? -eq 0 ]; then
        echo "Checking built distribution with command:"
        echo "  ${check_dist}"
        ${check_dist}
        if [ $? -eq 0 ]; then
          echo "Build successful and verified"
          echo
          echo "Test release with command:"
          echo "  ${test_pypi_upload}"
          echo
          echo "Release with command:"
          echo "  ${pypi_upload}"
        fi
      fi
    fi
  fi
}

if [ -r pyproject.toml ]; then
  clean
  execute
else
  echo "ERROR: must run script from repository root"
fi
