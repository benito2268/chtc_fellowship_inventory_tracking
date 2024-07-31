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
from datetime import datetime

sys.path.append(os.path.abspath("scripts/csv_2_yaml/"))
sys.path.append(os.path.abspath("scripts/shared/"))

import yaml_io
import dict_utils
import csv2yaml

# TODO move this into the config
YAML_DIR = "./"
SWAP_DIR = "./swapped"

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

# returns a list of new files
def asset_add(args: argparse.Namespace) -> list[str]:
    filenames = []

    if args.interactive:
        filenames = ingest_interactive(args.domain)
    elif args.csv:
        filenames = ingest_csv(args.csv)
    elif args.file:
        filenames = ingest_file(args.file)

    return filenames

# ================ ASSET REMOVE FUNCTIONS ====================

# TODO make a batch / interactive? mode here
# returns a list of file names
def asset_rm(args: argparse.Namespace) -> list[str]:
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

    return list(filename)

# ================ ASSET UPDATE FUNCTIONS ====================


def asset_update(args: argparse.Namespace):
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

# ================ ASSET MOVE FUNCTIONS ====================


def asset_move(args: argparse.Namespace):
    pass

# ================ ASSET RENAME FUNCTIONS ====================


def asset_rename(args: argparse.Namespace):
        pass

# ================ MAIN AND ARGPARSE FUNCTIONS ====================

def setup_args() -> argparse.Namespace:
    pass

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="subcommands", dest="command")

    # add a subparser for each subcommand
    add_parser = subparsers.add_parser("add", help="add a new asset")
    rm_parser = subparsers.add_parser("rm", help="decomission an asset")
    move_parser = subparsers.add_parser("move", help="change an asset's location")
    rename_parser = subparsers.add_parser("rename", help="rename an asset")
    update_parser = subparsers.add_parser("update", help="change an asset's data")

    subp_list = [add_parser, rm_parser, move_parser, rename_parser, update_parser]

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

    args = parser.parse_args()

    # map argument names to their corresponding functions
    func_map = {
        "add" : asset_add,
        "rm"  : asset_rm,
        "update" : asset_update,
        "move" : asset_move,
        "rename" : asset_rename,
    }

    # call the appropriate function
    func_map[args.command](args)

if __name__ == "__main__":
    main()
