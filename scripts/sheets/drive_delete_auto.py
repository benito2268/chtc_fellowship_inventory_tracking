# a helper script to interactivly delete files from the service account's Drive
# just a temporary thing for testing :)
#
# NOTE: depending on what we do - it might be useful to add a feature
# for recovering files and emptying the trash
import os
import sys

from pprint import pprint 
from googleapiclient.discovery import Resource
from api_helpers import get_drive_service
from googleapiclient.errors import HttpError

# will ask for files to delete until you type 'q'
def main():
    try:
        drive_service = get_drive_service()

        with open("spreadsheet_id.txt", "r") as infile:
            i = infile.read()
            drive_service.files().delete(fileId=i).execute()

            # danger zone
            # drive_service.files().emptyTrash().execute()
 
    except HttpError as err:
        print(err)

if __name__ == "__main__":
    main()
