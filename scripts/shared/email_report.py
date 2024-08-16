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
import check_data
import yaml_io

class Report:
    def __init__(self, assets: list[yaml_io.Asset], stats_file: str):
        delta = dict()

        with open(stats_file, 'r') as infile:
            delta = yaml.safe_load(infile)

        self.added = delta["added_this_week"]
        self.decom = delta["decom_this_week"]
        self.total = len(assets)

        # run all integrity checks to tally errors
        errs = []
        errs.extend(check_data.chk_all_missing(assets))
        errs.extend(check_data.chk_conflicting(assets))
        errs.extend(check_data.chk_uw_tag(assets))

        self.integrity_errs = len(errs)

        # generate the detailed error report
        with open("integrity_errs.txt", "w") as errfile:
            for err in errs:
                errfile.write(str(err))

        # TODO attach it to the email and delete

        # tally vendors and model
        # NOTE: since vendor is not it's own tag this is only a heuristic
        self.vendors = {
            "dell" : [],
            "supermicro" : [],
            "kingstar" : [],
            "cisco" : [],
            "other" : [],
        }

        for asset in assets:
            model = asset.get("hardware.model").lower()
            for vendor in self.vendors.keys():
                if len(model.split(" ")) > 1:
                    if vendor in model:
                        self.vendors[vendor].append(model.split(" ", 1)[1])
                        break
                    # somewhat special cases
                    elif "poweredge" in model:
                        # some dell servers say "PowerEdge XXXX" instead of "Dell PowerEdge XXXX"  
                        self.vendors["dell"].append(model.split(" ", 1)[1])
                        break
                    elif "king" in model and "star" in model:
                        # sometimes kingstar is two words
                        self.vendors["kingstar"].append(model.split(" ", 2)[2])
                        break
                else:
                    self.vendors["other"].append(model)
                    break

        self.atleast_ten = 0
        for asset in assets:
            # tally age
            acq_date = asset.get("acquisition.date")

            if acq_date and acq_date != "MISSING":
                date = datetime.datetime.strptime(acq_date, "%Y-%m-%d")
                today = datetime.datetime.today()

                # datetime has no 'years' attribute
                # so 3650 days is 10 years
                if abs((today - date).days) >= 3650:
                    self.atleast_ten += 1

    def __str__(self):
        lf = '\n'
        msg = "CHTC Weekly Inventory Report \n\n In the last week...\n"
        msg += f"    1. {self.added} assets were added, {self.decom} assets were decomissioned. We have {self.total} assets in total.{lf}"
        msg += f"    2. {self.integrity_errs} suspected data integrity errors currently exist (see attached file).{lf}"

        percent_over_ten = 100 * (self.atleast_ten / self.total) if self.atleast_ten != 0 else 0

        msg += f"    3. {self.atleast_ten} out of {self.total} total assets are at least 10 years old ({int(percent_over_ten)}%).{lf}"
        msg += f"    4. A breakdown of current inventory is:"
        msg += f"""
            {len(self.vendors['dell'])} Dell machines across {len(set(self.vendors['dell']))} models
            {len(self.vendors['supermicro'])} SuperMicro machines across {len(set(self.vendors['supermicro']))} models
            {len(self.vendors['kingstar'])} KingStar machines across {len(set(self.vendors['kingstar']))} models
            {len(self.vendors['cisco'])} Cisco machines across {len(set(self.vendors['cisco']))} models
            {len(self.vendors['other'])} Machines with other or missing models
        """

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

def reset_totals(stats_file: str):
    stats = dict()
    with open(stats_file, 'r') as infile:
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
    # TODO fix paths for GitHub action
    # get the config
    # c = config.get_config("config.yaml")
    # yaml_path = c.yaml_path

    stats_file = "../../.weekly_stats.yaml"
    assets = yaml_io.read_yaml("../../data/")

    report = Report(assets, stats_file)
    print(str(report), file=file)

    # reset the totals
    reset_totals(stats_file)
