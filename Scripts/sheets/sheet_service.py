# a shared module for making starting up a Google Drive and Sheets service
# this module is intended to be used in other scripts - not nessesarily on its own

import os.path
 
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google APIs we expect to be able to access
# the API token will be the final judge, any scopes
# listed here that the token says we don't have access to are ignored
#
# NOTE: new additions must be enabled in Google Cloud Platform under "Enabled APIs and Services"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# path to api token
SERVICE_ACCOUNT_FILE = "token-7-3-24.json"

def get_creds():
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        return Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    else:
        print(f'ERROR: path not found: {SERVICE_ACCOUT_FILE}')
        exit(1)    

# returns a Google API Resource object with methods to call into
# the sheets API
def get_sheets_service():
    pass

def get_drive_service():
    pass
