#!/bin/python3

# removes (moves to swap) an asset from the system
import os
import sys
import argparse
import subprocess
import shutil
import yaml
from datetime import datetime

sys.path.append(os.path.abspath("scripts/shared/"))
import yaml_io
import dict_utils

# TODO move this into the config
YAML_DIR = "./"
SWAP_DIR = "swapped/"

def chk_subproc(result: subprocess.CompletedProcess):
    if result.returncode != 0:
        print(f"{' '.join(result.args)} failed")
        exit(1)

def setup_args() -> argparse.Namespace:
    # set up argparse
    parser = argparse.ArgumentParser()

    required = parser.add_argument_group(title="required arguments")
    required.add_argument("name", help="the hostname of the asset to swap ex) 'ap2002'", action="store")
    required.add_argument("-r", "--reason", help="why the asset is being swapped", action="store", required=True)

    # optional domain arg
    parser.add_argument("-d", "--domain", help="the domain of the asset - defaults to 'chtc.wisc.edu' if not specified", action="store", default="chtc.wisc.edu")

    return parser.parse_args()


def main():
    args = setup_args()
    filename = f"{YAML_DIR}{args.name}.{args.domain}.yaml"

    result = subprocess.run(["git", "pull"])
    chk_subproc(result)

    # set the swap reason
    asset = yaml_io.Asset(filename)
    asset.put("hardware.swap_reason", args.reason)
    yaml_io.write_yaml(asset, f"{YAML_DIR}{filename}")

    # add the date to the new name and move the file
    date = datetime.now()
    newname = f"{os.path.basename(filename.removesuffix('.yaml'))}-{date.strftime('%Y-%m-%d')}.yaml"
    os.rename(filename, newname)

    shutil.move(newname, SWAP_DIR)

    # TODO remove - for testing don't commit anything :)
    exit(0)

    # git add + commit + push
    result = subprocess.run(["git", "add", f"{SWAP_DIR}{newname}"])
    chk_subproc(result)
    result = subprocess.run(["git", "commit", "-m", f"decomissioned {args.name} on {date.strftime('%Y-%m-%d')}"])
    chk_subproc(result)
    result = subprocess.run(["git", "push"])
    chk_subproc(result)

if __name__ == "__main__":
    main()
