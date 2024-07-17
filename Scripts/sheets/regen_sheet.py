import os
import sys
import math
from datetime import datetime
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from api_helpers import get_drive_service
from api_helpers import get_sheets_service

sys.path.append(os.path.abspath('../shared/'))
from yaml_io import read_yaml
from yaml_io import Asset
from dict_utils import flatten_dict

# a list the specifies the order 
# this also filters what appears in the spreadsheeti
# anything that doesn't appear here also won't in the sheet
COLUMN_MAP = [
    "location.building",
    "location.room",
    "location.rack",
    "location.elevation",
    "hardware.model",
    "hardware.serial_number",
    "hardware.service_tag",
    "hardware.condo_chassis.model",
    "hardware.condo_chassis.identifier",
    "tags.uw",
    "tags.csl",
    "tags.morgridge",
    "hardware.notes",
    "hardware.purpose",
]

PRETTY_COL_NAMES = [
    "Building",
    "Room",
    "Rack",
    "Elevation",
    "Model",
    "Serial Number",
    "Service Tag",
    "Condo Model",
    "Condo Serial",
    "UW Tag",
    "CSL Tag",
    "Morgridge Tag",
    "Notes",
    "Purpose",
]

# + 1 because we need a column for the hostname
NUM_COLUMNS = len(COLUMN_MAP) + 1

# TODO is there a better way to store these?
# otherwise they have to be changed if the spreadsheet
# is recreated
SPREADSHEET_ID = "1FUFVVVgNXOj14wYMsNTwmU15kzQTduUfFefo_o5iWGE"
MAIN_SHEET_ID = 0

# reads asset data from the sheet to compare against what is in the
# canonical data - will be used for finding the 'diff' of the sheet and the YAML
# note: does NOT read the first (header row)
#
# params: sheet_srv - an initialized Google Sheets API service
#
# returns a list of rows (list[str]) read from the sheet
def read_spreadsheet(sheet_srv: Resource) -> list[list[str]]:
    # want to specifiy the entire sheet
    result = (
        sheet_srv.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range="Sheet1")
        .execute()
    )

    ret = result.get("values", [])
    
    #remove the first (header) row
    del ret[0]

    return ret

def do_deletions(sheet_srv: Resource, assets: list[Asset]):
    rows = read_spreadsheet(sheet_srv)

    # the + 1 is because spreasheets start indexing at 1
    sheet_hostnames = {rows[i][0] : i + 1 for i in range(len(rows))}
    yaml_hostnames = {asset.fqdn for asset in assets}
    
    # pick out elements in sheet_data but not in file_data
    delete_hosts = set(sheet_hostnames.keys()) - yaml_hostnames
    api_requests = []

    if len(delete_hosts) == 0:
        return

    for hn in delete_hosts:
        api_requests.append (
            {
                "deleteDimension" : {
                    "range" : {
                        "sheetId" : MAIN_SHEET_ID,
                        "dimension" : "ROWS",
                        "startIndex" : sheet_hostnames[hn],
                        "endIndex" : sheet_hostnames[hn] + 1,
                    }
                }
            }
        )

    # make the api request
    body = {"requests" : api_requests}
    response = (
        sheet_srv.spreadsheets().
        batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
        .execute()
    )


def do_additions(rows: list[list[str]], yaml_data: list[list[str]]):
    pass

def do_changes(rows: list[list[str]], yaml_data: list[list[str]]):
    pass

# a function that updates the spreadsheet by comparing
# to the parsed YAML. Handles additions, deletions, and modifications
#
# params:
#    assets - the list of assets read in from files
#
# returns: a list of dicts containing row data for the spreadsheet
def diff_data(assets: list[Asset]) -> list[dict]:
    # row 1 contains the column headings
    data = []
    row = 2

    for asset in assets:
        # create the range string
        range_str = f"Sheet1!A{row}:{chr(ord('A') + NUM_COLUMNS)}{row}"
        flat = flatten_dict(asset.asset)

        vals = [
            [flat[key] for key in COLUMN_MAP],
        ]
    
        # prepend the hostname
        vals[0].insert(0, asset.fqdn)

        data.append({"range" : range_str, "values" : vals})
        row += 1

    return data

