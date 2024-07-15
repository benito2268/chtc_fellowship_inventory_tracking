import os
import sys
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
    "hardware.purpose",
    "hardware.condo_chassis.model",
    "hardware.condo_chassis.identifier",
    "tags.uw",
    "tags.csl",
    "tags.morgridge",
    "hardware.notes",
]

def get_id() -> str:
    with open("sheet_id.txt", "r") as id:
        return id.read().strip()

# a generator functions that creates a spreasheet row
# for each asset in the asset list
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

def main():
    assets = read_yaml("../csv_2_yaml/")

    try:
        sheets_service = get_sheets_service()
        drive_service = get_drive_service()


        # update the title to reflect the time the sheet was updated
        date = datetime.now()
        title = f"CHTC Inventory {date.strftime('%Y-%m-%d %H:%M')}"
        title_body = {
            "requests" : {
                "updateSpreadsheetProperties" : {
                    "properties" : {"title" : title},
                    "fields" : "title",
                }
            }
        }

        # as far as I can tell - the spreadsheet itself only has batchUpdate() and not update()?
        title_request = (
            sheets_service.spreadsheets()
            .batchUpdate(spreadsheetId=get_id(), body=title_body)
        )

        title_request.execute()

        # write the column headings - they will apprear in the order they are in the list
        # sheets API requires a 2D list - but in this case the outer list contains only the inner list
        headings = [
            [header for header in COLUMN_MAP],
        ]

        data = gen_data(assets)
        data.insert(0, {"range" : "Sheet1!A1:T1", "values" : headings})

        # write the data
        # "RAW" means google sheets treats the data exactly as is - no evaluating formulas or anything
        data_body = {"valueInputOption" : "RAW", "data" : data}
        write_request = (
            sheets_service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=get_id(), body=data_body)
        )

        result = write_request.execute()

    except HttpError as err:
        print(err)

if __name__ == "__main__":
    main()
