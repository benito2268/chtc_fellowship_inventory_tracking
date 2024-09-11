# chtc_inventory

This repo holds a project I worked on during the 2024 Fellowship Program at the Center for High Throughput Computing at UW-Madison.

**Note: This repo represents work that was done solely as part of the 2024 fellowship. The project was archived in the state it existed in upon completion of the fellowship**

The project consists of a set of tools designed to manage and manipulate inventory records for CHTC's technical assets (mostly servers). This repository holds the scripts that make up said tools, as well as sample data and other products of the fellowship.

This repo:
1) Is THE place to store asset data in YAML form 
2) Provides tools to manage said asset data in the form of python scripts from the CLI
    - Adding new assets
    - Retiring Legacy assets
    - Changing asset location
    - Renaming assets
    - Updating Asset Attributes
3) Provides automatic reporting functionality as well as data integretiy checking, via Github Action 
4) Provides Google Sheets integration to publish a read-only spreadsheet that updates automatically as the YAML data is updated
    - Google sheets integration requires a Google Cloud Platform Service Account, as well as authorization, authentication, and ACL configuration to manage consumers of this spreadsheet 
    - Automation is accompilshed via a Github Action
       - For better or worse, the Github Action must have some access to the "secret" that allows updating of the sheet

# Details
This section contains a more deatailed breakdown of each script, how to use it, and how it works.
### `csv2yaml.py`
`scripts/csv2yaml/csv2yaml.py`
A one-off import script used to convert inventory data from a spreadsheet to YAML format

#### How to Use It:
This script should be run from either the repository's base directory (`asset_data/`) or from it's own directory.
To use it, pass the script a path to a local copy of the CHTC Inventory Spreasheet and optionally a YAML output path using the `-o` or `--output` flag (run `./csv2yaml.py --help` to see full options). If `-o` or `--output` is not specified the output path is read from `yaml_path` in `config.yaml`

#### How it Works:
This script reads the inventory spreadsheet using a predefined column map that determines which spreadsheet columns
correspond to which YAML tags. The script constructs a YAML-like dictionary object with the data and uses the PyYAML Python module to dump the YAML to a file.

### `check_data.py`
`scripts/integrity_checker/check_data.py`
A script to check for data integrity issues in YAML asset data.

#### How to Use It:
This script is run automatically by the repository's GitHub Action each time a push occurs, however it can also be run manually from the command line. Currently, the script has options to check for missing tags, conflicting tags (i.e. two servers that claim the same rack-elevation), or UW asset tags that have been missing for at least 6 months since the purchase data. These options can be controlled via command line flags (run `./check_data.py --help` to see options). If no checks are specified on the command line, all checks are run. Optionally, you may also specify a path to YAML data, if you wish to override `config.yaml`.

#### How it Works:
This script performs a set of checks on YAML asset data, each defined in a function. These functions are mapped to their respective arguments in the `validate_funcs` `dict` in the main function. To add a new integrity check, implement a function for it, implement a function for it, add an argument, and add an entry to `validate_funcs`. Interally the script provides a list of `Asset` objects within the main function (see `scripts/shared/yaml_io.py` for the `Asset` class).

### `sheet_create.py`, `sheet_delete.py`, and `sheet_update.py`
`scripts/sheets/*.py`    
Scripts for manipulating the Google Sheets spreadsheet populated by asset data.

#### How to Use Them:
##### `sheet_create.py`:
This script is used to generate a fresh Google Sheet. Sheets are identified by a "[Spreadsheet ID](https://developers.google.com/sheets/api/guides/concepts)" the ID of the current working sheet is stored automatically by the scripts in `scripts/sheets/.spreadsheet_id` modifying the contents of this file can break the scripts. When a new sheet is created **this file is overwritten with the new ID**, but the old spreadsheet is not deleted and it's ID can be obtained from its URL. As a result replacing the ID in this file will change the current working spreadsheet. To use it, provide an email address for the service account to share the sheet with (most likely yourself). From there, sharing can be done normally through Google Drive.

##### `sheet_delete.py`:
This script is used to delete files from the service account's Google Drive. Like any Google Drive account, a service account is limited to 15GB of storage. Unlike a normal Drive, it is not accessible through a GUI for managing files. This script allows for old files to be deleted. To use, run the script with no arguments. The script will list all of the files in the service account's Drive and their IDs. To delete a file, copy the ID of the file you wish to delete into the prompt and press enter.

##### `sheet_update.py`:
The most substantial of the sheets scripts, this script handles updating both the current and decomissioned tabs of the spreadsheet to reflect additions, deletions, and changes to the YAML data. This script is run automatically by the repository's GitHub Action each time a push occurs, but it can also be run manually from the command line. If you wish to run manually, the script takes no arguments and the update will take place with respect to the data located at `yaml_path` in `config.yaml`.

#### How They Work:
These scripts make use of the [Google Sheets API](https://developers.google.com/sheets/api/guides/concepts) and associated Python client libraries (see "Getting Started"). The spreadsheet is stored in a Google Drive belonging to a "[service account](https://cloud.google.com/iam/docs/service-account-overview)", a Google bot account that acts similarily to a user. A service account has it's own email address (though it might ignore your emails :P), Drive, and keys to authenticate with Google APIs. Service accounts, and the APIs themselves are configured in Google Cloud Platform

### The `scripts/shared/` Directory
This directory contains several scripts with code that is commonly shared among other scripts in the system. Almost all of the other scripts add `scripts/shared/` to `sys.path` near the top of the file to make them accessible. `yaml_io.py` contains the definition for the `Asset` object, as well as functions for reading from and writing to and from YAML files. `dict_utils.py` contains methods for flattening and unflattening Python `dict`s, which is commonly used by the other scripts. `config.py` contains code for reading the config. Finally, `email_report.py` contains code that generates email message bodies for both errors and weekly report emails.


### Sending a Weekly Report Email ###
To send a weekly report email using a `cron` or other `cron`-like system run the `email_report.py` script from the repo's top level directory (`asset_data/`). The script take no arguments, and will send reports to each email in `summary_email_list` in `config.yaml`.

Example invocation: `./scripts/shared/email_report.py`
