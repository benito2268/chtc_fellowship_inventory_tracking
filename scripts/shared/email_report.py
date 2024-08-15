# this script manages email reporting (error and weekly info)
# for the inventory system

import os
import io
import sys
import traceback
import yaml
import datetime

sys.path.append(os.path.abspath("./"))
sys.path.append(os.path.abspath("scripts/shared/"))

sys.path.append(os.path.abspath("../data_validator/"))
sys.path.append(os.path.abspath("scripts/data_validator/"))

import config
import validate
import yaml_io

class Report:
    def __init__(self, assets: list[yaml_io.Asset], stats_file: str):
        delta = dict()

        with open(stats_file, 'r') as infile:
            delta = yaml.safe_load(infile)

        self.added = delta["added_this_week"]
        self.decom = delta["decom_this_week"]
        self.total = len(assets)

        # run a validation check to tally errors
        self.integrity_errs = 0

        # tally vendors and model
        # NOTE: since vendor is not it's own tag
        # this assumes that the vendor is the first word in the 'hardware.model' field
        vendors = dict()
        self.atleast_ten = 0

        for asset in assets:
            #vendors["newkey"].append()

            # tally age
            acq_date = asset.get("acquisition.date")

            if acq_date:
                date = datetime.datetime.strptime(acq_date, "%Y-%m-%d")
                today = datetime.datetime.today()

                # datetime has no 'years' attribut
                # so 3650 days is 10 years
                if abs((today - date).days) >= 3650:
                    self.atleast_ten += 1

    def __str__(self):
        lf = '\n'
        msg = f"{self.added} assets were added, {self.decom} assets were decomissioned.{lf}"
        msg += f"{self.integrity_errs} suspected data integrity errors currently exist (see attached CSV).{lf}"

        percent_over_ten = 100 * (self.atleast_ten / self.total) if self.atleast_ten != 0 else 0

        msg += f"{self.atleast_ten} out of {self.total} assets are at least 10 years old ({int(percent_over_ten)}%){lf}"
        msg += f"vendors"

        return msg

    def __repr__(self):
        return self.__str__()

# adds to the weekly running tally for added and decom'ed assets
# if add == False the operation is considered in decom
def count_add_or_rm(add: bool, count: int):
    stats = dict()
    with open(".weekly_stats.yaml", 'r') as infile:
        stats = yaml.safe_load(infile)

    if add:
        stats["added_this_week"] += count
    else:
        stats["decom_this_week"] += count

    with open(".weekly_stats.yaml", 'w') as outfile:
        yaml.safe_dump(stats, outfile)

def reset_totals():
    stats = dict()
    with open(".weekly_stats.yaml", 'r') as infile:
        stats = yaml.safe_load(infile)

    stats["added_this_week"] = 0
    stats["decom_this_week"] = 0

    with open(".weekly_stats.yaml", 'w') as outfile:
        yaml.safe_dump(stats, outfile)

# generates a human readable email error when
# when passed a tuple from sys.exc_info()
def report(exc_info: tuple, file: str=sys.stdout):
    lf = '\n'
    msg = ""
    exc_type, exc_value, exc_tb = exc_info

    tb = io.StringIO()
    traceback.print_tb(exc_tb, file=tb)

    msg += f"An exception occurred during inventory update{lf}"
    msg += f"{exc_type.__name__}: {exc_value} in {os.path.basename(exc_tb.tb_frame.f_code.co_filename)} at line {exc_tb.tb_lineno}{lf}{lf}"
    msg += f"Traceback:{lf}{tb.getvalue()}"

    tb.close()

    print(msg)

# generates a body for a periodic inventory summary
# email. The body is 'printed' to the specified file
# (or stdout by default)
#
# formatted as follows:
# This week:
#   - X assets were added, Y were decomissioned.
#   - X assets have data integrity issues (see attached CSV)
#   - X assets are older than Y years (Z %)
#   - X total assets are from Y vendors
#       - X <vendor> across Y models
#       - X <vendor2> across Y models
# 
def gen_weekly_report(file: str=sys.stdout):
    # get the config
    # c = config.get_config("config.yaml")
    #yaml_path = c.yaml_path

    assets = yaml_io.read_yaml("../../data/")

    report = Report(assets, "../../.weekly_stats.yaml")
    print(str(report), file=file)

    # reset the totals
    reset_totals()
