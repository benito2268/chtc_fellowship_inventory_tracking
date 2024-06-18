# TODO is there a better way to do this?
import sys
import os
sys.path.append(os.path.abspath('../yaml_read/'))

import yaml_read

# main validation function
def validate_asset(asset):
    pass

def main():
    if len(sys.argv) != 2:
        print('usage: validate.py <path-to-yaml-files>')
        exit(1)

    path = sys.argv[1]
    if not path.endswith('/'):
        path += '/'

    assets = yaml_read.read_yaml(path)

    for asset in assets:
        validate_asset(asset)

if __name__ == '__main__':
    main()
