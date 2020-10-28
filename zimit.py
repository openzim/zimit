#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

"""
Main zimit run script
This script validates arguments with warc2zim, checks permissions
and then calls the Node based driver
"""

from argparse import ArgumentParser
import os
import tempfile
import subprocess
import atexit
import shutil
import glob
import signal
import sys
from pathlib import Path

from warc2zim.main import warc2zim


def zimit(args=None):
    parser = ArgumentParser(
        description="Run a browser-based crawl on the specified URL and convert to ZIM"
    )

    parser.add_argument("-u", "--url", help="The URL to start crawling from")

    parser.add_argument("-w", "--workers", type=int, help="Number of parallel workers")

    parser.add_argument(
        "--newContext",
        help="The context for each new capture, can be a new: page, session or browser.",
        choices=["page", "session", "browser"],
        default="page",
    )

    parser.add_argument(
        "--waitUntil",
        help="Puppeteer page.goto() condition to wait for before continuing",
        choices=["load", "domcontentloaded", "networkidle0", "networkidle2"],
        default="load",
    )

    parser.add_argument(
        "--limit", help="Limit crawl to this number of pages", type=int, default=0
    )

    parser.add_argument(
        "--timeout",
        help="Timeout for each page to load (in seconds)",
        type=int,
        default=90,
    )

    parser.add_argument(
        "--scope",
        help="Regex of page URLs that should be included in the crawl (defaults to the immediate directory of the URL)",
    )

    parser.add_argument(
        "--exclude", help="Regex of page URLs that should be excluded from the crawl."
    )

    parser.add_argument(
        "--scroll",
        help="If set, will autoscroll to bottom of the page",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--keep",
        help="If set, keep WARC files after crawl, don't delete",
        action="store_true",
    )

    parser.add_argument(
        "--output", help="Output directory for ZIM and WARC files", default="/output"
    )

    zimit_args, warc2zim_args = parser.parse_known_args(args)

    # pass url and output to warc2zim also
    if zimit_args.output:
        warc2zim_args.append("--output")
        warc2zim_args.append(zimit_args.output)

    if zimit_args.url:
        warc2zim_args.append("--url")
        warc2zim_args.append(zimit_args.url)

    print("----------")
    print("Testing warc2zim args")
    print("Running: warc2zim " + " ".join(warc2zim_args))
    res = warc2zim(warc2zim_args)
    if res != 100:
        print("Exiting, invalid warc2zim params")
        return 2

    # make temp dir for this crawl
    temp_root_dir = Path(tempfile.mkdtemp(dir=zimit_args.output, prefix=".tmp"))

    if not zimit_args.keep:

        def cleanup():
            print("")
            print("----------")
            print("Cleanup, removing temp dir: " + str(temp_root_dir))
            shutil.rmtree(temp_root_dir)

        atexit.register(cleanup)

    # create pywb collection
    print("")
    print("----------")
    print("pywb init")
    subprocess.run(
        ["/usr/bin/env", "wb-manager", "init", "capture"], check=True, cwd=temp_root_dir
    )  # nosec

    subprocess.Popen(
        ["/usr/bin/env", "redis-server"], cwd=temp_root_dir, stdout=subprocess.DEVNULL
    )  # nosec

    subprocess.Popen(
        ["/usr/bin/env", "uwsgi", os.getcwd() + "/uwsgi.ini"],
        cwd=temp_root_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )  # nosec

    cmd_args = get_node_cmd_line(zimit_args)
    cmd_line = " ".join(cmd_args)

    print("")
    print("----------")
    print("running zimit driver: " + cmd_line)
    subprocess.run(cmd_args, check=True)

    warc_files = temp_root_dir / "collections" / "capture" / "archive"
    warc2zim_args.append(str(warc_files))

    num_files = sum(1 for e in warc_files.iterdir())

    print("")
    print("----------")
    print("Processing {0} WARC files to ZIM".format(num_files))

    return warc2zim(warc2zim_args)

def get_node_cmd_line(args):
    node_cmd = ["/usr/bin/env", "node", "crawler.js"]
    for arg in [
        "url",
        "workers",
        "newContext",
        "waitUntil",
        "limit",
        "timeout",
        "scope",
        "exclude",
        "scroll",
    ]:
        value = getattr(args, arg)
        if value:
            node_cmd.append("--" + arg)
            if not isinstance(value, bool):
                node_cmd.append(str(value))

    return node_cmd


def sigint_handler(*args):
    print("")
    print("")
    print("SIGINT/SIGTERM received, stopping zimit")
    print("")
    print("")
    sys.exit(3)


signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

if __name__ == "__main__":
    zimit()
