# a list the specifies the order 
# this also filters what appears in the spreadsheeti
# anything that doesn't appear here also won't in the sheet
COLUMN_MAP = [
    "location.building",
    "location.room",
    "location.rack",
    "location.elevation",
    "hardware.model",
    "hardware.serial_number",
    "hardware.service_tag",
    "hardware.condo_chassis.model",
    "hardware.condo_chassis.identifier",
    "tags.uw",
    "tags.csl",
    "tags.morgridge",
    "hardware.notes",
    "hardware.purpose",
]

PRETTY_COL_NAMES = [
    "Building",
    "Room",
    "Rack",
    "Elevation",
    "Model",
    "Serial Number",
    "Service Tag",
    "Condo Model",
    "Condo Serial",
    "UW Tag",
    "CSL Tag",
    "Morgridge Tag",
    "Notes",
    "Purpose",
]

# + 1 because we need a column for the hostname
NUM_COLUMNS = len(COLUMN_MAP) + 1
