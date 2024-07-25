#!/bin/python3

# renames an asset
import os
import subprocess
import argparse

YAML_DIR = "./"

def chk_subproc(result: subprocess.CompletedProcess):
    if result.returncode != 0:
        print(f"{' '.join(result.args)} failed")
        exit(1)

def setup_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    # required args
    parser.add_argument("name", help="the name of the asset to rename", action="store")
    parser.add_argument("newname", help="the asset's new name", action="store")

    # optional args
    parser.add_argument("-d", "--domain", help="defaults to chtc.wisc.edu if not specified", action="store", default="chtc.wisc.edu")

    return parser.parse_args()

def main():
    args = setup_args()

    # git pull
    result = subprocess.run(["git", "pull"])
    chk_subproc(result)

    # rename the asset
    filename = f"{YAML_DIR}{args.name}.{args.domain}.yaml"
    newname = f"{YAML_DIR}{args.newname}.{args.domain}.yaml"

    os.rename(filename, newname)

    # git add, commit, push
    result = subprocess.run(["git", "add", newname])
    chk_subproc(result)
    result = subprocess.run(["git", "commit", "-m", f"renamed {args.name} to {args.newname}"])
    chk_subproc(result)
    result = subprocess.run(["git", "push"])


if __name__ == "__main__":
    main()
