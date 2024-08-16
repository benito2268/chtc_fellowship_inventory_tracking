#!/bin/python3

# Main asset operations script
# contains operations for add, remove, update, move, and rename
#
# run ./asset.py --help to see command line usage

import sys
import os
import argparse
import shutil
import git
import csv
from collections import namedtuple
from copy import deepcopy
from datetime import datetime

sys.path.append(os.path.abspath("scripts/csv_2_yaml/"))
sys.path.append(os.path.abspath("scripts/shared/"))

import yaml_io
import dict_utils
import csv2yaml
import config
import email_report

# Git repo object for the repo in which the script is operating
REPO = None

# these are read in from the config
YAML_DIR = ""
SWAP_DIR = ""

# declare a namedtuple to hold git data (specifically changed files and a commit message)
GitData = namedtuple("GitData", [ "files", "commit_msg", "commit_body"])

# tuple to handle swapped files for Git
# Git counts a move as an add + delete - we need to add both the new and old file names
MovedFiles = namedtuple("MovedFiles", ["added", "removed"])

# a named tuple representing a location
Location = namedtuple("Location", ["building", "room", "rack", "elevation"])

# ================ GIT HELPER FUNCTIONS ====================

# for adding assets - exits with an error if an asset already exists and is tracked
def chk_file_tracked(path: str) -> bool:
    if os.path.exists(path) and path not in REPO.untracked_files:
        print(f"ERROR: asset {path} already exists and is tracked by Git (skipping)")
        return True
    return False

# ================ CSV HELPER FUNCTIONS ====================

