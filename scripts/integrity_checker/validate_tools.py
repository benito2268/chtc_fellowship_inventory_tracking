# this file contains helper functions used in validate.py
import sys
import re
import itertools
import os
sys.path.append(os.path.abspath('../shared'))

import yaml_io
import errortypes

# regex to match possible ways of saying 'missing'
missing_rxp = "(?i)none|missing|\\?+|^\\s*$"

# groups assets that share a certain attribute
#
# params:
#   assets: list of all assets
#   key: the attribute to group by (in YAML style ex. 'location.rack')
#
# returns: a list[list[yaml_io.Asset]] - a list of groups
#          all assets in a group posess the same value for the given key
#
def group_by_attrib(assets: list, key: str):
    ret_group = []

    if key == 'location.rack' or key == 'location.elevation':
        # want to compare location as a whole
        keyfunc = lambda a: a.get_full_location()
    else:
        keyfunc = lambda a: a.get(key)

    grp_list = list(filter(lambda a: not re.fullmatch(missing_rxp, a.get(key)), assets))

    # now group by each asset by value corresponding to key
    grp_list = sorted(grp_list, key=keyfunc)
    for k, g in itertools.groupby(grp_list, keyfunc):
        group = list(g)
        if len(group) > 1:
            ret_group.append(group)

    return ret_group

# makes validations of the form "all assets that share X must share Y"
#
# params:
#   groups: a list of groups (lists) of Assets grouped by X
#           most likely returned by get_key_grps()
#   tag: the tag to validate
#   msg: an error message to display if the validation fails
#
# returns: a list of ConflictingGroupErrors or None if no conflicts are found
#
def get_conflicts(shared_tag: str, groups: list, tag: str, msg: str): 
    errs = []
    for group in groups[shared_tag]:
        conflicting = []
        for asset in group:
            # gather all conflicting items
            if tag == 'location.rack' or tag == 'location.elevation':
                value = asset.get_full_location()
            else:
                value = asset.get(tag)

            # do we really want to account for missing things? - UW tags make no sense
            if (re.fullmatch(missing_rxp, value)):
                conflicting.append(errortypes.ConflictItem(asset.fqdn + '.yaml', asset.get(shared_tag) , value))

        if conflicting:
            errs.append(errortypes.ConflictingGroupError(conflicting, msg))

    return errs if errs else None
