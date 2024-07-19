import os
import sys
import math
import copy
from datetime import datetime
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from api_helpers import get_drive_service
from api_helpers import get_sheets_service

sys.path.append(os.path.abspath('../shared/'))
import format_vars
from yaml_io import read_yaml
from yaml_io import Asset
from dict_utils import flatten_dict


# TODO is there a better way to store these?
# otherwise they have to be changed if the spreadsheet
# is recreated
SPREADSHEET_ID = ""
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
    if ret:
        del ret[0]

    return ret

# finds the index of a new spreadsheet element
# in a sorted spreadsheet and inserts a new row at the proper place
def find_sorted_pos(sheet_srv: Resource, rows: list[list[str]], new_row: list[str]) -> int:
    # the key to sort by
    key = "location.room"
    key_index = format_vars.COLUMN_MAP.index(key)

    index = 0
    while index < len(rows) and new_row[key_index] > rows[index][key_index]:
        index += 1

    # insert a new row at index + 2 (+1 for 1-indexing, +1 to account for the header)
    requests = [
        {
            "insertDimension" : {
                "range" : {
                    "sheetId" : MAIN_SHEET_ID,
                    "dimension" : "ROWS",
                    "startIndex" : index + 1,
                    "endIndex" : index + 2,
                }
            }
        },

        {
            "pasteData" : {
                "coordinate" : {
                    "sheetId" : MAIN_SHEET_ID,
                    "rowIndex" : index + 1,
                },
                "data" : f"{',,,'.join(new_row)}\n",
                "type" : "PASTE_NORMAL",
                "delimiter" : ",,,",
            }
        },
    ]

    body = {"requests" : requests}
    request = (
        sheet_srv.spreadsheets()
        .batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
    )
    request.execute()

    rows.insert(index, new_row)
    return index + 1

