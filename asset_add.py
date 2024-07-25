#!/bin/python3

# ingests assets into the system
#
# asset addition can be done 3 ways
#   1. Interactivly
#   2. via. a CSV file
#   3. via. a specified asset YAML file

import sys
import os
import argparse
import subprocess

sys.path.append(os.path.abspath("scripts/csv_2_yaml/"))
sys.path.append(os.path.abspath("scripts/shared/"))

import yaml_io
import csv2yaml

# TODO move this into the config
YAML_DIR = "./"

def chk_subproc(result: subprocess.CompletedProcess):
    if result.returncode != 0:
        print(f"{result.args.join(' ')} failed")
        exit(1)

def ingest_file(path: str):
    # TODO should there be a way to ingest multiple files??
    # ^ that seems like a job for the CSV function
    # make sure that cp doesn't fail if path and ./path are the same file
    newpath = f"{YAML_DIR}{os.path.basename(path)}"

    if os.path.abspath(path) == os.path.abspath(newpath):
        print(f"added an asset {path}")
        return

    # copy the file into the YAML directory
    # from the config fill
    result = subprocess.run(["cp", path, newpath])
    chk_subproc(result)

    return newpath

# TODO make a column map in the config
def ingest_csv(path: str):
    # convert the CSV file into Asset objects
    assets = csv2yaml.csv_read(path, False)

    # generate the yaml files in the current directory
    # TODO change this dir once the config is set up
    return csv2yaml.gen_yaml(assets, YAML_DIR)

def ingest_interactive():
    print("interactive")

def setup_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    # the ingestion method are mutually exclusive
    # TODO probably tweak the CLI here
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="ingest an asset via a YAML file", action="store")
    group.add_argument("-c", "--csv", help="ingest one or many assets via a CSV file", action="store")
    group.add_argument("-i", "--interactive", help="add an asset interactivly via CLI", action="store_true")

    # an optional argument if the domain is different than 'chtc.wisc.edu'
    parser.add_argument("-d", "--domain", help="the domain of the new asset - set to 'chtc.wisc.edu' if not specified", action="store", default="chtc.wisc.edu")

    return parser.parse_args()

def main():
    args = setup_args()

    # do a pull first
    result = subprocess.run(["git", "pull"])
    chk_subproc(result)

    filenames = []

    # add the new file(s)
    if args.file:
        filenames = ingest_file(args.file)
    elif args.csv:
        filenames = ingest_csv(args.csv)
    elif args.interactive:
        filenames = ingest_interactive()

    # TODO remove for testing we never want to push :)
    exit(0)

    # git add/commit/push sequence
    result = subprocess.run(["git", "add", f"{filenames.join(' ')}"])
    chk_subproc(result)
    result = subprocess.run(["git", "commit", "-m", f"\"Added asset(s) {filenames.join(' ')}\""])
    chk_subproc(result)
    result = subprocess.run(["git", "push"])
    chk_subproc(result)

if __name__ == "__main__":
    main()
