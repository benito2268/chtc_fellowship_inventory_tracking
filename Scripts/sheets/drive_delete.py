# a helper script to interactivly delete files from the service account's Drive
# just a temporary thing for testing :)
import os
import sys

from api_helpers import get_drive_service
from googleapiclient.errors import HttpError

# will ask for files to delete until you type 'q'
def main():
    try:
        drive_service = get_drive_service()

        files = drive_service.files().list().execute()
        for filestr in files.get('files'):
            print(filestr)

        cmd = ""
        while(True):
            cmd = input("paste a file ID to delete it or type 'q' to quit: ")
            
            if cmd == 'q': break

            drive_service.files().delete(fileId=cmd.replace('\n', '')).execute()
            
    except HttpError as err:
        print(err)

if __name__ == "__main__":
    main()
