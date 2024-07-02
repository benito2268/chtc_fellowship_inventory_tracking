import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# sheet is read-only for now
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# TODO: idea for the future - could parse sheet id from inputted URL
SHEET_ID = "1rKCtBd7QMCOEc3gdyKp5XzHVwlVmf-EFgtt7sFdBVgA"

# Range is specified in A1 notation
# Google sheets says the format is 'sheetname!cell1:cell2'
SAMPLE_RANGE = "Sheet1!A1:7"

def main():
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:

        # can refresh credentials if they are expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # TODO what is this part doing??
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

            with open('token.json', 'w') as token:
                token.write(creds.to_json())

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
