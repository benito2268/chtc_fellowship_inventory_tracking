#!/bin/python3

import os.path
import argparse
from api_helpers import get_sheets_service
from api_helpers import get_drive_service
from api_helpers import share_file
from datetime import datetime
from googleapiclient.errors import HttpError

import api_helpers
import format_vars

def main():
    # use argparse to get the email to share with
    parser = argparse.ArgumentParser()

    parser.add_argument("email_address", help="the email address that the script will share the sheet with", type=str, action="store")
    parser.add_argument("-k", "--keypath", help="the path the a json API key file. For use outside of the GitHub action", type=str, action="store")
    args = parser.parse_args()

    # try is used to catch HttpError during the API call
    try:
        if args.keypath:
            drive_service = get_drive_service(args.keypath)
            sheets_service = get_sheets_service(args.keypath)
        else:
            drive_service = get_drive_service()
            sheets_service = get_sheets_service()

        # create a spreadsheet
        date = datetime.now()
        title = f"CHTC Inventory {date.strftime('%Y-%m-%d %H:%M')}"
        sheet_data = {"properties" : {"title" : title}}
        sheet = sheets_service.spreadsheets().create(body=sheet_data)

        sheet_response = sheet.execute()

        requests = []

        # create the swapped sheet (tab)
        requests.append({
            "addSheet" : {
                "properties" : {
                    "title" : format_vars.SWAP_SHEET_NAME,
                }
            }
        })

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

        # make initial requests
        body = {"requests" : requests}

        response = (
            sheets_service.spreadsheets()
            .batchUpdate(spreadsheetId=sheet_response.get("spreadsheetId"), body=body)
            .execute()
        )

        # write the column headings - they will apprear in the order they are in the list
        # sheets API requires a 2D list - but in this case the outer list contains only the inner list
        headings = [
            [header for header in format_vars.PRETTY_COL_NAMES],
        ]

        # fqdn goes in column 1 - but is not in the YAML
        headings[0].insert(0, "Hostname")
        data = [ {"range" : f"{format_vars.MAIN_SHEET_NAME}!A1:{chr(ord('A') + format_vars.NUM_COLUMNS)}1", "values" : headings} ]

        data_body = {"valueInputOption" : "RAW", "data" : data}

        header_request = (
            sheets_service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=sheet_response.get('spreadsheetId'), body=data_body)
        )

        header_request.execute()

        # TODO this is not ideal - but do we have time to fix??
        data = [ {"range" : f"{format_vars.SWAP_SHEET_NAME}!A1:{chr(ord('A') + format_vars.NUM_COLUMNS)}1", "values" : headings} ]

        data_body = {"valueInputOption" : "RAW", "data" : data}

        swap_header_request = (
            sheets_service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=sheet_response.get('spreadsheetId'), body=data_body)
        )

        swap_header_request.execute()

        # requests to be done for both sheets
        ids = api_helpers.get_sheet_ids(sheets_service, sheet_response.get('spreadsheetId'))
        requests.clear()

        for sheet_id in ids:
            requests.extend([
                {
                    "addBanding" : {
                        "bandedRange" : {
                            "bandedRangeId" : sheet_id + 1, # + 1 since banded range id cannot be zero :(
                            "range" : {
                                "sheetId" : sheet_id,
                                "startRowIndex" : 1,
                            },

                            "rowProperties" : {
                                "firstBandColorStyle" : {
                                    "rgbColor" : {
                                        # light grey in RGBA
                                        "red" : 0.9,
                                        "green" : 0.9,
                                        "blue" : 0.9,
                                    },
                                },

                                "secondBandColorStyle" : {
                                    "rgbColor" : {
                                        # white in RGBA
                                        "red" : 1.0,
                                        "green" : 1.0,
                                        "blue" : 1.0,
                                    },
                                },
                            },
                        }
                    }
                },
                # make the sheet protected so it cannot be edited
                {
                    "addProtectedRange" : {
                        "protectedRange" : {
                            "range" : {
                                "sheetId" : sheet_id,
                            },
                            "warningOnly" : False,
                            "requestingUserCanEdit" : False,
                            "editors" : {
                                "users" : None,
                                "groups" : None,
                            }

                        }
                    }
                },

                 # center text
                {
                    "repeatCell" : {
                        "range" : {
                            "sheetId" : sheet_id,
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

                 # bold the header
                {
                    "repeatCell" : {
                        "range" : {
                            "startRowIndex" : 0,
                            "endRowIndex" : 1,
                            "startColumnIndex" : 0,
                            "sheetId" : sheet_id,
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
            ])

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
        with open(".spreadsheet_id", "w+") as outfile:
            outfile.write(sheet_response.get("spreadsheetId"))

        # share the service with the specified user
        share_file(sheet_response.get('spreadsheetId'), args.email_address, args.keypath)

    except HttpError as err:
        print(err)

if __name__ == "__main__":
    main()
