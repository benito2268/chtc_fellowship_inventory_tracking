import sys
import os
import yaml

# a wrapper class for quoted yaml string values
# used instead of str so keys are not also quoted
class quoted(str):
    pass

# the default Python yaml module doesn't preserve double quotes :(
# can change that behavior with a representer
# see "Constructors, representers, resolvers" in https://pyyaml.org/wiki/PyYAMLDocumentation
def quote_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

class Asset:
    def __init__(self, filename):
        with open(filename, 'r') as infile:

            # as far as I can tell safe_load doesn't have any relevant
            # disadvantages over load() here - maybe it's overkill but might as well
            self.asset = yaml.safe_load(infile)

        self.filepath = filename
        self.fqdn = os.path.basename(filename).removesuffix('.yaml')

def read_yaml(yaml_dir):
    # for ease of use
    if not yaml_dir.endswith('/'):
        yaml_dir += '/'

    ret = []

    for file in os.listdir(yaml_dir):
        if file.endswith('.yaml'):
            ret.append(Asset(yaml_dir + file))

    return ret

def write_yaml(asset, filepath):

    # register the yaml representer for double quoted strings
    yaml.add_representer(quoted, quote_representer)

    # newline='\n' writes files with unix (LF) line endings
    with open(filepath, 'w', newline='\n') as outfile:
        yaml.dump(asset.asset, outfile, sort_keys=False)


def main():

    if len(sys.argv) != 2:
        print('usage: yaml_read.py <yaml_dir>')
        exit(1)

    yaml_dir = sys.argv[1]
    
    assets = read_yaml(yaml_dir)

if __name__ == '__main__':
    main()
