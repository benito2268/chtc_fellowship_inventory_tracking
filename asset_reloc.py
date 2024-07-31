#!/bin/python3

# TODO should this script automatically ask you to rename if you change the room?
# updates an asset's physical location
import sys
import os
import subprocess
import argparse
import yaml

sys.path.append(os.path.abspath("scripts/shared/"))
import yaml_io

# TODO replace this once the config is done
YAML_DIR = "./"

def chk_subproc(result: subprocess.CompletedProcess):
    if result.returncode != 0:
        print(f"{' '.join(result.args)} failed")
        exit(1)

def setup_args() -> argparse.Namespace:
    main_parser = argparse.ArgumentParser()
    subparsers = main_parser.add_subparsers(title="subcommands", dest="command")

    # need a sub parser for the 'asset_move switch' option
    switch_parser = subparsers.add_parser("switch", help="switch the locations of assets 'first' and 'second'")
    switch_parser.add_argument("first_host", type=str, action="store")
    switch_parser.add_argument("second_host", type=str, action="store")

    # move options
    move_parser = subparsers.add_parser("move", help="change an asset's location")
    move_parser.add_argument("name", help="the name of the asset to move", action="store")
    main_parser.add_argument("-d", "--domain", help="defaults to 'chtc.wisc.edu' if not specified", action="store", default="chtc.wisc.edu")

    return main_parser.parse_args()

def get_new_location() -> list[str]:

    opts = []
    prompts = [
        "Enter a new elevation: ",
        "Enter a new rack: (press ENTER to keep prev.) ",
        "Enter a new room: (press ENTER to keep prev.) ",
        "Enter a new building: (press ENTER to keep prev.) ",
    ]

    # interactive move
    for prompt in prompts:
        opts.append(input(prompt))

    return opts

def main():
    args = setup_args()

    keys = [
        "elevation",
        "rack",
        "room",
        "building",
    ]

    commit_msg = ""

    # git pull
    result = subprocess.run(["git", "pull"])
    chk_subproc(result)

    # otherwise we need new values
    if args.command == "switch":
        # switch locations
        first = f"{args.first_host}.{args.domain}.yaml"
        second = f"{args.second_host}.{args.domain}.yaml"

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

        # set the commit message and add appropriate files
        commit_msg = f"switched locations of {args.first_host} and {args.second_host}"

        result = subprocess.run(["git", "add", f"{YAML_DIR}{first} {YAML_DIR}{second}"])
        chk_subproc(result)

    elif args.command == "move":
        filename = f"{args.name}.{args.domain}.yaml"

        opts = get_new_location()
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

        # set the commit message and add appropriate files
        commit_msg = f"moved {args.name} to {', '.join(new_locs)}"

        result = subprocess.run(["git", "add", f"{YAML_DIR}{filename}"])
        chk_subproc(result)

    else:
        # TODO is there an argparse way to do this? 
        print("please specify a subcommand - options: 'move', 'switch'")
        exit(1)

    # git add, commit, push
    result = subprocess.run(["git", "commit", "-m", f"\"{commit_msg}\""])
    chk_subproc(result)
    result = subprocess.run(["git", "push"])
    chk_subproc(result)

if __name__ == "__main__":
    main()
