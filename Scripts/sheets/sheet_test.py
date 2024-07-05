import os.path
from api_helpers import get_sheets_service
from api_helpers import get_drive_service
from api_helpers import share_file
from datetime import datetime
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

def main():
    # try is used to catch HttpError during the API call
    try:   
        drive_service = get_drive_service()
        sheets_service = get_sheets_service()

        # create a spreadsheet
        date = datetime.now()
        sheet_data = {"properties" : {"title" : f"CHTC Inventory {date.strftime('%Y-%m-%d %H:%M')}"}}
        sheet = sheets_service.spreadsheets().create(body=sheet_data)

        sheet_response = sheet.execute()
    
        # share the service with the specified user
        share_file(sheet_response.get('spreadsheetId'), 'benstaehle@gmail.com', True) 

        # print the spreadsheet URL
        print(sheet_response.get("spreadsheetUrl"))

        #TODO remove
        drive = drive_service.files().list()
        drive_response = drive.execute()

        for filestr in drive_response.get('files'):
            print(filestr)

    except HttpError as err:
        print(err) 

if __name__ == "__main__":
    main()
