#!/bin/python3

# this script manages email reporting (error and weekly info)
# for the inventory system

import os
import io
import sys
import traceback
import yaml
import datetime
import smtplib
import email

from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.utils import COMMASPACE

sys.path.append(os.path.abspath("./"))
sys.path.append(os.path.abspath("scripts/shared/"))

sys.path.append(os.path.abspath("../integrity_checker/"))
sys.path.append(os.path.abspath("scripts/integrity_checker/"))

import config
import check_data
import yaml_io

ERROR_FILE_NAME = "integrity_errors.txt"
CONFIG_PATH = "config.yaml"
STATS_PATH = ".weekly_stats.yaml"

MISSING_RXP = "(?i)none|missing|\\?+|^\\s*$"

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
        with open(ERROR_FILE_NAME, "w") as errfile:
            for err in errs:
                errfile.write(str(err))


        # tally vendors and model
        # NOTE: since vendor is not it's own tag this is only a heuristic
        # each dict value is a list (not a set) of models
        self.vendors = dict()

        # to make this work, the vendor should be the first word in
        # hardware.model and the model should make up the rest 
        # example: "Dell PowerEdge C6400" will be read as
        # vendor: "Dell" - Model: "PowerEdge C6400"
        for asset in assets:
            splitlist = asset.get("hardware.model").split(" ", 1)
            vendor = splitlist[0]
            if not re.fullmatch(MISSING_RXP, vendor):

                lower = ' '.join([s.lower() for s in splitlist])
                key = vendor

                # try to catch a couple different vendor name spellings
                if "poweredge" in lower:
                    key = "Dell"
                elif "super" in lower and "micro" in lower:
                    key = "SuperMicro"
                elif "king" in lower and "star" in lower:
                    key = "KingStar"

                if key not in self.vendors:
                    self.vendors[key] = []

                if not len(splitlist) > 1:
                    self.vendors[key].append("")
                else:
                    self.vendors[key].append(splitlist[1])

        # count the number of assets that are at least (>=) ten
        # years old
        self.atleast_ten = 0
        for asset in assets:
            acq_date = asset.get("acquisition.date")

            if acq_date and not re.fullmatch(MISSING_RXP, acq_date):
                date = datetime.datetime.strptime(acq_date, "%Y-%m-%d")
                today = datetime.datetime.today()

                # datetime has no 'years' attribute
                # so 3650 days is 10 years
                if abs((today - date).days) >= 3650:
                    self.atleast_ten += 1

    def __str__(self):
        # these are here because f-strings don't apprciate escape chars
        lf = '\n'
        tab = '\t'
        date = datetime.datetime.today().strftime("%Y-%m-%d")

        # subject line
        msg = f"CHTC Weekly Inventory Report for {date} {lf}{lf} Inventory Summary for {date}\n"

        # added, decom'ed, and total assets line
        msg += f"{tab}1. In the last week, {str(self.added) + ' assets were added' if self.added > 0 else ''}"
        msg += f"{self.decom  + ', assets were decomissioned.' if self.decom > 0 else ''}"
        msg += f" CHTC has {self.total} assets currently in service.{lf}" # presumably, the total will always be > 0, otherwise CHTC is in trouble :)

        # fresh integrity check summary line
        msg += f"{tab}2. {self.integrity_errs} suspected data integrity issues currently exist (see attached file).{lf}"

        # number of assets over 10 years old
        percent_over_ten = 100 * (self.atleast_ten / self.total) if self.atleast_ten != 0 else 0
        msg += f"{tab}3. {self.atleast_ten} out of {self.total} in-service assets were purchased 10 or more years ago ({int(percent_over_ten)}%).{lf}"

        # per-vendor and per-model breakdown
        msg += f"{tab}4. A breakdown of current inventory by vendor is:{lf}"

        # generate the breakdown message
        # sort by number of machine
        sorted_keys = sorted(self.vendors, key=lambda key: len(self.vendors[key]), reverse=True)
        for key in sorted_keys:
            msg += f"{tab}{tab}{len(self.vendors[key])} {key} machines across {len(set(self.vendors[key]))} models{lf}"

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
def send_err_report(exc_info: tuple):
    lf = '\n'
    msg = ""
    exc_type, exc_value, exc_tb = exc_info

    tb = io.StringIO()
    traceback.print_tb(exc_tb, file=tb)

    msg += f"An exception occurred during inventory update{lf}"
    msg += f"{exc_type.__name__}: {exc_value} in {os.path.basename(exc_tb.tb_frame.f_code.co_filename)} at line {exc_tb.tb_lineno}{lf}{lf}"
    msg += f"Traceback:{lf}{tb.getvalue()}"

    tb.close()

    # get the config
    c = config.get_config(CONFIG_PATH)

    stats_file = STATS_PATH

    email_out = io.StringIO()
    email_out.write(msg)

    msg = MIMEMultipart()
    msg.attach(MIMEText(email_out.getvalue()))

    subject = "CHTC Inventory - Scripts Failed"
    send_from = "chtc-inventory"

    msg['Subject'] = subject
    msg['From'] = send_from
    msg['To']  = COMMASPACE.join(c.err_emails)

    # send the message via a (very briefly alive) local SMTP server
    s = smtplib.SMTP("localhost")
    s.sendmail(send_from, c.err_emails, msg.as_string())
    s.quit()

    email_out.close()

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
def send_weekly_report():
    # get the config
    c = config.get_config(CONFIG_PATH)

    stats_file = STATS_PATH
    assets = yaml_io.read_yaml(c.yaml_path)

    report = Report(assets, stats_file)
    email_out = io.StringIO()
    email_out.write(str(report))

    msg = MIMEMultipart()
    msg.attach(MIMEText(email_out.getvalue()))

    subject = "CHTC Inventory - Weekly Report"
    send_from = "chtc-inventory"

    msg['Subject'] = subject
    msg['From'] = send_from
    msg['To']  = COMMASPACE.join(c.sum_emails)

    with open(ERROR_FILE_NAME, 'r') as err_file:
        attachment = MIMEApplication(err_file.read(), Name=ERROR_FILE_NAME)

    attachment["Content-Disposition"] = f"attachment; filename={ERROR_FILE_NAME}"
    msg.attach(attachment)

    # send the message via a (very briefly alive) local SMTP server
    s = smtplib.SMTP("localhost")
    s.sendmail(send_from, c.sum_emails, msg.as_string())
    s.quit()

    email_out.close()

    # reset the totals
    reset_totals(stats_file)

    # remove the errors file
    os.remove(ERROR_FILE_NAME)

def main():
    send_weekly_report()

if __name__ == "__main__":
    main()


