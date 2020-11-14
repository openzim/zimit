#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

"""
Main zimit run script
This script validates arguments with warc2zim, checks permissions
and then calls the Node based driver
"""

from argparse import ArgumentParser
import tempfile
import subprocess
import atexit
import shutil
import signal
import sys
from pathlib import Path
from urllib.parse import urlsplit

from warc2zim.main import warc2zim
import requests


def zimit(args=None):
    parser = ArgumentParser(
        description="Run a browser-based crawl on the specified URL and convert to ZIM"
    )

    parser.add_argument("-u", "--url", help="The URL to start crawling from")

    parser.add_argument("-w", "--workers", type=int, help="Number of parallel workers")

    parser.add_argument(
        "--newContext",
        help="The context for each new capture (page, session or browser).",
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
        help="Regex of page URLs that should be included in the crawl "
        "(defaults to the immediate directory of the URL)",
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

    parser.add_argument("--adminEmail", help="Admin Email for Zimit crawler")

    parser.add_argument(
        "--mobileDevice", help="Crawl as Mobile Device", nargs="?", const="iPhone X"
    )

    zimit_args, warc2zim_args = parser.parse_known_args(args)

    # pass url and output to warc2zim also
    if zimit_args.output:
        warc2zim_args.append("--output")
        warc2zim_args.append(zimit_args.output)

    url = zimit_args.url

    if url:
        url = check_url(url)
        warc2zim_args.append("--url")
        warc2zim_args.append(url)

    print("----------")
    print("Testing warc2zim args")
    print("Running: warc2zim " + " ".join(warc2zim_args), flush=True)
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
            print(f"Cleanup, removing temp dir: {temp_root_dir}", flush=True)
            shutil.rmtree(temp_root_dir)

        atexit.register(cleanup)

    cmd_args = get_node_cmd_line(zimit_args)
    if url:
        cmd_args.append("--url")
        cmd_args.append(url)

    user_agent_suffix = "+Zimit "
    if zimit_args.adminEmail:
        user_agent_suffix += zimit_args.adminEmail

    cmd_args.append("--userAgentSuffix")
    cmd_args.append(user_agent_suffix)

    cmd_args.append("--cwd")
    cmd_args.append(str(temp_root_dir))

    cmd_line = " ".join(cmd_args)

    print("")
    print("----------")
    print(f"Output to tempdir: {temp_root_dir} - {'will keep' if zimit_args.keep else 'will delete'}")
    print(f"Running browsertrix-crawler crawl: {cmd_line}", flush=True)
    subprocess.run(cmd_args, check=True)

    warc_files = temp_root_dir / "collections" / "capture" / "archive"
    warc2zim_args.append(str(warc_files))

    num_files = sum(1 for e in warc_files.iterdir())

    print("")
    print("----------")
    print(f"Processing {num_files} WARC files to ZIM", flush=True)

    return warc2zim(warc2zim_args)


def check_url(url):
    try:
        resp = requests.head(url, stream=True, allow_redirects=True, timeout=10)
    except requests.exceptions.RequestException as exc:
        print(f"failed to connect to {url}: {exc}", flush=True)
        raise SystemExit(1)
    actual_url = resp.url

    if actual_url != url:
        if urlsplit(url).netloc != urlsplit(actual_url).netloc:
            raise ValueError(
                f"Main page URL ({url}) redirects to out-of-scope domain "
                f"({actual_url}), cancelling crawl"
            )

        return actual_url

    return url


def get_node_cmd_line(args):
    node_cmd = ["crawl"]
    for arg in [
        "workers",
        "newContext",
        "waitUntil",
        "limit",
        "timeout",
        "scope",
        "exclude",
        "scroll",
        "mobileDevice",
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
    print("", flush=True)
    sys.exit(3)


signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

if __name__ == "__main__":
    zimit()
