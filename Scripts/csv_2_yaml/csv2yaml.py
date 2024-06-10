import sys
import csv

class Asset:

    # a shared (among all Assets) dictionary that maps YAML/dict key names
    # to their corresponding column number in the spreadsheet
    key_map = {
        'room'          : 0,
        'rack'          : 1,
        'elevation'     : 2,
        'model'         : 5,
        'serial_number' : 6,
        'service_tag'   : 8,
        'uw'            : 9,
        'csl'           : 10,
        'morgridge'     : 11,
        'purpose'       : 12, # map 'purpose' to 'notes' for now
    }

    # converts an array of strings (row from the csv file) to a dictionary
    # TODO need a way to detect condos
    def __init__(self, csv_row):
        # each asset is represented with a nested dictionary
        self.asset = {
            'aquisition' : {
                'po'     : '',
                'date'   : '',
                'reason' : '',
            },

            'purpose' : '',

            'hardware' : {
                'model'         : '',
                'serial_number' : '',
                'service_tag'   : '',
            },

            # TODO revisit this probably
            'condo_chassis' : {
                'serial_number' : '',
                'service_tag'   : '',
                'model'         : '',
            },

            'location' : {
                'rack'      : '',
                'elevation' : '',
                'room'      : '',
                'building'  : '',
            }, 

            'tags' : {
                'csl'       : '',
                'uw'        : '',
                'morgridge' : '',
            },
        }

        # iterate through each inner and outer key and grab
        # its corresponding value (as determined by key_map) from the spreadsheet
        # TODO derive 'building' from 'room'
        # TODO this bit is in desperate need of a cleanup and fixup - but it's a start
        for outer_key, outer_value in self.asset.items():

            if isinstance(outer_value, dict):

                #if outer_value is a dictionary we need to iterate one level deeper
                for inner_key, inner_value in outer_value.items():
                    cell = self.key_map.get(inner_key, '')
                    if cell == '':
                        self.asset[outer_key][inner_key] = 'MISSING'
                    else:
                        self.asset[outer_key][inner_key] = csv_row[cell]

            else:
                # otherwise don't iterate any more!
                csv_val = self.key_map.get(outer_key, '')
                if cell == '':
                    self.asset[outer_key] = 'MISSING'
                else:
                    self.asset[outer_key] = csv_row[cell]

# for debugging
def print_dict(d):
    print('\n')
    for x in d:
        print(x, end='')

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
def csv2yaml(csv_name): 
    with open(csv_name, newline='') as csvfile:

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
    
# having a main function might be a good idea?
# if this module is ever imported somewhere for use of csv2yaml()
# but this script is also kind of a one off...
def main():
    # take csv filename as a command line arg
    if len(sys.argv) < 2:
        print("usage: csv2yaml.py <csv_file>")
        exit(1)

    csv_name = sys.argv[1]
    assets = csv2yaml(csv_name)

    for a in assets:
        print_dict(a.asset)

if __name__ == "__main__":
    main()
