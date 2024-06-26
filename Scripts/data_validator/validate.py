import sys
import re
import os
import itertools
import argparse
from collections import defaultdict
from pprint import pprint

# finishing touch: is there a better way to do this?
sys.path.append(os.path.abspath('../shared'))
import yaml_io
import dict_utils
import validate_tools
import errortypes

# regex to match possible ways of saying 'missing'
missing_rxp = "(?i)none|missing|\\?+|^\\s*$"

# checks a single asset for missing data fields
#
# params:
#   asset: a yaml_io.Asset object
#
# returns: a a MissingDataError or None
def chk_single_missing(asset: yaml_io.Asset):
    bad_tags = []

    # a list of keys that are exempt from 'missing' checks
    exempt_keys = [
        'acquisition.reason',
        'tags.morgridge',
        'tags.csl',
        'hardware.notes',
        'hardware.swap_reason',
        'hardware.condo_chassis.identifier',
    ]

    # condo model is conditional - if condo id not present - ignore it
    if re.fullmatch(missing_rxp, asset.get('hardware.condo_chassis.identifier')):
        exempt_keys.append('hardware.condo_chassis.model')   

    # use a regex for ways 'missing' is said in the speadsheet
    # i.e. '', 'none', '???', etc.
    flat = dict_utils.flatten_dict(asset.asset)
    for key, value in flat.items():
        if key not in exempt_keys and re.fullmatch(missing_rxp, str(value)):
            bad_tags.append(': '.join((key, str(value))))

            # MISSING will be the 'magic string'
            asset.put(key, yaml_io.quoted('MISSING'))

    if bad_tags:
        # write back changes we've made and return and error
        yaml_io.write_yaml(asset, asset.filepath)
        return errortypes.MissingDataError(asset.fqdn + '.yaml', bad_tags, 'tags are missing values')

    # otherwise no error - return None
    return None


# validates assets with respect to each other
def chk_conflicting(assets):

    # list of keys we want to grab
    # adding a key here will make the next expression groups for it
    keys = [
        'location.rack',
        'acquisition.po',
        'hardware.condo_chassis.identifier',
        'tags.uw',
    ]

    groups = { key:validate_tools.group_by_attrib(assets, key) for key in keys}

    # run checks to compare groups as follows
    # - a group with the same rack and elevation should all share hardware.condo_chassis.identifier
    # - a group with the same hardware.condo_chassis.identifier should all share rack + elevation
    # - a group with the same UW tag should share a condo chassis OR be part of a fabrication
    # - a group with the same UW PO # should share a condo chassis OR be part of a fabrication

    errs = []

    # check rack against condo_chassis.identifier
    # TODO account for elevation 'ranges' instead of checking pure equality
    location_conflicts = validate_tools.get_conflicts(groups['location.rack'], 
                                'hardware.condo_chassis.identifier', 
                                'assets share rack-elevation without common hardware.condo_chassis.identifier')

    if location_conflicts != None:
        errs.extend(location_conflicts)

    # check condo_id against rack
    condo_id_confls = validate_tools.get_conflicts(groups['hardware.condo_chassis.identifier'], 
                                           'location.rack', 
                                           'assets share hardware.condo_chassis.id but show different rack-elevation') 
    if condo_id_confls != None:
        errs.extend(condo_id_confls)

    # check tags.uw against hardware.condo_chassis.identifier OR acquisition.fabrication    
    condo_tag_confls = validate_tools.get_conflicts(groups['tags.uw'],
                                    'hardware.condo_chassis.identifier',
                                    'assets share UW tags, but do not belong to a common condo or fabrication')
    if condo_tag_confls != None:
        for group in groups['tags.uw']:
            for a in group:
                if a.get('acquisition.fabrication') != True:
                    errs.extend(condo_tag_confls)
                    return errs

    return errs

def do_chk_missing(assets):
    missing = 0

    for asset in assets:
        err = chk_single_missing(asset)
        if err:
            print(err)
            print()
            missing += 1

    print('validate: found {0} assets with missing tags'.format(missing))

def do_chk_conflicting(assets):
    errs = chk_conflicting(assets)

    for err in errs:
        print(err)
        print()

    print(f'validate: found {len(errs)} conflicting items')
    
def main():
    # set up command line options
    parser = argparse.ArgumentParser()

    # add new options here
    parser.add_argument('-m', '--missing', help='only check for asset tags that are missing values', action='store_true')
    parser.add_argument('-c', '--conflicting', help='only check for conflicting asset data', action='store_true')
    parser.add_argument('yaml_path', help='the path to a directory containing YAML asset files to validate', type=str)

    args = parser.parse_args()

    # dict of functions called during validate
    # keys match the long command-line options
    # it should invoke
    validate_funcs = {
        'missing'     : do_chk_missing,
        'conflicting' : do_chk_conflicting,
    }

    # read all yaml files from the dir. at yaml_path
    assets = yaml_io.read_yaml(args.yaml_path)

    # if no optional arguments are specified - run all checks
    opts = vars(args)
    if len(sys.argv) < 3: 
        for value in validate_funcs.values():
            value(assets) 
    else:
        for key, value in validate_funcs.items():
            if opts[key]:
                value(assets)

if __name__ == '__main__':
    main()
