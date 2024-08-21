#!/bin/python3

import sys
import re
import os
import io
import itertools
import argparse
import datetime
import smtplib
import email
from collections import defaultdict
from typing import Callable

sys.path.append(os.path.abspath("../shared"))
sys.path.append(os.path.abspath("scripts/shared/"))

import yaml_io
import config
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
        'tags.uw',
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

def chk_all_missing(assets: list):
    errs = []
    
    for asset in assets:
        err = chk_single_missing(asset)
        if err:
            errs.append(err)

    return errs
        
# validates assets with respect to each other
def chk_conflicting(assets: list):

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
    location_conflicts = validate_tools.get_conflicts('location.rack', groups, 
                                'hardware.condo_chassis.identifier', 
                                'assets share rack-elevation without common hardware.condo_chassis.identifier')

    if location_conflicts != None:
        errs.extend(location_conflicts)

    # check condo_id against rack
    condo_id_confls = validate_tools.get_conflicts('hardware.condo_chassis.identifier', groups, 
                                           'location.rack', 
                                           'assets share hardware.condo_chassis.id but show different rack-elevation') 
    if condo_id_confls != None:
        errs.extend(condo_id_confls)

    
    # check tags.uw against hardware.condo_chassis.identifier OR acquisition.fabrication    
    condo_tag_confls = validate_tools.get_conflicts('tags.uw', groups,
                                    'hardware.condo_chassis.identifier',
                                    'assets share UW tags, but do not belong to a common condo or fabrication')
    if condo_tag_confls != None:
        for group in groups['tags.uw']:
            for a in group:
                if a.get('acquisition.fabrication') != True:
                    errs.extend(condo_tag_confls)
                    return errs

    return errs

def chk_uw_tag(assets: list):
    errs = []

    for asset in assets:
        if re.fullmatch(missing_rxp, asset.get('tags.uw')):
            asset_date = asset.get('acquisition.date')
            if re.fullmatch(missing_rxp, asset_date):
                errs.append(errortypes.MissingDataError(asset.fqdn + '.yaml', ['tags.uw'], 'asset with no purchase date lacks UW tag'))
                continue

            # uses ISO 8601 date format (aka. yyyy-mm-dd)
            fmt = '%Y-%m-%d'
            currdate = datetime.datetime.today()
            olddate = datetime.datetime.strptime(asset_date, fmt)

            diff = currdate - olddate

            # warn about a missing UW tag if it's been more than 180 days
            if diff.days >= 180:
                errs.append(errortypes.MissingDataError(asset.fqdn + '.yaml', ['tags.uw'], f'asset with PO: "{asset.get("acquisition.po")}" purchased on {asset_date} lacks UW tag'))

    return errs

# performs the validation and outputs the results
# if email_addr is '' - will output to stdout otherwise
# will send and email to the specified address
#
# params:
#   assets: list of assets to check
#   chk_fun: the checking function - returns a list of DataError
#   email_addr: email address to send to - if any
#
def output_chks(errs: list[errortypes.DataError], email_addr: str='', yaml_path: str=''):
    output = io.StringIO()
    for err in errs:
        print(err, file=output)
        
    if email_addr:
        # TODO if this becomes some sort of ci/cd or cron job - should figure
        # out a way to avoid spamming people's inboxes
        header = '[this message was auto-generated by validate.py]\n\n'
        header += f'The following asset data errors were found in {yaml_path}:\n\n'

        # append to the err messages
        email_out = io.StringIO()
        email_out.write(header)
        email_out.write(output.getvalue())

        msg = email.message.EmailMessage()
        msg.set_content(email_out.getvalue())

        msg['Subject'] = 'Asset Data Validation Errors'
        msg['From'] = 'no_reply@example.com'
        msg['To']  = email_addr

        # send the message via a (very briefly alive) local SMTP server
        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()

        email_out.close()

    else:
        print(output.getvalue())

    output.close()


def main():
    # set up command line options
    parser = argparse.ArgumentParser()

    # add new options here
    parser.add_argument('-m', '--missing', help='only check for asset tags that are missing values', action='store_true')
    parser.add_argument('-c', '--conflicting', help='only check for conflicting asset data', action='store_true')
    parser.add_argument('-u', '--uwtag', help='check for missing UW tags on assets older than 180 days', action='store_true')
    parser.add_argument('-p', '--path', help='the path to a directory containing YAML asset files to validate', type=str)

    args = parser.parse_args()

    # dict of functions called during validate
    # keys match the long command-line options
    # it should invoke
    validate_funcs = {
        'missing'     : chk_all_missing,
        'conflicting' : chk_conflicting,
        'uwtag'       : chk_uw_tag,
    }

    # scripts can be run 'manually' too
    yaml_path = ""
    if args.path:
        yaml_path = args.path
    else:
        # get yaml path from config
        # NOTE: scripts are from from the same dir as config.yaml in the GitHub action
        yaml_path = config.get_config("config.yaml").yaml_path

    # read all yaml files from the dir. at yaml_path
    assets = yaml_io.read_yaml(yaml_path)

    # if no optional arguments are specified - run all checks
    opts = vars(args)
    checks = [opts[key] for key in validate_funcs]

    errs = []
    if not any(checks):
        for fun in validate_funcs.values():
             errs.extend(fun(assets))
    else:
        for fun in checks:
            if fun:
                errs.extend(fun(assets))

    output = output_chks(errs, args.email, yaml_path)

if __name__ == '__main__':
    main()
