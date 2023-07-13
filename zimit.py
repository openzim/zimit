#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

"""
Main zimit run script
This script validates arguments with warc2zim, checks permissions
and then calls the Node based driver
"""

import atexit
import itertools
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import urllib.parse
from argparse import ArgumentParser
from multiprocessing import Process
from pathlib import Path

import inotify
import inotify.adapters
import requests
from tld import get_fld
from warc2zim.main import warc2zim
from zimscraperlib.uri import rebuild_uri


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
                "done": data["crawled"],
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
    wait_until_options = ["load", "domcontentloaded", "networkidle"]
    wait_until_all = wait_until_options + [
        f"{a},{b}" for a, b in itertools.combinations(wait_until_options, 2)
    ]
    parser = ArgumentParser(
        description="Run a browser-based crawl on the specified URL and convert to ZIM"
    )

    parser.add_argument("-u", "--url", help="The URL to start crawling from")
    parser.add_argument("--title", help="ZIM title")
    parser.add_argument("--description", help="ZIM description")

    parser.add_argument(
        "--urlFile",
        help="If set, read a list of seed urls, " "one per line, from the specified",
    )

    parser.add_argument("-w", "--workers", type=int, help="Number of parallel workers")

    parser.add_argument(
        "--waitUntil",
        help="Puppeteer page.goto() condition to wait for before continuing. One of "
        f"{wait_until_options} or a comma-separated combination of those.",
        choices=wait_until_all,
        default="load",
    )

    parser.add_argument(
        "--depth", help="The depth of the crawl for all seeds", type=int, default=-1
    )

    parser.add_argument(
        "--extraHops",
        help="Number of extra 'hops' to follow, beyond the current scope",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--limit", help="Limit crawl to this number of pages", type=int, default=0
    )

    parser.add_argument(
        "--maxPageLimit",
        help="Maximum pages to crawl, overriding pageLimit if both are set",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--timeout",
        help="Timeout for each page to load (in seconds)",
        type=int,
        default=90,
    )

    parser.add_argument(
        "--scopeType",
        help="A predfined scope of the crawl. For more customization, "
        "use 'custom' and set scopeIncludeRx regexes",
        choices=["page", "page-spa", "prefix", "host", "domain", "any", "custom"],
    )

    parser.add_argument(
        "--include",
        help="Regex of page URLs that should be "
        "included in the crawl (defaults to "
        "the immediate directory of URL)",
    )

    parser.add_argument(
        "--exclude",
        help="Regex of page URLs that should be excluded from the crawl",
    )

    parser.add_argument(
        "--collection",
        help="Collection name to crawl to (replay will be accessible "
        "under this name in pywb preview) instead of crawl-@ts",
    )

    parser.add_argument(
        "--allowHashUrls",
        help="Allow Hashtag URLs, useful for "
        "single-page-application crawling or "
        "when different hashtags load dynamic "
        "content",
        action="store_true",
    )

    parser.add_argument(
        "--mobileDevice",
        help="Emulate mobile device by name from "
        "https://github.com/microsoft/playwright/blob/main/packages/"
        "playwright-core/src/server/deviceDescriptorsSource.json",
    )

    parser.add_argument(
        "--userAgent",
        help="Override user-agent with specified",
    )

    parser.add_argument(
        "--userAgentSuffix",
        help="Append suffix to existing browser user-agent "
        "(ex: +MyCrawler, info@example.com)",
        default="+Zimit ",
    )

    parser.add_argument(
        "--useSitemap",
        help="If set, use the URL as sitemap to get additional URLs for the crawl "
        "(usually /sitemap.xml)",
    )

    parser.add_argument(
        "--behaviors",
        help="Which background behaviors to enable on each page",
        default="autoplay,autofetch,siteSpecific",
    )

    parser.add_argument(
        "--behaviorTimeout",
        help="If >0, timeout (in seconds) for in-page behavior will run on each page. "
        "If 0, a behavior can run until finish",
        type=int,
        default=90,
    )

    parser.add_argument(
        "--delay",
        help="If >0, amount of time to sleep (in seconds) after behaviors "
        "before moving on to next page",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--profile",
        help="Path to tar.gz file which will be extracted "
        "and used as the browser profile",
    )

    parser.add_argument(
        "--sizeLimit",
        help="If set, save state and exit if size limit exceeds this value",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--diskUtilization",
        help="If set, save state and exit if diskutilization "
        "exceeds this percentage value",
        type=int,
        default=90,
    )

    parser.add_argument(
        "--timeLimit",
        help="If set, save state and exit after time limit, in seconds",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--healthCheckPort",
        help="port to run healthcheck on",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--overwrite",
        help="overwrite current crawl data: if set, existing collection directory "
        "will be deleted before crawl is started",
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
        "--custom-css",
        help="[warc2zim] Custom CSS file URL/path to inject into all articles",
    )

    parser.add_argument(
        "--statsFilename",
        help="If set, output stats as JSON to this file",
    )

    parser.add_argument(
        "--config",
        help="Path to YAML config file. If set, browsertrix-crawler will use this file"
        "to configure the crawling behaviour if not set via argument.",
    )

    zimit_args, warc2zim_args = parser.parse_known_args(args)

    # pass url and output to warc2zim also
    if zimit_args.output:
        warc2zim_args.append("--output")
        warc2zim_args.append(zimit_args.output)

    url = zimit_args.url

    if url:
        url = check_url(url, zimit_args.scopeType)
        warc2zim_args.append("--url")
        warc2zim_args.append(url)

    if zimit_args.custom_css:
        warc2zim_args += ["--custom-css", zimit_args.custom_css]

    if zimit_args.title:
        warc2zim_args.append("--title")
        warc2zim_args.append(zimit_args.title)

    if zimit_args.description:
        warc2zim_args.append("--description")
        warc2zim_args.append(zimit_args.description)

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

    user_agent_suffix = zimit_args.userAgentSuffix
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
    crawl = subprocess.run(cmd_args)
    if crawl.returncode == 11:
        print("crawl interupted by a limit")
    elif crawl.returncode != 0:
        raise subprocess.CalledProcessError(crawl.returncode, cmd_args)

    warc_files = list(temp_root_dir.rglob("collections/crawl-*/archive/"))[-1]
    warc2zim_args.append(str(warc_files))

    num_files = sum(1 for e in warc_files.iterdir())

    print("")
    print("----------")
    print(f"Processing {num_files} WARC files to ZIM", flush=True)

    return warc2zim(warc2zim_args)


