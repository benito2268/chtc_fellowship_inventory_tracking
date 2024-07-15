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

def get_id() -> str:
    with open("sheet_id.txt", "r") as id:
        return id.read().strip()

# a generator functions that creates a spreasheet row
# for each asset in the asset list
def gen_data(assets: list[Asset]) -> list[dict]:
    data = []
    row = 1

    for asset in assets:
        # create the range string
        range_str = f"Sheet1!A{row}:T{row}"
        flat = flatten_dict(asset.asset)

        vals = [
            [flat[key] for key in flat.keys()],
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

        title_request = (
            sheets_service.spreadsheets()
            .batchUpdate(spreadsheetId=get_id(), body=title_body)
        )

        title_request.execute()

        # write the data
        # "RAW" means google sheets treats the data exactly as is - no evaluating formulas or anything
        data_body = {"valueInputOption" : "RAW", "data" : gen_data(assets)}
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
