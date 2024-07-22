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

#sys.path.append(os.path.abspath("../chtc_fellowship_inventory_tracking/scripts/csv_2_yaml/"))
#import csv2yaml

def chk_subproc(result: subprocess.CompletedProcess):
    if result.returncode != 0:
        print(f"{result.args.join(' ')} failed")
        exit(1)

def ingest_file(newname: str, path: str):
    # make sure that cp doesn't fail if path and ./newname are the same file
    if os.path.abspath(path) == os.path.abspath(newname):
        return

    # copy the file into the YAML directory
    # from the config fill
    result = subprocess.run(["cp", path, f"./{newname}"])
    chk_subproc(result)

# TODO make a column map in the config
def ingest_csv(path: str):
    # convert the CSV file into Asset objects
    assets = csv2yaml.csv_read(path)

    # generate the yaml files in the current directory
    # TODO change this dir once the config is set up
    csv2yaml.gen_yaml(assets, ".")
    pass

def ingest_interactive():
    print("interactive")

def add(filename: str, args: list):
    # do a pull first
    result = subprocess.run(["git", "pull"])
    chk_subproc(result)

    # add the new file(s)
    if args.file:
        ingest_file(filename, "./test.chtc.wisc.edu.yaml")
    elif args.csv:
        ingest_csv()
    elif args.interactive:
        ingest_interactive()

    # git add/commit/push sequence
    result = subprocess.run(["git", "add", filename])
    chk_subproc(result)

    result = subprocess.run(["git", "commit", "-m", f"\"Added asset {filename}\""])
    chk_subproc(result)

    result = subprocess.run(["git", "push"])
    chk_subproc(result)

def main():
    parser = argparse.ArgumentParser()

    required = parser.add_argument_group(title="required")
    required.add_argument("-n", "--name", help="the asset's name", action="store", required=True)

    # the ingestion method are mutually exclusive
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="ingest an asset via a YAML file", action="store_true")
    group.add_argument("-c", "--csv", help="ingest one or many assets via a CSV file", action="store_true")
    group.add_argument("-i", "--interactive", help="add an asset interactivly via CLI", action="store_true")

    # an optional argument if the domain is different than 'chtc.wisc.edu'
    parser.add_argument("-d", "--domain", help="the domain of the new asset - set to 'chtc.wisc.edu' if not specified", action="store", default="chtc.wisc.edu")

    args = parser.parse_args()

    add(f"{args.name}.{args.domain}.yaml", args)

if __name__ == "__main__":
    main()
