import sys
import os
import io
import csv
import yaml

sys.path.append(os.path.abspath("../shared"))
sys.path.append(os.path.abspath("scripts/shared"))

import yaml_io
import dict_utils

# the path to puppet site files if that's where site data comes from
# if site data is supplied in the CSV - this is not used
PUPPET_SITE_PATH = "../../puppet/puppet_data/site_tier_0/"

# default map for spreadsheet columns (order of old spreasheet)
# to their corresponding column number in the spreadsheet
# not all tags are mapped because not all come directly from the spreadsheet
INGEST_KEY_MAP = {
    'location.rack'                     : 1,
    'location.elevation'                : 2,
    'hostname'                          : 3,
    'domain'                            : 4,
    'hardware.model'                    : 5,
    'hardware.serial_number'            : 6,
    'hardware.condo_chassis.identifier' : 7,
    'hardware.service_tag'              : 8,
    'tags.uw'                           : 9,
    'tags.csl'                          : 10,
    'tags.morgridge'                    : 11,
    'hardware.notes'                    : 12,
}

class Asset:
    # converts an array of strings (row from the csv file) to a dictionary
    def __init__(self, csv_row: list[str], sites: list, key_map: dict, do_heuristics: bool):
        self.key_map = key_map

        # each asset is represented with a nested dictionary
        self.asset = yaml_io.ASSET_TEMPLATE.copy()

        self.fqdn = csv_row[self.key_map['hostname']]
        if csv_row[self.key_map['domain']] != '':
            self.fqdn += '.' + csv_row[self.key_map['domain']]

        # flatten the dictionary first (with '.' as the seperator)
        # then place place each value according to key_map
        flat = dict_utils.flatten_dict(self.asset)

        for key in flat.keys():
            index = self.key_map.get(key, "")
            fetched = csv_row[index] if index != "" else ""

            flat[key] = fetched

        self.asset = dict_utils.unflatten_dict(flat)

        # some csv reads may want to skip heuristics
        if not do_heuristics:
            return

        # call any heuristics here to help extract misc. data
        notes = csv_row[self.key_map['hardware.notes']]

        self.asset['acquisition']['po'] = yaml_io.quoted(has_po(notes))
        self.asset['acquisition']['fabrication'] = is_fabrication(notes)
        self.asset['acquisition']['owner'] = yaml_io.quoted(find_owner(notes))
        self.asset['hardware']['purpose'] = yaml_io.quoted(find_purpose(notes))

        if sites:
            site = find_site(self.fqdn, sites)
            self.asset['location']['room'] = yaml_io.quoted(site[0])
            self.asset['location']['building'] = yaml_io.quoted(site[1])

# a heuristic for trying to determine if an asset
# is a fabrication from its 'notes' field
def is_fabrication(notes):
    return notes.lower().find('fabrication') >= 0

# a heuristic for trying to determine if an asset
# has a PO # from its 'notes' field
def has_po(notes):
    if notes.lower().find('uw po') >= 0:
        index = notes.find("UW PO")
        index += len("UW PO ")
        return notes[index:]

    return ''

# another (very basic) heuristic to try to fill the owner field from the notes column
# TODO is there a place that we could find this?? should we even worry?
def find_owner(notes):
    # look for a couple of names found in the spreadsheet
    owners = [
        'Yuan Ping',
        'Ben Lindley'
    ]

    for owner in owners:
        if owner.lower() in notes.lower():
            return owner

    return ''

# another heuristic to try to discern the asset's purpose from the notes column
def find_purpose(notes):
    # some common purposes found in the 'notes' column
    keys = [
        'former hpc ',
        'path facility ',
        ' tor',
        ' admin',
    ]

    for key in keys:
        if notes.lower().find(key) >= 0:
            return notes

    return ''

# reads all of the site files in site_dir - do this once
# at the beginning and store results to avoid a very slow script
#
# returns: a dictionary associating filename with the path string read
# from that file
def get_sitefiles(site_dir):
    files = dict()
    for ln_name in os.listdir(site_dir):
            filename = os.readlink('/'.join((site_dir, ln_name)))
            files[ln_name] = filename
    return files


# scans through file read from puppet_data/site_tier_0/ and looks for asset's locations
# returns: a tuple of the form (Room, Building)
def find_site(hostname, file_dict):

    pretty_names = {
        '3370a'   : ('CS3370a', "Computer Sciences"),
        '2360'    : ('CS2360', 'Computer Sciences'),
        'b240'    : ('CSB240', "Computer Sciences"),
        'oneneck' : ('OneNeck', "OneNeck"),
        'wid'     : ('WID', 'WID'),
        'fiu'     : ('FIU', 'FIU'),
        'syra'    : ('Syracuse', 'Syracuse'),
        'syrb'    : ('CS2360', 'Computer Sciences'),
        'wisc'    : ('CS2360', 'Computer Sciences'),
        'unl'     : ('UNL', 'UNL'),
    }

    if hostname + '.yaml' in file_dict:
        sitestr = file_dict[hostname + '.yaml']

        for key, value in pretty_names.items():
            if sitestr.find(key) >= 0:
                return value

    return ('', '')

# This function is meant to convert the CHTC inventory spreadsheet
# into an array of Asset objects containing all of it's data
# 
# params: csv_name - name of the input csv file
# returns: a list of Asset objects as read from the file
def csv_read(csv_name: str, sites_from_puppet: bool, do_heuristics: bool,  key_map: dict =INGEST_KEY_MAP) -> list[Asset]:
    with open(csv_name, newline="") as csvfile:
        # I think the csv module considers this the "excel dialect"
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        assets = []

        # TODO what to do about hard coded path
        # generate the dictionary of sites
        if sites_from_puppet:
            sites = get_sitefiles(PUPPET_SITE_PATH)
        else:
            sites = None

        # skip labels in the first CSV row
        next(reader)

        for row in reader:
            assets.append(Asset(row, sites, key_map, do_heuristics))

        return assets

# This function takes a list of Asset objects and generated a YAML file
# for each one
#
# params:
#   assets: the list of assets to generate from
#
# returns: a list of names of generated asset files
def gen_yaml(assets, path, **kwargs) -> list[str]:
    files = 0
    skipped = 0
    names = []

    for asset in assets:
        hostname = kwargs.get('filename', asset.fqdn)

        # figure out if we should warn about the hostname
        # remove this if too slow - seems okay
        if hostname in names:
            print(f'WARNING: a host with the name {hostname} already exists - skipping')
            print('==========================================================================')
            print('[ASSET THAT WAS SKIPPED]')
            dict_utils.print_dict(asset.asset)

            skipped += 1
            continue

        names.append(hostname)
        files += 1

        if not path.endswith("/"):
            path += "/"

        yaml_io.write_yaml(asset, f"{path}/{hostname}.yaml")

    print(f"csv2yaml: generated {files} files - skipped {skipped} assets with duplicate hostnames")
    return names

def main():
    # take csv filename and output path as command line args
    if len(sys.argv) < 3:
        print("usage: csv2yaml.py <csv_file> <output_path>")
        exit(1)

    csv_name = sys.argv[1]
    output_path = sys.argv[2]
    assets = csv_read(csv_name, True, True)

    # for quality of life's sake
    if output_path[-1] != '/':
        output_path += '/'

    gen_yaml(assets, output_path)

if __name__ == "__main__":
    main()
