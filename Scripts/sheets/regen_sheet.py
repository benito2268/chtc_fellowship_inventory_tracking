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

# TODO is there a better way to store these?
# otherwise they have to be changed if the spreadsheet
# is recreated
SPREADSHEET_ID = "18f5BtIll56LJlMf0drmebz5ooyEmGPwAtGteKWEvX90"
MAIN_SHEET_ID = 0

# a generator functions that creates a spreasheet row
# for each asset in the asset list
#
# params:
#    assets - the list of assets read in from files
#
# returns: a list of dicts containing row data for the spreadsheet
def gen_data(assets: list[Asset]) -> list[dict]:
    # row 1 contains the column headings
    data = []
    row = 2

    for asset in assets:
        # create the range string
        range_str = f"Sheet1!A{row}:T{row}"
        flat = flatten_dict(asset.asset)

        vals = [
            [flat[key] for key in COLUMN_MAP],
        ]

        data.append({"range" : range_str, "values" : vals})
        row += 1

    return data

def write_data(sheets_srv: Resource):
    # write the column headings - they will apprear in the order they are in the list
    # sheets API requires a 2D list - but in this case the outer list contains only the inner list
    headings = [
        [header for header in COLUMN_MAP],
    ]

    data = gen_data(assets)
    data.insert(0, {"range" : f"Sheet1!A1:{ord('A') + len(COLUMN_MAP)}1", "values" : headings})

    # write the data
    # "RAW" means google sheets treats the data exactly as is - no evaluating formulas or anything
    # TODO could/should this be replaced with UpdateCellsRequest??
    # ^^ that way I might be able to put everything into one batch request
    data_body = {"valueInputOption" : "RAW", "data" : data}
    write_request = (
        sheets_service.spreadsheets()
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

        # write the sheet data first
        write_data(sheets_service)

        # sheet only has 1000 rows by default
        # we'll round up to the nearest thousand
        # also calculate the number of colunms we need
        nearest_k_rows = math.ceil(len(assets) / 1000) * 1000

        # update the title to reflect the time the sheet was updated
        # and also make sure there are enough rows for our data
        date = datetime.now()
        title = f"CHTC Inventory - Updated {date.strftime('%Y-%m-%d %H:%M')}"
        requests = [
            {
                "updateSpreadsheetProperties" : {
                    "properties" : {"title" : title},
                    "fields" : "title",
                }
            },

            {
                "updateSheetProperties" : {
                    "properties" : {
                        "sheetId" : MAIN_SHEET_ID,
                        "gridProperties" : {
                            "rowCount" : nearest_k_rows,
                            "frozenRowCount" : 1,
                            "columnCount" : len(COLUMN_MAP),
                        },
                    },

                    "fields" : "gridProperties",
                }
            },

            {
                "autoResizeDimensions" : {
                    "dimensions" : {
                        "sheetId" : MAIN_SHEET_ID,
                        "dimension" : "COLUMNS",
                        "startIndex" : 0,
                        "endIndex" : len(COLUMN_MAP),
                    }
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

    except HttpError as err:
        print(err)

if __name__ == "__main__":
    main()
