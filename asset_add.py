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
from datetime import datetime

sys.path.append(os.path.abspath("scripts/csv_2_yaml/"))
sys.path.append(os.path.abspath("scripts/shared/"))

import yaml_io
import dict_utils
import csv2yaml

# TODO move this into the config
YAML_DIR = "./"

def chk_subproc(result: subprocess.CompletedProcess):
    if result.returncode != 0:
        print(f"{' '.join(result.args)} failed")
        exit(1)

def ingest_file(path: str):
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
# or assume a certain order??
def ingest_csv(path: str):
    # convert the CSV file into Asset objects
    assets = csv2yaml.csv_read(path, False)

    # generate the yaml files in the current directory
    names = csv2yaml.gen_yaml(assets, YAML_DIR)
    return [f"{name}.yaml" for name in names]

def ingest_interactive(domain: str):
    # list of generated files
    filenames = []
    another = 'y'

    while another  == 'y':
        print("Interactive asset entry: for each option you may press ENTER to skip")
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

        # hostname is the one parameter that MUST be entered
        hostname = ""
        while not hostname:
            hostname = input("Enter a hostname: ")

        # create an asset object
        asset = yaml_io.Asset(fqdn=f"{hostname}.{domain}")

        # yaml tags to skip in interative mode (ex. swap reason should be blank to start with)
        skip = [
            "hardware.swap_reason",
        ]

        # interactive prompts
        condo_asked = False
        flat = dict_utils.flatten_dict(asset.asset)
        for key in flat.keys():
            value = ""

            # some special cases to make entry easier
            if key == "acquisition.date":
                value = input(f"Enter {key} (or enter 'today'): ")
                if value == "today":
                    today = datetime.now()
                    value = today.strftime("%Y-%m-%d")
            elif key == "acquisition.fabrication":
                opt = input(f"Does this asset belong to a fabrication? (y/n): ")
                value = True if opt == 'y' else False
            elif key in skip:
                continue
            else:
                if "condo" in key and not condo_asked:
                    opt = input("Is this asset a condo sled? (y/n): ")
                    condo_asked = True
                    if opt != 'y':
                        skip.append("hardware.condo_chassis.identifier")
                        skip.append("hardware.condo_chassis.model")
                        continue

                value = input(f"Enter {key} (or press ENTER to skip): ")

            flat[key] = value

        # write the data to a file
        asset.asset = dict_utils.unflatten_dict(flat)

        filepath = f"{YAML_DIR}{asset.fqdn}.yaml"
        yaml_io.write_yaml(asset, filepath)
        filenames.append(filepath)

        # prompt the user for another asset
        another = input("Enter another asset?: (y/n)")
        print()

        return filenames

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

# stages and commits many new asset files
# assets are listed individually in the commit body
def git_add_commit_many(filenames: list[str]):
    # git add each file
    cmd = ["git", "add"]
    for filename in filenames:
        cmd.append(filename)

    result = subprocess.run(cmd)
    chk_subproc(result)

    # commit with a long message
    newline = '\n' # because f-strings don't support the backslash char :(
    result = subprocess.run(["git", "commit", "-m", f"added {len(filenames)} new assets", "-m", f"added {newline}{newline.join(filenames)}"])
    chk_subproc(result)

def main():
    args = setup_args()

    # do a pull first
    result = subprocess.run(["git", "pull"])
    chk_subproc(result)

    # add the new file(s)
    if args.file:
        filename = ingest_file(args.file)

        # git add/commit
        result = subprocess.run(["git", "add", filename])
        chk_subproc(result)
        result = subprocess.run(["git", "commit", "-m", f"Added an asset: {filename}"])
        chk_subproc(result)

    elif args.csv:
        filenames = ingest_csv(args.csv)
        git_add_commit_many(filenames)

    elif args.interactive:
        filenames = ingest_interactive(args.domain)
        git_add_commit_many(filenames)

    # git push
    result = subprocess.run(["git", "push"])
    chk_subproc(result)

if __name__ == "__main__":
    main()
