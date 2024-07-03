import os.path

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# sheet is read-only for now
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# TODO: idea for the future - could parse sheet id from inputted URL
SHEET_ID = "1rKCtBd7QMCOEc3gdyKp5XzHVwlVmf-EFgtt7sFdBVgA"

# Range is specified in A1 notation
# the format is 'sheetname!cell1:cell2'
# where 'sheet' refers to a tab within a larger spreasheet
SAMPLE_RANGE = "Sheet1!A1:7"

# TODO probably not the best idea to have this - what to do with it
SERVICE_ACCOUNT_FILE = 'token-7-3-24.json'

def main():
    creds = None

    if os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        # try is used to catch HttpError during the API call
        try:
            service = build('sheets', 'v4', credentials=creds)
 
            # call the sheets API to get some data
            sheet = service.spreadsheets()
            result = (
                sheet.values().get(spreadsheetId=SHEET_ID, range=SAMPLE_RANGE).execute()
            )

            values = result.get('values', [])
            if not values:
                print('no data in spreadsheet range')
                exit(1)

            # print the fetched values
            for value in values:
                print(value)

        except HttpError as err:
            print(err) 

if __name__ == "__main__":
    main()
