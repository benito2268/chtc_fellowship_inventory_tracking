# TODO is there a better way to do this?
import sys
import re
import os
sys.path.append(os.path.abspath('../yaml_read/'))

import yaml_read
import errors

# validates the integrity of a single asset
# returns an error object if data is missing
# or None otherwise
def chk_missing(asset):

    # use a regex for ways 'missing' is said in the speadsheet
    # i.e. '', 'none', '???', etc.
    missing_rxp = '(?i)none|missing|\?+|\s*'

    #TODO insert code here to flatten dict

    for key, value in asset.items():
        if re.search(value, missing_rxp):
            #TODO return some error here
            pass

    return None

# validates assets with respect to each other
def chk_conflicting(assets):
    pass

def main():
    if len(sys.argv) != 2:
        print('usage: validate.py <path-to-yaml-files>')
        exit(1)

    path = sys.argv[1]
    if not path.endswith('/'):
        path += '/'

    #assets = yaml_read.read_yaml(path)

    #for asset in assets:
        #chk_missing(asset)

    #chk_conflicting(assets)

    m = errors.MissingDataError('test.yaml', ['hardware.serial: none', 'tags.uw: ']);
    print(m)

if __name__ == '__main__':
    main()
