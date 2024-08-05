# asset_data
Infrastructure Inventory Data and Scripts

This is CHTC Infrastructure Services' Production Asset Inventory System. 
It's an "informal" clone of Ben Staehle's 2024 Fellowship Project, originally here:  https://github.com/benito2268/chtc_fellowship_inventory_tracking/tree/main
Cloning in this method was necessary since production CHTC Asset data and the scripts he authored co-habitate. The data isn't sensitive but doesn't make sense to make public intentionally.
Original Data population was accomplished by reading CHTC's manually edited Inventory Google Sheet into this repo.

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
