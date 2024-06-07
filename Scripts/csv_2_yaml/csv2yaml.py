import sys
import csv

class Asset:

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

        self.asset['location']['room'] = csv_row[0]

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

        for row in reader:
            # print(', '.join(row))
            a = Asset(row)
            assets.append(a)

        for a in assets:
            print(a.asset['location']['room'])

    
# having a main function might be a good idea?
# if this module is ever imported somewhere for use of csv2yaml()
# but this script is also kind of a one off...
def main():
    # take csv filename as a command line arg
    if len(sys.argv) < 2:
        print("usage: csv2yaml.py <csv_file>")
        exit(1)

    csv_name = sys.argv[1]
    csv2yaml(csv_name)

if __name__ == "__main__":
    main()
