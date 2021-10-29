#!/usr/bin/env /usr/bin/python3.8
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

"""
Main zimit run script
This script validates arguments with warc2zim, checks permissions
and then calls the Node based driver
"""

import re
import itertools
from argparse import ArgumentParser
import tempfile
import subprocess
import atexit
import shutil
import signal
import sys
import json
from pathlib import Path
from multiprocessing import Process

from warc2zim.main import warc2zim
import requests

import inotify
import inotify.adapters
from tld import get_fld


class ProgressFileWatcher:
    def __init__(self, output_dir, stats_path):
        self.crawl_path = output_dir / "crawl.json"
        self.warc2zim_path = output_dir / "warc2zim.json"
        self.stats_path = Path(stats_path)

        if not self.stats_path.is_absolute():
            self.stats_path = output_dir / self.stats_path

        # touch them all so inotify is not unhappy on add_watch
        self.crawl_path.touch()
        self.warc2zim_path.touch()
        self.stats_path.touch()
        self.process = None

    def stop(self):
        self.process.join(0.1)
        self.process.terminate()

    def watch(self):
        self.process = Process(
            target=self.inotify_watcher,
            args=(str(self.crawl_path), str(self.warc2zim_path), str(self.stats_path)),
        )
        self.process.daemon = True
        self.process.start()

    @staticmethod
    def inotify_watcher(crawl_fpath, warc2zim_fpath, output_fpath):
        ino = inotify.adapters.Inotify()
        ino.add_watch(crawl_fpath, inotify.constants.IN_MODIFY)
        ino.add_watch(warc2zim_fpath, inotify.constants.IN_MODIFY)

        class Limit:
            def __init__(self):
                self.max = self.hit = None

            @property
            def as_dict(self):
                return {"max": self.max, "hit": self.hit}

        # limit is only reported by crawl but needs to be reported up
        limit = Limit()

        def crawl_conv(data, limit):
            # we consider crawl to be 90% of the workload so total = craw_total * 90%
            # limit = {"max": data["limit"]["max"], "hit": data["limit"]["hit"]}
            limit.max = data["limit"]["max"]
            limit.hit = data["limit"]["hit"]
            return {
                "done": data["numCrawled"],
                "total": int(data["total"] / 0.9),
                "limit": limit.as_dict,
            }

        def warc2zim_conv(data, limit):
            # we consider warc2zim to be 10% of the workload so
            # warc2zim_total = 10% and  total = 90 + warc2zim_total * 10%
            return {
                "done": int(
                    data["total"]
                    * (0.9 + (float(data["written"]) / data["total"]) / 10)
                ),
                "total": data["total"],
                "limit": limit.as_dict,
            }

        for _, _, fpath, _ in ino.event_gen(yield_nones=False):
            func = {crawl_fpath: crawl_conv, warc2zim_fpath: warc2zim_conv}.get(fpath)
            if not func:
                continue
            # open input and output separatly as to not clear output on error
            with open(fpath, "r") as ifh:
                try:
                    out = func(json.load(ifh), limit)
                except Exception:  # nosec
                    # simply ignore progress update should an error arise
                    # might be malformed input for instance
                    continue
                if not out:
                    continue
                with open(output_fpath, "w") as ofh:
                    json.dump(out, ofh)


def zimit(args=None):
    wait_until_options = ["load", "domcontentloaded", "networkidle0", "networkidle2"]
    wait_until_all = wait_until_options + [
        f"{a},{b}" for a, b in itertools.combinations(wait_until_options, 2)
    ]
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
        help="Puppeteer page.goto() condition to wait for before continuing. One of "
        f"{wait_until_options} or a comma-separated combination of those.",
        choices=wait_until_all,
        default="load,networkidle0",
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

    parser.add_argument(
        "--useSitemap",
        help="If set, use the URL as sitemap to get additional URLs for the crawl (usually /sitemap.xml)",
    )

    parser.add_argument(
        "--custom-css",
        help="[warc2zim] Custom CSS file URL/path to inject into all articles",
    )

    parser.add_argument(
        "--statsFilename",
        help="If set, output stats as JSON to this file",
    )

    zimit_args, warc2zim_args = parser.parse_known_args(args)

    # pass url and output to warc2zim also
    if zimit_args.output:
        warc2zim_args.append("--output")
        warc2zim_args.append(zimit_args.output)

    url = zimit_args.url

    if url:
        url = check_url(url, zimit_args.scope)
        warc2zim_args.append("--url")
        warc2zim_args.append(url)

    if zimit_args.custom_css:
        warc2zim_args += ["--custom-css", zimit_args.custom_css]

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

    # setup inotify crawler progress watcher
    if zimit_args.statsFilename:
        watcher = ProgressFileWatcher(
            Path(zimit_args.output), Path(zimit_args.statsFilename)
        )
        print(f"Writing progress to {watcher.stats_path}")
        # update crawler command
        cmd_args.append("--statsFilename")
        cmd_args.append(str(watcher.crawl_path))
        # update warc2zim command
        warc2zim_args.append("-v")
        warc2zim_args.append("--progress-file")
        warc2zim_args.append(str(watcher.warc2zim_path))
        watcher.watch()

    cmd_line = " ".join(cmd_args)

    print("")
    print("----------")
    print(
        f"Output to tempdir: {temp_root_dir} - {'will keep' if zimit_args.keep else 'will delete'}"
    )
    print(f"Running browsertrix-crawler crawl: {cmd_line}", flush=True)
    subprocess.run(cmd_args, check=True)

    warc_files = list(temp_root_dir.rglob("collections/capture-*/archive/"))[-1]
    warc2zim_args.append(str(warc_files))

    num_files = sum(1 for e in warc_files.iterdir())

    print("")
    print("----------")
    print(f"Processing {num_files} WARC files to ZIM", flush=True)

    return warc2zim(warc2zim_args)


def check_url(url, scope=None):
    try:
        resp = requests.head(url, stream=True, allow_redirects=True, timeout=10)
    except requests.exceptions.RequestException as exc:
        print(f"failed to connect to {url}: {exc}", flush=True)
        raise SystemExit(1)
    actual_url = resp.url

    if actual_url != url:
        # redirect on same domain or same first-level domain
        if get_fld(url) == get_fld(actual_url):
            return actual_url

        # is it in scope?
        if scope:
            try:
                if re.match(scope, actual_url):
                    return actual_url
            except Exception as exc:
                print(f"failed to parse your scope regexp for url checking: {exc}")

        raise ValueError(
            f"Main page URL ({url}) redirects to out-of-scope domain "
            f"({actual_url}), cancelling crawl"
        )

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
        "useSitemap",
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
