import os.path
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google APIs we expect to be able to access
# the API token will be the final judge, any scopes
# listed here that the token says we don't have access to are ignored
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# path to api token
SERVICE_ACCOUNT_FILE = "token-7-3-24.json"

def spreadsheet_auth():
    pass

def main():
    creds = None

    if os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        # try is used to catch HttpError during the API call
        try: 
            # startup required services
            drive_service = build("drive", "v3", credentials=creds)
            sheets_service = build("sheets", "v4", credentials=creds)
 
            # create a spreadsheet
            date = datetime.now()
            sheet_data = {"properties" : {"title" : f"CHTC Inventory {date.strftime('%Y-%m-%d %H:%M')}"}}
            sheet = sheets_service.spreadsheets().create(body=sheet_data)

            sheet_response = sheet.execute()
    
            # share the service with the specified user
            perm_data = {
                "type" : "user",
                "role" : "writer",
                "emailAddress" : "insert_email_here"
            }

            perm = drive_service.permissions().create(
                fileId=sheet_response.get("spreadsheetId"),
                body=perm_data
            )
            perm_response = perm.execute()

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
