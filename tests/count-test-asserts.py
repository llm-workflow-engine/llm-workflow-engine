#!/usr/bin/env python

import os

DEFAULT_TEST_DIRECTORY = os.path.dirname(os.path.realpath(__file__))


def count_asserts_in_file(file_path, debug):
    with open(file_path, "r") as file:
        count = file.read().count("assert")
    if debug:
        print(f"{file_path}: {count} asserts")
    return count


def count_asserts_in_directory(directory_path, debug):
    total_asserts = 0
    for root, _dirs, files in os.walk(directory_path):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                total_asserts += count_asserts_in_file(os.path.join(root, file), debug)
    return total_asserts


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Count the number of 'assert' statements in test files."
    )
    parser.add_argument(
        "directory",
        metavar="DIR",
        type=str,
        nargs="?",
        default=DEFAULT_TEST_DIRECTORY,
        help="the directory to analyze (default: %(default)s)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print the number of asserts for each file"
    )
    args = parser.parse_args()
    directory_path = args.directory
    debug = args.debug
    total_asserts = count_asserts_in_directory(directory_path, debug)
    print(f"Total asserts in {directory_path}: {total_asserts}")
