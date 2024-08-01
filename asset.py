#!/bin/python3

# Main asset operations script
# contains operations for add, remove, update, move, and rename
#
# TODO should this be rewritten with typer???
# run ./asset.py --help to see command line usage

import sys
import os
import argparse
import shutil
import git
from collections import namedtuple
from datetime import datetime

sys.path.append(os.path.abspath("scripts/csv_2_yaml/"))
sys.path.append(os.path.abspath("scripts/shared/"))

import yaml_io
import dict_utils
import csv2yaml

# TODO move this into the config
YAML_DIR = "./"
SWAP_DIR = "./swapped"

# declare a namedtuple to hold git data (specifically changed files and a commit message)
GitData = namedtuple("GitData", [ "files", "commit_msg"])

# ================ ASSET ADD FUNCTIONS ====================

def ingest_file(path: str) -> str:
    # make sure that cp doesn't fail if path and ./path are the same file
    newpath = f"{YAML_DIR}{os.path.basename(path)}"

    if os.path.abspath(path) == os.path.abspath(newpath):
        print(f"added an asset {path}")
        return

    # copy the file into the YAML directory
    # from the config fill
    shutil.copy(path, newpath)

    return newpath

# TODO make a column map in the config
# or assume a certain order??
def ingest_csv(path: str) -> list[str]:
    # convert the CSV file into Asset objects
    assets = csv2yaml.csv_read(path, False)

    # generate the yaml files in the current directory
    names = csv2yaml.gen_yaml(assets, YAML_DIR)

    return [f"{name}.yaml" for name in names]

def ingest_interactive(domain: str) -> list[str]:
    # list of generated files
    filenames = []
    another = 'y'

    while another  == 'y':
        print("Interactive asset entry: for each option you may press ENTER to skip")
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print()

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

def asset_add(args: argparse.Namespace) -> GitData:
    filenames = []

    if args.interactive:
        filenames = ingest_interactive(args.domain)
    elif args.csv:
        filenames = ingest_csv(args.csv)
    elif args.file:
        filenames = ingest_file(args.file)

    # TODO figure out long commit messages
    return GitData(filenames, f"added {len(filenames)} new assets")

# ================ ASSET REMOVE FUNCTIONS ====================

# TODO make a batch / interactive? mode here
def asset_rm(args: argparse.Namespace) -> GitData:
    filename = f"{YAML_DIR}{args.name}.{args.domain}.yaml"

    # set the swap reason
    asset = yaml_io.Asset(filename)
    asset.put("hardware.swap_reason", args.reason)
    yaml_io.write_yaml(asset, f"{YAML_DIR}{filename}")

    # add the date to the new name and move the file
    date = datetime.now()
    newname = f"{os.path.basename(filename.removesuffix('.yaml'))}-{date.strftime('%Y-%m-%d')}.yaml"
    os.rename(filename, newname)

    shutil.move(newname, SWAP_DIR)

    now = datetime.now()
    return GitData([filename], f"decomissioned {filename} on {now.strftime('%Y-%m-%d')}")

# ================ ASSET UPDATE FUNCTIONS ====================

def asset_update(args: argparse.Namespace) -> GitData:
    # read the yaml file
    filename = f"{YAML_DIR}{args.name}.{args.domain}.yaml"
    asset = yaml_io.Asset(filename)

    # modify the file
    try:
        asset.get(args.key)
    except KeyError:
        if args.add:
            print(f"adding new YAML tag {args.key} : {args.value}")
        else:
            print(f"YAML tag not found (pass '-a/--add' if you wish to add it to the file)")
            exit(1)

    # write out to the file
    asset.put(args.key, args.value)
    yaml_io.write_yaml(asset, filename)

    return GitData([filename], f"updated {args.key} to {args.value} in {filename}")

# ================ ASSET MOVE FUNCTIONS ====================

# TODO add non-interactive mode
def asset_move(args: argparse.Namespace) -> GitData:
    opts = []
    prompts = [
        "Enter a new elevation: ",
        "Enter a new rack: (press ENTER to keep prev.) ",
        "Enter a new room: (press ENTER to keep prev.) ",
        "Enter a new building: (press ENTER to keep prev.) ",
    ]

    keys = [
        "elevation",
        "rack",
        "room",
        "building",
    ]

    # interactive move
    for prompt in prompts:
        opts.append(input(prompt))


    filename = f"{args.name}.{args.domain}.yaml"
    asset = yaml_io.Asset(filename)

    # for the commit message
    new_locs = []

    for i in range(len(opts)):
        if opts[i] != "":
            asset.put(f"location.{keys[i]}", opts[i])
            new_locs.append(f"{keys[i]}: {opts[i]}")
        else:
            old_loc = asset.get(f"location.{keys[i]}")
            new_locs.append(f"{keys[i]}: {old_loc}")

    # write out to the YAML file
    yaml_io.write_yaml(asset, f"{YAML_DIR}{filename}")

    return GitData([filename], f"moved {args.name} to {', '.join(new_locs)}")

