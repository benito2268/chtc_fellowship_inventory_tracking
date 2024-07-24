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
        print(f"{result.args.join(' ')} failed")
        exit(1)

def main():
    # set up argparse
    parser = argparse.ArgumentParser()

    required = parser.add_argument_group(title="required arguments")
    required.add_argument("-n", "--name", help="the name of the asset to swap ex) 'ap2002'", action="store", required=True)
    required.add_argument("-r", "--reason", help="why the asset is being swapped", action="store", required=True)

    # optional domain arg
    parser.add_argument("-d", "--domain", help="the domain of the asset - defaults to 'chtc.wisc.edu' if not specified", action="store", default="chtc.wisc.edu")

    args = parser.parse_args()

    # get the filename of the asset
    filename = f"{YAML_DIR}{args.name}.{args.domain}.yaml"

    # do a git pull before we do anything
    result = subprocess.run(["git", "pull"])
    chk_subproc(result)

    # add the swap reason to the YAML and swap date to the filename
    with open(filename, 'r') as yamlfile:
        yamldata = yaml.safe_load(yamlfile)

    # TODO this may break
    asset = yaml_io.Asset(filename)
    asset.put("hardware.swap_reason", args.reason)
    yaml_io.write_yaml(asset, f"{YAML_DIR}{filename}")

    date = datetime.now()
    newname = f"{os.path.basename(filename.removesuffix('.yaml'))}-{date.strftime('%Y-%m-%d')}.yaml"
    os.rename(filename, newname)

    # move the file
    shutil.move(newname, SWAP_DIR)

    # TODO remove - for testing don't commit anything :)
    exit(0)

    # git add + commit + push
    result = subprocess.run(["git", "add", f"{SWAP_DIR}/{newname}"])
    chk_subproc(result)

    # TODO should the reason be in the commit message?
    result = subprocess.run(["git", "commit", "-m", f"swappped {args.name} on {date.strftime('%Y-%m-%d')}"])
    chk_subproc(result)

    result = subprocess.run(["git", "push"])
    chk_subproc(result)

if __name__ == "__main__":
    main()
