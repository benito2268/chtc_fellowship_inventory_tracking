import os.path
import argparse
from api_helpers import get_sheets_service
from api_helpers import get_drive_service
from api_helpers import share_file
from datetime import datetime
from googleapiclient.errors import HttpError

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
    
        # share the service with the specified user
        share_file(sheet_response.get('spreadsheetId'), args.email_address) 

        # print the spreadsheet URL
        print(f"A spreadsheet \"{title}\" was created and shared: ")
        print(sheet_response.get("spreadsheetUrl"))
        print()

    except HttpError as err:
        print(err) 

if __name__ == "__main__":
    main()