# handles deleting rows whose underlying YAML no longer exists
#
# params:
#   sheet_srv - a Google Sheets API service
#   assets - a list of Asset objects read from underlaying YAML
def do_deletions(sheet_srv: Resource, assets: list[Asset]):
    rows = read_spreadsheet(sheet_srv)

    sheet_hostnames = {rows[i][0] : i for i in range(len(rows))}
    yaml_hostnames = {asset.fqdn for asset in assets}

    # pick out elements in sheet_data but not in file_data
    delete_assets = set(sheet_hostnames.keys()) - yaml_hostnames
    api_requests = []

    # if no deletions - don't bother calling the API
    if not delete_assets:
        return

    for hn in delete_assets:
        api_requests.append (
            {
                "deleteDimension" : {
                    "range" : {
                        "sheetId" : MAIN_SHEET_ID,
                        "dimension" : "ROWS",
                        "startIndex" : sheet_hostnames[hn] + 1, # semi-frustratingly spreadsheets are '1-indexed'
                        "endIndex" : sheet_hostnames[hn] + 2,
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

# handles adding spreadsheet rows for new underlying
# YAML files
#
# params:
#   sheet_srv - a Google Sheets API service
#   assets - a list of asset objects read from underlying YAML
def do_additions(sheet_srv: Resource, assets: list[Asset]):
    rows = read_spreadsheet(sheet_srv)
    rows_cpy = copy.deepcopy(rows)

    # the + 1 is because spreasheets start indexing at 1
    sheet_hostnames = {row[0] for row in rows}
    yaml_hostnames = {assets[i].fqdn : i for i in range(len(assets))}

    # seperate assets that are in the YAML but not the sheet
    new_assets = set(yaml_hostnames.keys()) - sheet_hostnames

    # if no additions - don't bother calling the API
    if not new_assets:
        return

    # generate rows for the new assets
    # for now append to the list
    data = []

    for hostname in new_assets:
        asset = assets[yaml_hostnames[hostname]]
        flat = flatten_dict(asset.asset)
        vals = [
            [flat[key] for key in format_vars.COLUMN_MAP],
        ]

        # prepend the hostname
        vals[0].insert(0, asset.fqdn)

        # create the range string
        row = find_sorted_pos(sheet_srv, rows_cpy, vals[0])

    # sort the sheet alphabetically
    #requests = [
    #    {
    #        "sortRange" : {
    #            "range" : {"startRowIndex" : 2},
    #            "sortSpecs" : {
    #                "sortOrder" : "ASCENDING",
    #                "dimensionIndex" : 2,
    #            }
    #        },
    #    },
    #]

    #body = {"requests" : requests}
    #request =  (
    #    sheet_srv.spreadsheets()
    #    .batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
    #)

    #request.execute()

# handles updating (only) spreadsheet rows whose underlying YAML has changed
#
# params:
#   sheet_srv - a Google Sheets API service
#   assets - a list of Asset objects read from underlying YAML
def do_changes(sheet_srv: Resource, assets: list[Asset]):
    rows = read_spreadsheet(sheet_srv)

    # the nested comprehension is a bit gross - maybe I should find a cleaner way
    yaml_data = {asset.fqdn : [flatten_dict(asset.asset)[key] for key in format_vars.COLUMN_MAP] for asset in assets}
    row_nums = {rows[i][0] : i + 2 for i in range(len(rows))}
    new_data = []

    # update the sheet with per-cell granularity
    for row in rows:
        for i in range(1, len(row)):
            # something changed in this file - update the sheet
            # note: if a hostname changes the script will process it as
            # a deletion and addition, not a change
            if not row[i] == yaml_data[row[0]][i - 1]:
                # track down what cell the change will occur in
                range_str = f"Sheet1!{chr(ord('A') + i)}{row_nums[row[0]]}"

                # google sheets needs it in a 2D list
                to_append = [ [yaml_data[row[0]][i - 1] ] ]
                new_data.append({"range" : range_str, "values" : to_append})

    # make the API request
    body = {"valueInputOption" : "RAW", "data" : new_data}

    request = (
        sheet_srv.spreadsheets()
        .values()
        .batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
    )

    request.execute()

def main():
    # read asset data from each YAML file in given dir
    assets = read_yaml("../csv_2_yaml/yaml_test/")

    # read the new spreadsheet id
    global SPREADSHEET_ID
    with open("spreadsheet_id.txt", "r") as infile:
        SPREADSHEET_ID = infile.read()

    try:
        sheets_service = get_sheets_service()
        drive_service = get_drive_service()

        # sheet only has 1000 rows by default
        # we'll round up to the nearest thousand
        # also calculate the number of colunms we need
        nearest_k_rows = math.ceil(len(assets) / 1000) * 1000

        # update the title to reflect the time the sheet was updated
        # and also make sure there are enough rows for our data
        date = datetime.now()
        title = f"CHTC Inventory - Updated {date.strftime('%Y-%m-%d %H:%M')}"
        pre_format_requests = [
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
                            "columnCount" : format_vars.NUM_COLUMNS,
                        },
                    },

                    "fields" : "gridProperties",
                }
            },
        ]

        # as far as I can tell - the spreadsheet itself only has batchUpdate() and not update()?
        body = {"requests" : pre_format_requests}
        pre_format_request = (
            sheets_service.spreadsheets()
            .batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
        )

        pre_format_request.execute()

        # do the actual updating
        do_deletions(sheets_service, assets)
        do_additions(sheets_service, assets)
        do_changes(sheets_service, assets)

        # post format requests get called after the data is written
        # for example, changing the cell size to fit the data
        post_format_requests = [
            # auto size each row to fit the longest line of text
            {
                "autoResizeDimensions" : {
                    "dimensions" : {
                        "sheetId" : MAIN_SHEET_ID,
                        "dimension" : "COLUMNS",
                        "startIndex" : 0,
                        "endIndex" : format_vars.NUM_COLUMNS,
                    }
                },
            },
        ]

        body = {"requests" : post_format_requests}
        post_format_request = (
            sheets_service.spreadsheets()
            .batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
        )

        post_format_request.execute()

    except HttpError as err:
        print(err)

if __name__ == "__main__":
    main()
