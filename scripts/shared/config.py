# facilitates reading the config file 
# and providing the inventory system with it's settings

import yaml

# a simple (could be a data class) the holds the config
class Config:
    def __init__(self, yaml_path: str, swapped_path: str, sum_emails: list, err_emails: list):
        if not yaml_path.endswith('/'):
            yaml_path += '/'
        if not swapped_path.endswith('/'):
            swapped_path += '/'

        self.yaml_path = yaml_path
        self.swapped_path = swapped_path
        self.sum_emails = sum_emails
        self.err_emails = err_emails

def get_config(config_path: str) -> Config:
    cfg = dict()

    with open(config_path, 'r') as infile:
        cfg = yaml.safe_load(infile)

    return Config(
        cfg["yaml_path"],
        cfg["swapped_path"],
        cfg["summary_email_list"],
        cfg["error_email_list"],
    )

