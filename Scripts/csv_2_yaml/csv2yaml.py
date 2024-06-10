import sys
import csv
import yaml

# a wrapper class for quoted yaml string values
# used instead of str so keys are not also quoted
class quoted(str):
    pass

class Asset:

    # a shared (among all Assets) dictionary that maps YAML/dict key names
    # to their corresponding column number in the spreadsheet
    key_map = {
        'room'          : 0,
        'rack'          : 1,
        'elevation'     : 2,
        'hostname'      : 3,
        'domain'        : 4,
        'model'         : 5,
        'serial_number' : 6,
        'identifier'    : 7,
        'service_tag'   : 8,
        'uw'            : 9,
        'csl'           : 10,
        'morgridge'     : 11,
        'notes'         : 12,
    }

    # converts an array of strings (row from the csv file) to a dictionary
    # TODO need a way to detect condos
    def __init__(self, csv_row):
        # each asset is represented with a nested dictionary
        self.asset = {
            'aquisition' : {
                'po'            : "",
                'date'          : "",
                'reason'        : "",
                'owner'         : "",
                'fabrication'   : "",
            },

            'hardware' : {
                'model'         : "",
                'serial_number' : "",
                'service_tag'   : "",
                'purpose'       : "",
                'notes'         : "",
            },

            # TODO revisit this probably
            'condo_chassis' : {
                'identifier'    : "",
                'model'         : "",
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

        self.hostname = csv_row[self.key_map['hostname']]
        self.domain = csv_row[self.key_map['domain']]

        # iterate through each inner and outer key and grab
        # its corresponding value (as determined by key_map) from the spreadsheet
        # TODO detect condos and fabrications (possibly via some sort of heuristic)
        # TODO find location info in puppet repo
        # TODO this bit is in desperate need of a cleanup and fixup - but it's a start
        for outer_key, outer_value in self.asset.items():

            if isinstance(outer_value, dict):

                #if outer_value is a dictionary we need to iterate one level deeper
                for inner_key, inner_value in outer_value.items():
                    cell = self.key_map.get(inner_key, "")
                    if cell == "":
                        value = quoted('MISSING')
                    else:
                        value = quoted(csv_row[cell])

                    self.asset[outer_key][inner_key] = value

# for debugging
def print_dict(d):
    print('\n')
    for x in d:
        print(x, end="")

        if isinstance(x, dict):
            for y in d[x]:
                print('\t', y, ':', d[x][y])
        else:
            print(':', d[x])

# This function is meant to convert the CHTC inventory spreadsheet
# to a yaml file - See INF-1138 in Jira
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
            # print(', '.join(row))
            a = Asset(row)
            assets.append(a)

        return assets
    
# the default Python yaml module doesn't preserve double quotes :(
# can change that behavior with a representer
# see "Constructors, representers, resolvers" in https://pyyaml.org/wiki/PyYAMLDocumentation
def quote_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    
# having a main function might be a good idea?
# if this module is ever imported somewhere for use of csv2yaml()
# but this script is also kind of a one off...
def main():
    # take csv filename as a command line arg
    if len(sys.argv) < 2:
        print("usage: csv2yaml.py <csv_file>")
        exit(1)

    csv_name = sys.argv[1]
    assets = csv_read(csv_name)

    # register the yaml representer for double quoted strings
    yaml.add_representer(quoted, quote_representer)

    with open(assets[0].hostname + '.' + assets[0].domain + ".yaml", 'w') as testfile:
        yaml.dump(assets[0].asset, testfile)

    for a in assets:
        print_dict(a.asset)

if __name__ == "__main__":
    main()
