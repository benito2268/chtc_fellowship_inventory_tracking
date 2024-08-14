import sys
import os
import yaml
import dict_utils

YAML_PATH = "../../data/"

# a wrapper class for quoted yaml string values
# used instead of str so keys are not also quoted
class quoted(str):
    pass

# the default Python yaml module doesn't preserve double quotes :(
# can change that behavior with a representer
# see "Constructors, representers, resolvers" in https://pyyaml.org/wiki/PyYAMLDocumentation
def quote_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')


ASSET_TEMPLATE = {
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
        'swap_reason'   : "",
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

# possible kwargs:
#   file="filename"
#   fqdn="fqdn"
class Asset:
    def __init__(self, file="", fqdn=""):
        if file:
            with open(file, 'r') as infile:
                # as far as I can tell safe_load doesn't have any relevant
                # disadvantages over load() here - maybe it's overkill but might as well
                self.asset = yaml.safe_load(infile)
                self.filepath = file
                self.fqdn = os.path.basename(file).removesuffix('.yaml')
        elif fqdn:
            # generate a blank template
            self.asset = ASSET_TEMPLATE.copy()
            self.fqdn = fqdn
            self.filename = f"{self.fqdn}.yaml"

    # returns a string (most likly used for comparison)
    # of the assets full location
    # separated but '.' "elev.rack.room.building"
    def get_full_location(self):
        return '.'.join( (self.asset['location']['elevation'], self.asset['location']['rack'], self.asset['location']['room'], self.asset['location']['building']) )

    # returns a data field from it's yaml style path (ex. location.rack)
    # this function eliminates some need for flattening and un-flattening
    def get(self, key: str):
        flat = dict_utils.flatten_dict(self.asset)
        ret = flat[key]
        self.asset = dict_utils.unflatten_dict(flat)
        return ret

    # stores value in the internal asset dict
    # takes a 'flat dict' yaml style tag (ex. location.rack)
    def put(self, key: str, value: str):
        flat = dict_utils.flatten_dict(self.asset)
        flat[key] = value
        self.asset = dict_utils.unflatten_dict(flat)

# reads YAML data from all .yaml files in yaml_dir
#
# params:
#   yaml_dir - the directory to read YAML from
#
# returns: a list of Asset objects corresponding to each file
def read_yaml(yaml_dir: str) -> list[Asset]:
    # allow dirs to be typed without the '/'
    if not yaml_dir.endswith('/'):
        yaml_dir += '/'

    ret = []

    for file in os.listdir(yaml_dir):
        if file.endswith('.yaml'):
            ret.append(Asset(yaml_dir + file))

    return ret

# writes Asset objects to YAML files
#
# params:
#   asset - the Asset object to write
#   filepath - where to output the yaml file
def write_yaml(asset: Asset, filepath: str):
    # register the yaml representer for double quoted strings
    yaml.add_representer(quoted, quote_representer)

    # newline='\n' writes files with unix (LF) line endings
    with open(filepath, 'w', newline='\n') as outfile:
        yaml.dump(asset.asset, outfile, sort_keys=False)


def main():
    assets = read_yaml(YAML_DIR)

if __name__ == '__main__':
    main()
