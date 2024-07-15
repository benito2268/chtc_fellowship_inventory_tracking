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

        print(vals)

        data.append({"range" : range_str, "values" : vals})
        row += 1

    return data

def main():
    assets = read_yaml("../csv_2_yaml/")

    try:
        sheets_service = get_sheets_service()
        drive_service = get_drive_service()

        # write the data
        body = {"valueInputOption" : "USER_ENTERED", "data" : gen_data(assets)}
        write_request = (
            sheets_service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=get_id(), body=body)
        )

        result = write_request.execute()

        # change the name of the sheet to reflect update time
        date = datetime.now()
        title = f"CHTC Inventory {date.strftime('%Y-%m-%d %H:%M')}"


    except HttpError as err:
        print(err)

if __name__ == "__main__":
    main()