def check_url(url, scope=None):
    url = urllib.parse.urlparse(url)
    try:
        resp = requests.head(
            url.geturl(), stream=True, allow_redirects=True, timeout=(12.2, 27)
        )
    except requests.exceptions.RequestException as exc:
        print(f"failed to connect to {url.geturl()}: {exc}", flush=True)
        raise SystemExit(1)
    actual_url = urllib.parse.urlparse(resp.url)

    # remove explicit port in URI for default-for-scheme as browsers does it
    if actual_url.scheme == "https" and actual_url.port == 443:
        actual_url = rebuild_uri(actual_url, port="")
    if actual_url.scheme == "http" and actual_url.port == 80:
        actual_url = rebuild_uri(actual_url, port="")

    if actual_url.geturl() != url.geturl():
        if scope in (None, "any"):
            return actual_url.geturl()

        print(
            "[WARN] Your URL ({0}) redirects to {1} which {2} on same "
            "first-level domain. Depending on your scopeType ({3}), "
            "your homepage might be out-of-scope. Please check!".format(
                url.geturl(),
                actual_url.geturl(),
                "is"
                if get_fld(url.geturl()) == get_fld(actual_url.geturl())
                else "is not",
                scope,
            )
        )

        return actual_url.geturl()

    return url.geturl()


def get_node_cmd_line(args):
    node_cmd = ["crawl", "--failOnFailedSeed"]
    for arg in [
        "workers",
        "waitUntil",
        "urlFile",
        "title",
        "description",
        "depth",
        "extraHops",
        "limit",
        "maxPageLimit",
        "timeout",
        "scopeType",
        "include",
        "exclude",
        "collection",
        "allowHashUrls",
        "mobileDevice",
        "userAgent",
        "useSitemap",
        "behaviors",
        "behaviorTimeout",
        "delay",
        "profile",
        "sizeLimit",
        "diskUtilization",
        "timeLimit",
        "healthCheckPort",
        "overwrite",
        "config",
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