# reads yaml tags out of the first row of the CSV and generates a column map
def get_column_map(csv_path: str) -> dict:
    col_map = {}

    with open(csv_path, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')

        # read the first line
        header = next(reader)

        # create a flat template dict to check keys against
        cp = deepcopy(yaml_io.ASSET_TEMPLATE)
        flat = dict_utils.flatten_dict(cp)

        # parse it into a map
        for i in range(len(header)):
            # check that this a real tag
            tag = header[i]
            if tag != "hostname" and tag != "domain":
                try:
                    test = flat[tag.strip()]
                except KeyError:
                    print(f"Warning: batch update skipping non-existant key: {tag}")
                    continue

            col_map[header[i].strip()] = i

    return col_map

# returns a list of files it modified
def modify_from_csv(path: str, key_map: dict, create_files: bool=False) -> list[str]:
    rows = []
    filenames = []

    with open(path, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')

        # skip header row?
        next(reader)

        for row in reader:
            # print(row)
            filename = f"{YAML_DIR}{row[key_map['hostname']]}.{row[key_map['domain']]}.yaml"

            if create_files:
                # check if the new file is already tracked
                if chk_file_tracked(filename):
                    # skip the asset if it already exists
                    continue

                filenames.append(filename)

                # create a blank yaml file
                asset = yaml_io.Asset(fqdn=f"{row[key_map['hostname']]}.{row[key_map['domain']]}")
                yaml_io.write_yaml(asset, filename)

            # load the file
            # TODO does this work in the constructor?
            asset = yaml_io.Asset(file=filename)

            # modify the fields
            for key in key_map:
                if key != "hostname" and key != "domain":
                    cell = row[key_map[key]]

                    # if the cell is empty - keep the old value
                    # TODO is this the right thing to do??
                    if cell == "":
                        continue
                    asset.put(key, cell)

            # write back to the file
            yaml_io.write_yaml(asset, filename)

    return filenames

# ================ ASSET ADD FUNCTIONS ====================

def ingest_single(name: str, domain: str, file: str) -> str:
    # make sure that cp doesn't fail if path and ./path are the same file
    path = f"{YAML_DIR}{name}.{domain}.yaml"
    newpath = f"{YAML_DIR}{os.path.basename(file)}"

    # check if newpath is tracked
    if chk_asset_tracked(newpath):
        exit(1)

    # don't cp a file to a location where it already exists
    if os.path.abspath(path) == os.path.abspath(newpath):
        return path

    # copy the file into the YAML directory
    # from the config fill
    shutil.copy(path, newpath)

    return newpath

def ingest_csv(csv_path: str) -> list[str]:
    # key map for imports
    key_map = get_column_map(csv_path)

    # convert the CSV file into Asset objects - with the create_files option set
    filenames = modify_from_csv(csv_path, key_map, True)
    return filenames

def ingest_interactive(name: str, domain: str) -> list[str]:
    # list of generated files
    filenames = []

    first = True
    another = 'y'

    print("Interactive asset entry: for each option you may press ENTER to skip")
    print("====================================================================")
    print()

    curr_name = name
    curr_domain = domain

    while another  == 'y':
        if not first:
            curr_name = input("Enter a hostname: ")
            d = input("Enter a domain: (or press ENTER for 'chtc.wisc.edu) ")
            curr_domain = d if d != "" else "chtc.wisc.edu"

        first = False

        # create an asset object
        asset = yaml_io.Asset(fqdn=f"{curr_name}.{curr_domain}")

        # check to make sure the file is not already tracked
        if chk_file_tracked(f"{YAML_DIR}{curr_name}{curr_domain}.yaml"):
            continue

        # yaml tags to skip in interactive mode (ex. swap reason should be blank to start with)
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
        filenames = ingest_interactive(args.interactive, args.domain)
    elif args.batch:
        filenames = ingest_csv(args.batch)
    elif args.single:
        name, file = args.single
        filenames = ingest_single(name, args.domain, file)

    # tally an addition for the email
    email_report.count_add_or_rm(True, len(filenames))

    # format strings don't allow the '\n' char :(
    filenames.append(".weekly_stats.yaml")
    return GitData(
        filenames,
        f"added {len(filenames)} new assets",
        "added\n" + "\n".join([os.path.basename(file) for file in filenames])
    )

# ================ ASSET REMOVE FUNCTIONS ====================

def remove_batch(csv_path: str) -> MovedFiles:
    key_map = get_column_map(csv_path)

    # modify the files
    filenames = modify_from_csv(csv_path, key_map)
    newpaths = []

    # move files to the swap dir
    datestr = datetime.now().strftime("%Y-%m-%d")
    for file in filenames:
        basename = os.path.basename(file)
        newpath = f"{SWAP_DIR}{basename.removesuffix('.yaml')}-{datestr}.yaml"
        newpaths.append(newpath)

        shutil.move(file, newpath)

    return MovedFiles(newpaths, filenames)

def remove_single(name: str, domain: str, reason: str) -> MovedFiles:
    filename = f"{YAML_DIR}{name}.{domain}.yaml"

    # set the swap reason
    asset = yaml_io.Asset(filename)
    asset.put("hardware.swap_reason", reason)
    yaml_io.write_yaml(asset, filename)

    # add the date to the new name and move the file
    datestr = datetime.now().strftime('%Y-%m-%d')
    newname = f"{os.path.basename(filename.removesuffix('.yaml'))}-{datestr}.yaml"
    os.rename(filename, newname)

    shutil.move(newname, SWAP_DIR)

    # need to git add both the new and old file paths
    return MovedFiles([filename], [f"{SWAP_DIR}{newname}"])

def asset_rm(args: argparse.Namespace) -> GitData:
    moved_files = None

    if args.batch:
        # remove in batch
        moved_files = remove_batch(args.batch)
    else:
        name, reason = args.single
        moved_files = remove_single(name, args.domain, reason)

    # tally an addition for the email
    email_report.count_add_or_rm(False, len(moved_files.removed))

    datestr = datetime.now().strftime('%Y-%m-%d')
    moved_files.added.append(".weekly_stats.yaml")

    return GitData(
        [moved_files.added, moved_files.removed],
        f"decomissioned {len(moved_files.removed)} assests on {datestr}",
        "swapped\n" + "\n".join([os.path.basename(file) for file in moved_files.removed])
    )

# ================ ASSET UPDATE FUNCTIONS ====================

def update_batch(csv_path: str) -> list[str]:
    key_map = get_column_map(csv_path)
    # print(key_map)

    filenames = modify_from_csv(csv_path, key_map)

    return filenames

def update_single(name: str, domain: str, key: str, value: str) -> list[str]:
    filename = f"{YAML_DIR}{name}.{domain}.yaml"

    # read the asset
    asset = yaml_io.Asset(file=filename)

    # modify the file
    try:
        asset.get(key)
    except KeyError:
        print(f"invalid YAML tag: {key}")
        exit(1)

    # write out to the file
    asset.put(key, value)
    yaml_io.write_yaml(asset, filename)

    return [filename]

def update_interactive(name: str, domain: str) -> list[str]:
    filenames = []
    first = True

    # read the yaml file
    curr_name = name
    curr_domain = domain

    print("Interactive asset update:")
    print("=====================================" )

    while True:
        if not first:
            curr_name = input("Enter a hostname: ")
            d = input("Enter a domain: (or press ENTER for 'chtc.wisc.edu) ")
            curr_domain = d if d != "" else "chtc.wisc.edu"
        first = False

        filename = f"{YAML_DIR}{curr_name}.{curr_domain}.yaml"
        asset = yaml_io.Asset(filename)
        filenames.append(filename)

        while True:
            # get input
            key = input("Enter a YAML tag to update: ")

            try:
                asset.get(key)
            except KeyError as err:
                print(f"invalid YAML tag: {key}")
                continue

            value = input("Enter a new value: ")
            asset.put(key, value)

            if input("Update another key? (y/n): ") == 'y':
                continue
            else:
                break

        # write out to the file
        yaml_io.write_yaml(asset, filename)

        if not input("Update a different asset? (y/n): ") == 'y':
            break

    return filenames

def asset_update(args: argparse.Namespace) -> GitData:
    filenames = []

    if args.single:
        name, key, value = args.single
        filenames = update_single(name, args.domain, key, value)
    elif args.batch:
        filenames = update_batch(args.batch)
    elif args.interactive:
        filenames = update_interactive(args.interactive, args.domain)

    # TODO include info about what changed in the commit msg?
    return GitData(
        filenames,
        f"updated {len(filenames)} files",
        "updated \n" + "\n".join([os.path.basename(file) for file in filenames])
    )

# ================ ASSET MOVE FUNCTIONS ====================

def move_single(name: str, domain: str, location: Location) -> list[str]:
    filename = f"{YAML_DIR}{name}.{domain}.yaml"

    keys = [
        "building",
        "room",
        "rack",
        "elevation",
    ]

    # load the asset
    asset = yaml_io.Asset(file=filename)

    # change the location
    for i in range(len(keys)):
        asset.put(f"location.{keys[i]}", location[i])


    # write out to file
    yaml_io.write_yaml(asset, filename)

    return [filename]

def move_interactive(name: str, domain: str) -> list[str]:
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

    filenames = []
    first = True

    # interactive move
    for prompt in prompts:
        opts.append(input(prompt))

    curr_name = name
    curr_domain = domain

    while True:
        if not first:
            curr_name = input("Enter a hostname: ")
            d = input("Enter a domain: (or press ENTER for 'chtc.wisc.edu') ")
            curr_domain = d if d != "" else "chtc.wisc.edu"

        filename = f"{YAML_DIR}{curr_name}.{curr_domain}.yaml"
        asset = yaml_io.Asset(filename)
        filenames.append(filename)

        # for the commit message
        new_locs = []

        for i in range(len(opts)):
            if opts[i] != "":
                asset.put(f"location.{keys[i]}", opts[i])
                new_locs.append(f"{keys[i]}: {opts[i]}")
            else:
                old_loc = asset.get(f"location.{keys[i]}")
                new_locs.append(f"{keys[i]}: {old_loc}")

        # write out update YAML file
        yaml_io.write_yaml(asset, f"{YAML_DIR}{filename}")

        # ask if user wants to move anothe asset
        if not input("Move another asset? (y/n)? ") == 'y':
            break

    return filenames

def asset_move(args: argparse.Namespace) -> GitData:
    if args.single:
        name, building, room, rack, elevation = args.single
        filenames = move_single(name, args.domain, Location(building, room, rack, elevation))
    elif args.interactive:
        filenames = move_interactive(args.interactive, args.domain)

    # TODO include info about where the assets moved in commit msg?
    return GitData(
        filenames,
        f"moved {len(filenames)} assets",
        "moved\n" + "\n".join([os.path.basename(file) for file in filenames])
    )

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

    return GitData(
        [first, second],
        f"swapped the locations of {args.name} and {args.swap_with}",
        ""
    )

# ================ ASSET RENAME FUNCTIONS ====================

def rename_single(name: str, domain: str, newname: str) -> MovedFiles:
    # rename the asset
    filename = f"{YAML_DIR}{name}.{domain}.yaml"
    newname = f"{YAML_DIR}{newname}.{domain}.yaml"

    os.rename(filename, newname)
    return MovedFiles([newname], [filename])

# note: this function would handle a batch rename if one was ever added
# it would just required some more arg-parsing to call the right rename func
def asset_rename(args: argparse.Namespace) -> GitData:
    name, newname = args.single
    filenames = rename_single(name, args.domain, newname)

    # assert len(filenames.added) == len(filenames.removed)

    # do some construction of the commit msg.
    commit_msg = ""
    for i in range(len(filenames.added)):
       commit_msg += f"renamed {os.path.basename(filenames.removed[i])} -> {os.path.basename(filenames.added[i])}" + "\n"

    # format strings don't like the '\n' character :(
    return GitData(
        [filenames.added] + [filenames.removed],
        f"renamed {len([filenames.added])} assets",
        commit_msg
    )

# ================ MAIN AND ARGPARSE FUNCTIONS ====================

def setup_args() -> argparse.Namespace:
    # argparse shenanigans
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="subcommands", dest="command")

    # add an option to auto push
    parser.add_argument("-p", "--push", help="automatically push to the git repo", action="store_true")

    # add a subparser for each subcommand
    add_parser = subparsers.add_parser("add", help="add a new asset")
    rm_parser = subparsers.add_parser("decom", help="decomission an asset")
    move_parser = subparsers.add_parser("move", help="change an asset's location")
    switch_parser = subparsers.add_parser("switch", help="switch the location of two assets")
    rename_parser = subparsers.add_parser("rename", help="rename an asset")
    update_parser = subparsers.add_parser("update", help="change an asset's data")

    parsers = [rename_parser, switch_parser, move_parser, add_parser, rm_parser, update_parser]

    # add common args to each subparser
    for subparser in parsers:
        subparser.add_argument("-d", "--domain", help="defaults to 'chtc.wisc.edu' if not specified", action="store", default="chtc.wisc.edu")

    # add unique args to each subparser
    # add asset args
    add_group = add_parser.add_mutually_exclusive_group(required=True)
    add_group.add_argument("-s", "--single", nargs=2, help="ingest a single asset via YAML file", action="store", metavar=("NAME", "FILE"))
    add_group.add_argument("-b", "--batch", help="ingest one or many assets via a CSV file", action="store", metavar=("CSV_FILE"))
    add_group.add_argument("-i", "--interactive", help="add an asset interactivly via CLI", action="store", metavar=("NAME"))

    # rm asset args
    rm_group = rm_parser.add_mutually_exclusive_group(required=True)
    rm_group.add_argument("-s", "--single", nargs=2, help="decomission a single asset", type=str, action="store", metavar=("NAME", "REASON"))
    rm_group.add_argument("-b", "--batch", help="remove assets in batch mode from a CSV file", type=str, action="store", metavar=("CSV_FILE"))

    # update asset args
    update_group = update_parser.add_mutually_exclusive_group(required=True)
    update_group.add_argument("-s", "--single", nargs=3, help="ingest an asset via a YAML file", action="store", metavar=("NAME", "KEY", "VALUE"))
    update_group.add_argument("-b", "--batch", help="ingest one or many assets via a CSV file", action="store", metavar=("CSV_FILE"))
    update_group.add_argument("-i", "--interactive", help="add an asset interactivly via CLI", action="store", metavar="NAME")


    # asset move args
    move_group = move_parser.add_mutually_exclusive_group(required=True)
    move_group.add_argument("-s", "--single", nargs=5, help="move a single asset", action="store", metavar=("NAME", "BUILDING", "ROOM", "RACK", "ELEVATION"))
    move_group.add_argument("-i", "--interactive", help="add an asset interactivly via CLI", action="store", metavar=("NAME"))

    # asset switch args
    switch_parser.add_argument("-s", "--single", help="switch a single asset's location with another", nargs=2, type=str, action="store", metavar=("NAME", "SWITCH_WITH"))

    # asset rename args
    rename_parser.add_argument("-s", "--single", nargs=2, help="rename a single asset", action="store", metavar=("NAME", "NEW_NAME"))

    args = parser.parse_args()

    if args.command == None:
        parser.print_help()
        exit(1)

    return args

def main():
    args = setup_args()

    # read config
    global YAML_DIR
    global SWAP_DIR

    c = config.get_config("./config.yaml")

    YAML_DIR = c.yaml_path
    SWAP_DIR = c.swapped_path

    # map argument names to their corresponding functions
    func_map = {
        "add" : asset_add,
        "decom"  : asset_rm,
        "update" : asset_update,
        "move" : asset_move,
        "switch" : asset_switch,
        "rename" : asset_rename,
    }

    # setup git
    # tell GitPython that that .git/ is in the current working dir
    global REPO
    REPO = git.Repo(os.path.abspath("./"))

    # check if the repo is clean
    if REPO.is_dirty():
        print()
        print("git error: working tree not clean! There are untracked changes: ")
        print("----------------------------------------------------------------")
        for file in REPO.index.diff(None):
            print(file.a_path)

        print()

        if REPO.untracked_files:
            print("untracked files: ")
            print("-----------------")
            for file in repo.untracked_files:
                print(file)

        print()
        exit(1) # leave it to the user to fix conflicts

    # if the repo is clean pull from origin main
    origin = REPO.remote(name="origin")

    origin.pull("main")

    # call the appropriate function
    # each returns a commit message describing what it did 
    data = func_map[args.command](args)

    # create a commit and push
    REPO.git.add(data.files)
    REPO.git.commit("-m", data.commit_msg, "-m", data.commit_body)

    # don't push by default
    if args.push:
        origin.push("main")

if __name__ == "__main__":
    main()