# write asset data to the body of the spreadsheet
def write_data(sheets_srv: Resource, assets: list):
    # write the column headings - they will apprear in the order they are in the list
    # sheets API requires a 2D list - but in this case the outer list contains only the inner list
    headings = [
        [header for header in PRETTY_COL_NAMES],
    ]

    # fqdn goes in column 1 - but is not in the YAML
    headings[0].insert(0, "Hostname")

    data = diff_data(assets)
    data.insert(0, {"range" : f"Sheet1!A1:{chr(ord('A') + NUM_COLUMNS)}1", "values" : headings})

    # write the data
    # "RAW" means google sheets treats the data exactly as is - no evaluating formulas or anything
    # TODO could/should this be replaced with UpdateCellsRequest??
    # ^^ that way I might be able to put everything into one batch request
    data_body = {"valueInputOption" : "RAW", "data" : data}
    write_request = (
        sheets_srv.spreadsheets()
        .values()
        .batchUpdate(spreadsheetId=SPREADSHEET_ID, body=data_body)
    )

    result = write_request.execute()


def main():
    # read asset data from each YAML file in given dir
    assets = read_yaml("../csv_2_yaml/yaml/")

    try:
        sheets_service = get_sheets_service()
        drive_service = get_drive_service()

        do_deletions(sheets_service, assets)

        # sheet only has 1000 rows by default
        # we'll round up to the nearest thousand
        # also calculate the number of colunms we need
        nearest_k_rows = math.ceil(len(assets) / 1000) * 1000

        # update the title to reflect the time the sheet was updated
        # and also make sure there are enough rows for our data
        date = datetime.now()
        title = f"CHTC Inventory - Updated {date.strftime('%Y-%m-%d %H:%M')}"
        requests = [
            # set the spreadsheet title
            {
                "updateSpreadsheetProperties" : {
                    "properties" : {"title" : title},
                    "fields" : "title",
                }
            },

            # round the number of rows to the nearest 1000
            # should we check this first??
            {
                "updateSheetProperties" : {
                    "properties" : {
                        "sheetId" : MAIN_SHEET_ID,
                        "gridProperties" : {
                            "rowCount" : nearest_k_rows,
                            "frozenRowCount" : 1,
                            "columnCount" : NUM_COLUMNS,
                        },
                    },

                    "fields" : "gridProperties",
                }
            },

            # auto size each row to fit the longest line of text
            {
                "autoResizeDimensions" : {
                    "dimensions" : {
                        "sheetId" : MAIN_SHEET_ID,
                        "dimension" : "COLUMNS",
                        "startIndex" : 0,
                        "endIndex" : NUM_COLUMNS,
                    }
                },
            },

            # bold the header
            {
                "repeatCell" : {
                    "range" : {
                        "startRowIndex" : 0,
                        "endRowIndex" : 1,
                        "startColumnIndex" : 0,
                        "sheetId" : MAIN_SHEET_ID,
                    },

                    "cell" : {
                        "userEnteredFormat" : {
                            "horizontalAlignment" : "CENTER",
                            "textFormat" : {
                                "bold" : True
                            }
                        }
                    },

                    "fields" : "userEnteredFormat"
                },
            },
        ]

        # as far as I can tell - the spreadsheet itself only has batchUpdate() and not update()?
        body = {"requests" : requests}
        setup_request = (
            sheets_service.spreadsheets()
            .batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
        )

        setup_request.execute()

        # write the sheet data 
        write_data(sheets_service, assets)

    except HttpError as err:
        print(err)

if __name__ == "__main__":
    main()
