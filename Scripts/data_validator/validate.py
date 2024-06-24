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
import errors 

# validates the integrity of a single asset
# returns an error object if data is missing
# or None otherwise
def chk_single_missing(asset):
    missing_rxp = "(?i)none|missing|\\?+|^\\s*$"

    flat = dict_utils.flatten_dict(asset.asset)
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
    if re.fullmatch(missing_rxp, flat['hardware.condo_chassis.identifier']):
        exempt_keys.append('hardware.condo_chassis.model')   

    # use a regex for ways 'missing' is said in the speadsheet
    # i.e. '', 'none', '???', etc.
    for key, value in flat.items():
        if key not in exempt_keys and re.fullmatch(missing_rxp, str(value)):
            bad_tags.append(': '.join((key, str(value))))

            # MISSING will be the 'magic string'
            flat[key] = 'MISSING' 

    if bad_tags:
        # unflatten and re-write if we made any changes
        asset.asset = dict_utils.unflatten_dict(flat)
        yaml_io.write_yaml(asset, asset.filepath)
        return errors.MissingDataError(asset.fqdn + '.yaml', bad_tags, 'tags are missing values')

    # otherwise no error - return None
    return None

# returns a list of lists that contain groups
# of assets that share the same (non-missing) value
# for the given key
def get_key_grp(assets, key):
    ret_group = []
    missing_rxp = "(?i)none|missing|\\?+|^\\s*$"

    if key == 'location.rack' or key == 'location.elevation':
        # room, rack, and elevation are kind of tied together
        keyfunc = lambda a: a.asset['location.room'] + a.asset['location.rack'] + a.asset['location.elevation']
    else:
        keyfunc = lambda a: a.asset[key]

    # remove assets missing the key
    flats = assets.copy()
    for asset in flats:
        asset.asset = dict_utils.flatten_dict(asset.asset)

    grp_list = list(filter(lambda a: not re.fullmatch(missing_rxp, a.asset[key]), flats))

    # now group by each asset by value corresponding to key
    grp_list = sorted(grp_list, key=keyfunc)
    for k, g in itertools.groupby(grp_list, keyfunc):
        group = list(g)
        if len(group) > 1:
            ret_group.append(group)

    return ret_group

# returns a ConflictingDataError if assets conflict, otherwise returns None
def get_conflicts(groups, tag, msg):
    errs = []
    for group in groups:
        first = group[0]
 
        conflicting = []
        for asset in group:
            # gather all conflicting items
            if asset.asset[tag] != first.asset[tag]:
                conflicting.append( (asset.fqdn, asset.asset[tag]) )

        if conflicting:
            errs.append(errors.ConflictingDataError((first.fqdn, first.asset[tag]), conflicting, msg))

    return errs if errs else None


# validates assets with respect to each other
def chk_conflicting(assets):

    # list of keys we want to grab
    # adding a key here will fetch and return its group
    keys = [
        'location.rack',
        'acquisition.po',
        'hardware.condo_chassis.identifier',
        'tags.uw',
    ]

    groups = { key:get_key_grp(assets, key) for key in keys}

    # run checks to compare groups as follows
    # - a group with the same rack and elevation should all share hardware.condo_chassis.identifier
    # - a group with the same hardware.condo_chassis.identifier should all share rack + elevation
    # - a group with the same UW tag should share a condo chassis OR be part of a fabrication
    # - a group with the same UW PO # should share a condo chassis OR be part of a fabrication

    errs = []

    # check rack against condo_chassis.identifier
    # TODO account for elevation 'ranges' instead of checking pure equality
    rack_confls = get_conflicts(groups['location.rack'], 
                                'hardware.condo_chassis.identifier', 
                                'assets share rack-elevation without common hardware.condo_chassis.identifier')

    if rack_confls != None:
        errs.extend(rack_confls)

    # check condo_id against rack
    condo_id_confls = get_conflicts(groups['hardware.condo_chassis.identifier'], 
                                           'location.rack', 
                                           'assets share hardware.condo_chassis.id but show different rack-elevation') 
    if condo_id_confls != None:
        errs.extend(condo_id_confls)

    # check tags.uw against hardware.condo_chassis.identifier OR acquisition.fabrication
    
    
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
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-m', '--missing', help='only check for asset tags that are missing values', action='store_true')
    group.add_argument('-c', '--conflicting', help='only check for conflicting asset data', action='store_true')
    parser.add_argument('yaml_path', help='the path to a directory containing YAML asset files to validate', type=str)

    args = parser.parse_args()

    assets = yaml_io.read_yaml(args.yaml_path)
    missing = 0

    if args.missing:
        do_chk_missing(assets)

    elif args.conflicting:
        do_chk_conflicting(assets)

    else:
        # check for both
        do_chk_missing(assets)
        do_chk_conflicting(assets)

if __name__ == '__main__':
    main()
