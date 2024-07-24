#!/bin/python3

# updates fields in an assets YAML file
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
        print(f"{result.args.join(' ')} failed")
        exit(1)

def main():
    parser = argparse.ArgumentParser()

    # required args
    parser.add_argument("key", help="the fully qualified YAML key (tag) to modify. ex) 'hardware.model'", action="store")
    parser.add_argument("value", help="the new value to store", action="store")

    required = parser.add_argument_group(title="required arguments")
    required.add_argument("-n", "--name", help="the name of the asset to swap. ex) 'ap2002'", action="store", required=True)

    # optional args
    parser.add_argument("-d", "--domain", help="defaults to 'chtc.wisc.edu' if not specified", action="store", default="chtc.wisc.edu")
    parser.add_argument("-a", "--add", help="if the key isn't found, add it to the file?", action="store_true")

    args = parser.parse_args()

    # git pull
    result = subprocess.run(["git", "pull"])
    chk_subproc(result)

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

    asset.put(args.key, args.value)

    # write out to the file
    yaml_io.write_yaml(asset, filename)

    # TODO remove once testing done
    exit(0)

    # git add, commit, push
    result = subprocess.run(["git", "add", filename])
    chk_subproc(result)

    # TODO better commit message
    result = subprocess.run(["git", "commit", "-m", f"modified {filename}"])
    chk_subproc(result)

    result = subprocess.run(["git", "push"])
    chk_subproc(result)


if __name__ == "__main__":
    main()
