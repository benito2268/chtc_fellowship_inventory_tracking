import os.path
import argparse
from api_helpers import get_sheets_service
from api_helpers import get_drive_service
from api_helpers import share_file
from datetime import datetime
from googleapiclient.errors import HttpError

import format_vars

def main():
    # use argparse to get the email to share with
    parser = argparse.ArgumentParser()

    parser.add_argument("email_address", help="the email address that the script will share the sheet with", type=str)
    args = parser.parse_args()

    # try is used to catch HttpError during the API call
    try:
        drive_service = get_drive_service()
        sheets_service = get_sheets_service()

        # create a spreadsheet
        date = datetime.now()
        title = f"CHTC Inventory {date.strftime('%Y-%m-%d %H:%M')}"
        sheet_data = {"properties" : {"title" : title}}
        sheet = sheets_service.spreadsheets().create(body=sheet_data)

        sheet_response = sheet.execute()

        requests = []

        # write the column headings - they will apprear in the order they are in the list
        # sheets API requires a 2D list - but in this case the outer list contains only the inner list
        headings = [
            [header for header in format_vars.PRETTY_COL_NAMES],
        ]

        # fqdn goes in column 1 - but is not in the YAML
        headings[0].insert(0, "Hostname")
        data = [ {"range" : f"Sheet1!A1:{chr(ord('A') + format_vars.NUM_COLUMNS)}1", "values" : headings} ]

        data_body = {"valueInputOption" : "RAW", "data" : data}

        title_request = (
            sheets_service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=sheet_response.get('spreadsheetId'), body=data_body)
        )

        title_request.execute()

        # make the sheet protected so it cannot be edited
        requests.append({
            "addProtectedRange" : {
                "protectedRange" : {
                    "range" : {
                        "sheetId" : 0,
                    },
                    "warningOnly" : False,
                    "requestingUserCanEdit" : False,
                    "editors" : {
                        "users" : None,
                        "groups" : None,
                    }

                }
            }
        })

        requests.append(
             # center text
            {
                "repeatCell" : {
                    "range" : {
                        "startRowIndex" : 0,
                        "startColumnIndex" : 0,
                    },

                    "cell" : {
                        "userEnteredFormat" : {
                            "horizontalAlignment" : "CENTER",
                        }
                    },

                    "fields" : "userEnteredFormat"
                },
            },
        )

        requests.append(
             # bold the header
            {
                "repeatCell" : {
                    "range" : {
                        "startRowIndex" : 0,
                        "endRowIndex" : 1,
                        "startColumnIndex" : 0,
                        "sheetId" : 0,
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
        )

        # rename the main sheet from 'Sheet1'
        requests.append(
            {
                "updateSheetProperties" : {
                    "properties" : {
                        "sheetId" : 0,
                        "title" : format_vars.MAIN_SHEET_NAME,
                    },

                    "fields" : "title",
                }
            }
        )

        requests.append(
            {
                "addConditionalFormatRule" : {
                    "rule" : {
                        "ranges" : [{
                            "sheetId" : 0,
                            "startRowIndex" : 0,
                            "startColumnIndex" : 0,
                        }],
                        "booleanRule" : {
                            "condition" : {
                                "type" : "CUSTOM_FORMULA",
                                "values" : [{
                                    "userEnteredValue" : "=ISODD(ROW())"
                                }],
                            },

                            "format" : {
                                "backgroundColor" : {
                                    "red" : 0.9,
                                    "green" : 0.9,
                                    "blue" : 0.9,
                                    "alpha" : 1,
                                }
                            },
                        },
                    },
                    "index" : 0,
                }
            }
        )

        body = {"requests" : requests}

        response = (
            sheets_service.spreadsheets()
            .batchUpdate(spreadsheetId=sheet_response.get("spreadsheetId"), body=body)
            .execute()
        )

        # print the spreadsheet URL
        print(f"A spreadsheet \"{title}\" was created and shared: ")
        print(sheet_response.get("spreadsheetUrl"))
        print()

        # write the spreadsheet id to a file
        with open("spreadsheet_id.txt", "w+") as outfile:
            outfile.write(sheet_response.get("spreadsheetId"))

        # share the service with the specified user
        share_file(sheet_response.get('spreadsheetId'), args.email_address)

    except HttpError as err:
        print(err)

if __name__ == "__main__":
    main()
