import os
import sys
import math
import copy
from datetime import datetime
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from api_helpers import get_drive_service
from api_helpers import get_sheets_service

sys.path.append(os.path.abspath("../shared/"))
sys.path.append(os.path.abspath("scripts/shared"))

import format_vars
from yaml_io import read_yaml
from yaml_io import Asset
from dict_utils import flatten_dict

SPREADSHEET_ID = ""
MAIN_SHEET_ID = 0

# the key the spreadsheet will be sorted
# (alphanumerically) by
SORT_BY = "location.room"

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
        .get(spreadsheetId=SPREADSHEET_ID, range=format_vars.MAIN_SHEET_NAME)
        .execute()
    )

    ret = result.get("values", [])

    #remove the first (header) row
    if ret:
        del ret[0]

    return ret

# returns new_row's sorted index within rows - does not actually insert
def find_sorted_position(rows: list[list[str]], new_row: list[str]) -> int:
    key_index = format_vars.COLUMN_MAP.index(SORT_BY) + 1
    index = 0

    while index < len(rows) and new_row[key_index] > rows[index][key_index]:
        index += 1

    return index

# finds the index of a new spreadsheet element
# in a sorted spreadsheet and inserts a new row at the proper place
def insert_batch_sorted(sheet_srv: Resource, rows: list[list[str]], new_rows: list[list[str]]):
    rows_cpy = copy.deepcopy(rows)
    requests = []

    for new_row in new_rows:
        row = new_row[0]
        index = find_sorted_position(rows_cpy, row)

        # insert a new row at index + 2 (+1 for 1-indexing, +1 to account for the header)
        inherit = True if index != 0 else False

        requests.append(
            {
                "insertDimension" : {
                    "range" : {
                        "sheetId" : MAIN_SHEET_ID,
                        "dimension" : "ROWS",
                        "startIndex" : index + 1,
                        "endIndex" : index + 2,
                    },

                    "inheritFromBefore" : inherit,
                }
            },
        )

        requests.append(
            {
                "pasteData" : {
                    "coordinate" : {
                        "sheetId" : MAIN_SHEET_ID,
                        "rowIndex" : index + 1,
                    },

                    "data" : f"{',,,'.join(row)}\n",
                    "type" : "PASTE_NORMAL",
                    "delimiter" : ",,,",
                }
            },
        )

        rows_cpy.insert(index, row)

    body = {"requests" : requests}
    request = (
        sheet_srv.spreadsheets()
        .batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
    )
    request.execute()

# handles deleting rows whose underlying YAML no longer exists
#
# params:
#   sheet_srv - a Google Sheets API service
#   assets - a list of Asset objects read from underlaying YAML
def do_deletions(sheet_srv: Resource, assets: list[Asset]):
    rows = read_spreadsheet(sheet_srv)

    # rows should be sorted in reverse order so when batch deletions happen
    # the row number shifts won't mess things up
    sheet_hostnames = [(rows[i][0], i) for i in reversed(range(len(rows)))]
    yaml_hostnames = [asset.fqdn for asset in assets]

    # pick out elements in sheet_data but not in file_data
    # sadly, these need to be ordered so can't use my beloved python sets :(
    delete_assets = []
    for row in sheet_hostnames:
        if row[0] not in yaml_hostnames:
            delete_assets.append(row)

    api_requests = []

    # if no deletions - don't bother calling the API
    if not delete_assets:
        return

    for pair in delete_assets:
        api_requests.append (
            {
                "deleteDimension" : {
                    "range" : {
                        "sheetId" : MAIN_SHEET_ID,
                        "dimension" : "ROWS",
                        "startIndex" : pair[1] + 1,
                        "endIndex" : pair[1] + 2,
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

    # the + 1 is because spreasheets start indexing at 1
    sheet_hostnames = {row[0] for row in rows}
    yaml_hostnames = {assets[i].fqdn : i for i in range(len(assets))}

    # seperate assets that are in the YAML but not the sheet
    new_hostnames = set(yaml_hostnames.keys()) - sheet_hostnames

    # if no additions - don't bother calling the API
    if not new_hostnames:
        return

    # generate rows for the new assets
    # for now append to the list
    new_assets = []

    for hostname in new_hostnames:
        asset = assets[yaml_hostnames[hostname]]
        flat = flatten_dict(asset.asset)
        vals = [
            [flat[key] for key in format_vars.COLUMN_MAP],
        ]

        # prepend the hostname
        vals[0].insert(0, asset.fqdn)

        new_assets.append(vals)

    insert_batch_sorted(sheet_srv, rows, new_assets)

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

    move_reqs = []
    new_data = []

    # update the sheet with per-cell granularity
    for row in rows:
        for i in range(1, len(row)):
            # something changed in this file - update the sheet
            # note: if a hostname changes the script will process it as
            # a deletion and addition, not a change
            # -- TODO: is this okay?
            if row[i] != yaml_data[row[0]][i - 1]:
                # track down what cell the change will occur in
                # + 1 to account for the hostname
                if i == format_vars.COLUMN_MAP.index(SORT_BY) + 1:
                    # if we modify the field on which the sorted is based
                    # we may need to move the row
                    yaml_row = copy.deepcopy(yaml_data[row[0]])
                    yaml_row.insert(0, row[0])
                    new_index = find_sorted_position(rows, yaml_row)

                    print(row_nums[row[0]])
                    print(new_index)

                    # create a new MoveDimensionRequest
                    move_reqs.append({
                        "moveDimension" : {
                            "source" : {
                                "sheetId" : MAIN_SHEET_ID,
                                "dimension" : "ROWS",
                                "startIndex" : row_nums[row[0]] - 1, # rows are 0-indexed in API call, and 1-indexed in range strings
                                "endIndex" : row_nums[row[0]],
                            },

                            "destinationIndex" : new_index + 1,
                        }
                    })

                range_str = f"{format_vars.MAIN_SHEET_NAME}!{chr(ord('A') + i)}{row_nums[row[0]]}"

                # google sheets needs it in a 2D list
                to_append = [ [yaml_data[row[0]][i - 1] ] ]
                new_data.append({"range" : range_str, "values" : to_append})

    # make the input API request
    body = {"valueInputOption" : "RAW", "data" : new_data}

    request = (
        sheet_srv.spreadsheets()
        .values()
        .batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
    )

    request.execute()

    # make the move API request
    if move_reqs:
        print('got here')
        body = {"requests" : move_reqs}
        move_req = (
            sheet_srv.spreadsheets()
            .batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
        )

        move_req.execute()

def main():
    # read asset data from each YAML file in given dir
    assets = read_yaml("../csv_2_yaml/yaml/")

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

            # update sheet banding
            {
                "updateBanding" : {
                    "bandedRange" : {
                        "bandedRangeId" : 222,
                        "range" : {
                            "sheetId" : 0,
                            "startRowIndex" : 1,
                        },

                        "rowProperties" : {
                            "firstBandColorStyle" : {
                                "rgbColor" : {
                                    # light grey in RGBA
                                    "red" : 0.9,
                                    "green" : 0.9,
                                    "blue" : 0.9,
                                    "alpha" : 1.0,
                                },
                            },

                            "secondBandColorStyle" : {
                                "rgbColor" : {
                                    # white in RGBA
                                    "red" : 1.0,
                                    "green" : 1.0,
                                    "blue" : 1.0,
                                    "alpha" : 1.0,
                                },
                            },
                        },
                    },

                    "fields" : "*",
                }
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
