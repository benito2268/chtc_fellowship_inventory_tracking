# TODO is there a better way to do this?
import sys
import re
import os
sys.path.append(os.path.abspath('../shared'))
import yaml_read
import dict_utils
import errors 

# validates the integrity of a single asset
# returns an error object if data is missing
# or None otherwise
def chk_missing(asset):

    missing_rxp = "(?i)none|missing|\\?+|^\\s*$"

    flat = dict_utils.flatten_dict(asset.asset)
    bad_tags = []

    # a list of keys that are exempt from validity checks
    exempt_keys = [
        'tags.morgridge',
        'tags.csl',
        'hardware.notes',
        'acquisition.reason',
        'hardware.condo_chassis.identifier',
    ]

    # condo model is conditional - check it now
    if re.fullmatch(missing_rxp, flat['hardware.condo_chassis.identifier']):
        exempt_keys.append('hardware.condo_chassis.model')   

    # use a regex for ways 'missing' is said in the speadsheet
    # i.e. '', 'none', '???', etc.
    for key, value in flat.items():
        if key not in exempt_keys and re.fullmatch(missing_rxp, str(value)):
            bad_tags.append(': '.join((key, str(value))))

    if bad_tags:
        return errors.MissingDataError(asset.fqdn + '.yaml', bad_tags, 'tags are missing values')

    # otherwise no error - return None
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

    assets = yaml_read.read_yaml(path)
    missing = 0

    for asset in assets:
        err = chk_missing(asset)
        if err:
            print(err)
            print()
            missing += 1

    chk_conflicting(assets)

    print('found {0} assets with missing tags'.format(missing))

if __name__ == '__main__':
    main()
