import sys
import os
import yaml

# TODO notes:
# read all .yaml files from a dir?
#   - this seems right since we will need all for something like a spreadsheet
#   - could add the option to check integrity of 1 at a time
#
# this will probably only be used as a standalone script when checking yaml
#   - do we want to seperate script for that? - first impression says yes

class Asset:
    def __init__(self, filename):
        with open(filename, 'r') as infile:

            # as far as I can tell safe_load doesn't have any relevant
            # disadvantages over load() here - maybe it's overkill but might as well
            self.asset = yaml.safe_load(infile)

def read_yaml(yaml_dir):
    ret = []

    for file in os.listdir(yaml_dir):
        if file.endswith('.yaml'):
            ret.append(Asset(yaml_dir + file))

    return ret


def main():

    if len(sys.argv) != 2:
        print('usage: yaml_read.py <yaml_dir>')
        exit(1)

    yaml_dir = sys.argv[1]
    
    assets = read_yaml(yaml_dir)

    # for testing
    for asset in assets:
        print(asset.asset['hardware']['model'])

if __name__ == '__main__':
    main()