# ================ ASSET SWITCH FUNCTIONS ====================

def asset_switch(args: argparse.Namespace) -> GitData:
    keys = [
        "elevation",
        "rack",
        "room",
        "building",
    ]

    # switch locations
    first = f"{args.name}.{args.domain}.yaml"
    second = f"{args.switch_with}.{args.domain}.yaml"

    asset1 = yaml_io.Asset(first)
    asset2 = yaml_io.Asset(second)

    # swap the keys
    for key in keys:
        temp = asset1.get(f"location.{key}")
        asset1.put(f"location.{key}", asset2.get(f"location.{key}"))
        asset2.put(f"location.{key}", temp)

    # write out both to YAML
    yaml_io.write_yaml(asset1, f"{YAML_DIR}{first}")
    yaml_io.write_yaml(asset2, f"{YAML_DIR}{second}")

    return GitData([first, second], f"swapped the location of {args.name} and {args.swap_with}")

# ================ ASSET RENAME FUNCTIONS ====================

def asset_rename(args: argparse.Namespace) -> GitData:
    # rename the asset
    filename = f"{YAML_DIR}{args.name}.{args.domain}.yaml"
    newname = f"{YAML_DIR}{args.newname}.{args.domain}.yaml"

    os.rename(filename, newname)

    return GitData([newname, filename], f"renamed {args.name} to {args.newname}")

# ================ MAIN AND ARGPARSE FUNCTIONS ====================

def setup_args() -> argparse.Namespace:
    # argparse shenanigans
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="subcommands", dest="command")

    # add a subparser for each subcommand
    add_parser = subparsers.add_parser("add", help="add a new asset")
    rm_parser = subparsers.add_parser("rm", help="decomission an asset")
    move_parser = subparsers.add_parser("move", help="change an asset's location")
    switch_parser = subparsers.add_parser("switch", help="switch the location of two assets")
    rename_parser = subparsers.add_parser("rename", help="rename an asset")
    update_parser = subparsers.add_parser("update", help="change an asset's data")

    subp_list = [add_parser, rm_parser, move_parser, rename_parser, update_parser, switch_parser]

    # add common args to each subparser
    for subparser in subp_list:
        subparser.add_argument("name", help="the asset's hostname", type=str, action="store")
        subparser.add_argument("-d", "--domain", help="defaults to 'chtc.wisc.edu' if not specified", action="store", default="chtc.wisc.edu")

    # add unique args to each subparser
    # add asset args
    add_group = add_parser.add_mutually_exclusive_group(required=True)
    add_group.add_argument("-f", "--file", help="ingest an asset via a YAML file", action="store")
    add_group.add_argument("-c", "--csv", help="ingest one or many assets via a CSV file", action="store")
    add_group.add_argument("-i", "--interactive", help="add an asset interactivly via CLI", action="store_true")

    # rm asset args
    rm_parser.add_argument("-r", "--reason", help="the reason for decomissioning", type=str, action="store", required=True)

    # update asset args
    update_parser.add_argument("key", help="the fully qualified YAML key (tag) to modify. ex) 'hardware.model'", action="store")
    update_parser.add_argument("value", help="the new value to store", action="store")

    # asset switch args
    switch_parser.add_argument("switch_with", help="", type=str, action="store")

    # asset rename args
    rename_parser.add_argument("newname", help="the asset's new name", action="store")

    return parser.parse_args()

def main():
    args = setup_args()

    # map argument names to their corresponding functions
    func_map = {
        "add" : asset_add,
        "rm"  : asset_rm,
        "update" : asset_update,
        "move" : asset_move,
        "switch" : asset_switch,
        "rename" : asset_rename,
    }

    # setup git
    # tell GitPython that that .git/ is in the current working dir
    repo = git.Repo(os.path.abspath("./"))

    # check if the repo is clean
    if repo.is_dirty():
        print()
        print("git error: working tree not clean! There are untracked changes: ")
        print("----------------------------------------------------------------")
        for file in repo.index.diff(None):
            print(file.a_path)

        print()

        if repo.untracked_files:
            print("untracked files: ")
            print("-----------------")
            for file in repo.untracked_files:
                print(file)

        print()

    # if the repo is clean pull from origin main
    # TODO I think these can generate exceptions
    origin = repo.remote(name="origin")
    origin.pull()

    # call the appropriate function
    # each returns a commit message describing what it did 
    data = func_map[args.command](args)

    # create a commit and push
    repo.git.add(data.files)
    repo.git.commit("-m", data.commit_msg)

    origin.push()

if __name__ == "__main__":
    main()
