import sys
import os
import io
import csv
import yaml

# yet TODO on this script
# 1. figure out locations
# 2. tweak some of the heuristics
# 3. print warnings for bad data

# a wrapper class for quoted yaml string values
# used instead of str so keys are not also quoted
class quoted(str):
    pass

class Asset:
    # a shared (among all Assets) dictionary that maps YAML/dict key names
    # to their corresponding column number in the spreadsheet
    # not all tags are mapped because not all come directly from the spreadsheet
    key_map = {
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

    # converts an array of strings (row from the csv file) to a dictionary
    def __init__(self, csv_row):
        # each asset is represented with a nested dictionary
        self.asset = {
            'acquisition' : {
                'po'            : "",
                'date'          : "",
                'reason'        : "",
                'owner'         : "",
                'fabrication'   : False,
            },

            'hardware' : {
                'model'         : "",
                'serial_number' : "",
                'service_tag'   : "",
                'purpose'       : "",
                'notes'         : "",

                'condo_chassis' : {
                    'identifier'    : "",
                    'model'         : "",
                },
            },

            'location' : {
                'rack'      : "",
                'elevation' : "",
                'room'      : "",
                'building'  : "",
            }, 

            'tags' : {
                'csl'       : "",
                'uw'        : "",
                'morgridge' : "",
            },
        }

        self.fqdn = csv_row[self.key_map['hostname']] + '.' + csv_row[self.key_map['domain']]

        # flatten the dictionary first (with '.' as the seperator)
        # then place place each value according to key_map
        # TODO find location info in puppet repo
        flat = flatten_dict(self.asset)
        
        for key in flat.keys():

            index = self.key_map.get(key, "")
            fetched = quoted(csv_row[index]) if index != "" else quoted("")
            
            flat[key] = fetched

            determine_missing(flat)

        self.asset = unflatten_dict(flat)

        # call any heuristics here to help extract misc. data
        notes = csv_row[self.key_map['hardware.notes']]

        self.asset['acquisition']['po'] = quoted(has_po(notes))
        self.asset['acquisition']['fabrication'] = is_fabrication(notes)
        self.asset['acquisition']['owner'] = quoted(find_owner(notes))
        self.asset['hardware']['purpose'] = quoted(find_purpose(notes))

        site = find_site(self.fqdn, '../../Puppet/puppet_data/site_tier_0/')
        self.asset['location']['room'] = quoted(site[0])
        self.asset['location']['building'] = quoted(site[1])


# for debugging
def print_dict(d):

    flat = flatten_dict(d)

    for key, value in flat.items():
        print(key, ':', value)
    
    print('\n')

# flattens a dictionary with '.' as the seperator
#
# params:
#   nested - current dictionary to be flattened
#   parent_key - the (already flattened) path the leads to nested - used by the recursive call only
# returns:
#   a dictionary that maps a 'path' to each bottom level value in the original
#   ex) an entry would look like  "hardware.condo_chassis.model" : "Dell PowerEdge ..." 
def flatten_dict(nested, parent_key=''):
    # using a list means we have append() and extend()
    flat = []
    for key, value in nested.items():
        if parent_key == '':
            # we're at the top level
            newkey = key
        else:
            # we're somewhere in a nested level
            newkey = parent_key + '.' + key
        
        if isinstance(value, dict):
            # if value is a dictionary - recurse further in
            flat.extend(flatten_dict(value, newkey).items())
        else:
            # otherwise, we've hit the base case - append and return once
            flat.append((newkey, value))
        
    return dict(flat)

# unflattens (nests) a dictionary with '.' as the seperator
def unflatten_dict(flat):
    ret = dict()

    for key, value in flat.items():
        tags = key.split('.')
        sub_dict = ret

        # re-nest all of the levels - not yet worrying about values
        # the last value in the list is the 'leaf' tag - so ignore it for now
        for tag in tags[:-1]:
            if tag not in sub_dict:
                sub_dict[tag] = dict()

            sub_dict = sub_dict[tag]

        # now put the value in the new 'leaf' tag
        sub_dict[tags[-1]] = value

    return ret

# for each tag with a value of "", determine whether or not we should
# complain about it being missing
#
# params:
#   flat_dict: a flattened dictionary representing the asset
#
def determine_missing(flat_dict):
    for key, value in flat_dict.items():

        if value == "":
            # not every asset NEEDS notes
            if key != 'hardware.notes':
                flat_dict[key] = quoted('MISSING')


            # for now don't worry about the model unless there's an ID
            # later scripts might do more to decide if this is okay or not
            elif key == 'hardware.condo_chassis.model':
                if flat_dict['hardware.condo_chassis.identifier']: 
                    flat_dict[key] = quoted("")

# the default Python yaml module doesn't preserve double quotes :(
# can change that behavior with a representer
# see "Constructors, representers, resolvers" in https://pyyaml.org/wiki/PyYAMLDocumentation
def quote_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

# a heuristic for trying to determine if an asset
# is a fabrication from its 'notes' field
# params:
#   notes: the notes section from the elevation spreadsheet
#
# returns: True if fabrication, false if not
def is_fabrication(notes):
    return notes.lower().find('fabrication') >= 0

# a heuristic for trying to determine if an asset
# has a PO # from its 'notes' field
# params:
#   notes: the notes section from the elevation spreadsheet
#
# returns: the PO # if one was found - 'MISSING' otherwise
def has_po(notes):
        # we assume it is, try to return the PO
    if notes.lower().find('uw po') >= 0:
        index = notes.find("UW PO")
        index += len("UW PO ")

        return notes[index:]
    else:
        return 'MISSING'

# another (very basic) heuristic to try to fill the owner field from the notes column
#
# params:
#   notes:  the notes column in the inventory spreadsheet
# returns:
#   a string containing the owner (CHTC is assumed if none other is found)
# TODO is there a place that we could find this?? should we even worry?
def find_owner(notes):
    # look for a couple of names found in the spreadsheet
    if notes.lower().find('yuan ping chassis') >= 0:
        return 'Yuan Ping'
    elif notes.lower().find('ben lindley chassis') >= 0:
        return 'Ben Lindley'

    return 'CHTC'

# another heuristic to try to discern the asset's purpose from the notes column
#
# params:
#   notes: the notes column in the inventory spreadsheet
# returns:  
#   a string containing the purpose, or 'MISSING if none
def find_purpose(notes):
    # some nodes are maked as 'former HPC'
    if notes.lower().find('former hpc') >= 0:
        return notes
    elif notes.lower().find('path facility') >= 0:
        return notes

    return 'MISSING'

# reads all of the site files in site_dir
#
# returns: a dictionary associating filename with the string read
# from that file
def get_sitefiles(site_dir):
    files = dict()
    for filename in os.listdir(site_dir):
        if filename == hostname + '.yaml':
            
            with open(site_dir + hostname + '.yaml', 'r') as sitefile:
                sitestr = sitefile.read()
                files[filename] = sitestr
    return files


# scans through file read from puppet_data/site_tier_0/ and looks for asset's locations
#
# returns: a tuple of the form (Room, Building)
def find_site(hostname, file_dict):


    if hostname + '.yaml' in file_dict:
        sitestr = file_dict[hostname + '.yaml']

        # this part is not super pretty - but it does work
        if sitestr.find('3370a') >= 0:
            return ('CS3370a', "Computer Sciences")
        elif sitestr.find('b240') >= 0:
            return ('CSB240', "Computer Sciences")
        elif sitestr.find('oneneck') >= 0:
            return ('OneNeck', "OneNeck")
        elif sitestr.find('wid') >= 0:
            return ('WID', 'WID')
        elif sitestr.find('fiu') >= 0:
            return ('FIU', 'FIU') 
        elif sitestr.find('2360') or sitestr.find('syrb') >= 0 or sitestr.find('wisc') >= 0:
            return ('CS2360', 'Computer Sciences')
        elif sitestr.find('syra') >= 0:
            return ('Syracuse', 'Syracuse')
        elif sitestr.find('unl') >= 0:
            return ('UNL', 'UNL')
    else:    
        return ('MISSING', 'MISSING')


    

# This function is meant to convert the CHTC inventory spreadsheet
# into an array of Asset objects containing all of it's data
# 
# params: csv_name - name of the input csv file
# returns: a list of Asset objects as read from the file
def csv_read(csv_name): 
    with open(csv_name, newline="") as csvfile:

        # I think the csv module considers this the "excel dialect"
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        assets = []

        # skip labels in the first CSV row
        next(reader)

        for row in reader:
            a = Asset(row)
            assets.append(a)

        return assets

# This function takes a list of Asset objects and generated a YAML file
# for each one
#
# params:
#   assets: the list of assets to generate from
def gen_yaml(assets):
    # register the yaml representer for double quoted strings
    yaml.add_representer(quoted, quote_representer)

    files = 0
    warnings = 0
    names = []

    # write files with unix (LF) line endings
    for asset in assets:

        hostname = asset.fqdn 

        # figure out if we should warn about the hostname
        # remove this if too slow seems okay
        if hostname in names:
            print('WARNING: a host with the name', hostname, 'already exists - skipping')
            print('==========================================================================')
            print('[ASSET THAT WAS SKIPPED]')
            print_dict(asset.asset)
            warnings += 1
            continue

        names.append(hostname)
        files += 1

        # TODO remove 'yaml/' 
        with open('yaml/' + hostname + '.yaml', 'w', newline='\n') as outfile:
            yaml.dump(asset.asset, outfile, sort_keys=False)
        
    print('csv2yaml: generated', files, 'files - skipped', warnings, 'assets with duplicate hostnames')
        
def main():
    # take csv filename as a command line arg
    if len(sys.argv) < 2:
        print("usage: csv2yaml.py <csv_file>")
        exit(1)

    csv_name = sys.argv[1]
    assets = csv_read(csv_name)

    gen_yaml(assets)

if __name__ == "__main__":
    main()
