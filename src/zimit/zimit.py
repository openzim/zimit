"""
Main zimit run script
This script validates arguments with warc2zim, checks permissions
and then calls the Node based driver
"""

import atexit
import json
import logging
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
from argparse import ArgumentParser
from multiprocessing import Process
from pathlib import Path

import inotify
import inotify.adapters
import requests
from warc2zim.main import main as warc2zim
from zimscraperlib.logging import getLogger
from zimscraperlib.uri import rebuild_uri

from zimit.__about__ import __version__

EXIT_CODE_WARC2ZIM_CHECK_FAILED = 2
EXIT_CODE_CRAWLER_LIMIT_HIT = 11
NORMAL_WARC2ZIM_EXIT_CODE = 100
REQUESTS_TIMEOUT = 10

logger = getLogger(name="zimit", level=logging.INFO)


class ProgressFileWatcher:
    def __init__(self, output_dir: Path, stats_path: Path):
        self.crawl_path = output_dir / "crawl.json"
        self.warc2zim_path = output_dir / "warc2zim.json"
        self.stats_path = stats_path

        if not self.stats_path.is_absolute():
            self.stats_path = output_dir / self.stats_path

        # touch them all so inotify is not unhappy on add_watch
        self.crawl_path.touch()
        self.warc2zim_path.touch()
        self.process = None

    def stop(self):
        if not self.process:
            return
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
    def inotify_watcher(crawl_fpath: str, warc2zim_fpath: str, output_fpath: str):
        ino = inotify.adapters.Inotify()
        ino.add_watch(crawl_fpath, inotify.constants.IN_MODIFY)  # pyright: ignore
        ino.add_watch(warc2zim_fpath, inotify.constants.IN_MODIFY)  # pyright: ignore

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

        for _, _, fpath, _ in ino.event_gen(yield_nones=False):  # pyright: ignore
            func = {crawl_fpath: crawl_conv, warc2zim_fpath: warc2zim_conv}.get(fpath)
            if not func:
                continue
            # open input and output separatly as to not clear output on error
            with open(fpath) as ifh:
                try:
                    out = func(json.load(ifh), limit)
                except Exception:  # nosec # noqa: S112
                    # simply ignore progress update should an error arise
                    # might be malformed input for instance
                    continue
                if not out:
                    continue
                with open(output_fpath, "w") as ofh:
                    json.dump(out, ofh)


def run(raw_args):
    parser = ArgumentParser(
        description="Run a browser-based crawl on the specified URL and convert to ZIM"
    )

    parser.add_argument("-u", "--url", help="The URL to start crawling from")
    parser.add_argument("--title", help="ZIM title")
    parser.add_argument("--description", help="ZIM description")
    parser.add_argument("--long-description", help="ZIM long description metadata")

    parser.add_argument(
        "--urlFile",
        help="If set, read a list of seed urls, one per line, from the specified",
    )

    parser.add_argument("-w", "--workers", type=int, help="Number of parallel workers")

    parser.add_argument(
        "--waitUntil",
        help="Puppeteer page.goto() condition to wait for before continuing. One of "
        "load, domcontentloaded, networkidle0 or networkidle2, or a "
        "comma-separated combination of those.",
        default="load",
    )

    parser.add_argument(
        "--depth", help="The depth of the crawl for all seeds", type=int, default=-1
    )

    parser.add_argument(
        "--extraHops",
        help="Number of extra 'hops' to follow, beyond the current scope",
        type=int,
    )

    parser.add_argument("--limit", help="Limit crawl to this number of pages", type=int)

    parser.add_argument(
        "--maxPageLimit",
        help="Maximum pages to crawl, overriding pageLimit if both are set",
        type=int,
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
        "--lang",
        help="if set, sets the language used by the browser, should be ISO 639 "
        "language[-country] code",
    )

    parser.add_argument(
        "--zim-lang",
        help="Language metadata of ZIM "
        "(warc2zim --lang param). ISO-639-3 code. "
        "Retrieved from homepage if found, fallback to `eng`",
    )

    parser.add_argument(
        "--mobileDevice",
        help="Emulate mobile device by name from "
        "https://github.com/puppeteer/puppeteer/blob/"
        "main/packages/puppeteer-core/src/common/Device.ts",
        default="Pixel 2",
    )

    parser.add_argument(
        "--noMobileDevice",
        help="Do not emulate a mobile device (use at your own risk, behavior is"
        "uncertain)",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--userAgent",
        help="Override default user-agent with specified value ; --userAgentSuffix and "
        "--adminEmail have no effect when this is set",
    )

    parser.add_argument(
        "--userAgentSuffix",
        help="Append suffix to existing browser user-agent "
        "(ex: +MyCrawler, info@example.com)",
        default="+Zimit",
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
    )

    parser.add_argument(
        "--profile",
        help="Path or HTTP(S) URL to tar.gz file which contains the browser profile "
        "directory",
    )

    parser.add_argument(
        "--sizeLimit",
        help="If set, save state and exit if size limit exceeds this value",
        type=int,
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
    )

    parser.add_argument(
        "--healthCheckPort",
        help="port to run healthcheck on",
        type=int,
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

    parser.add_argument("--output", help="Output directory for ZIM", default="/output")

    parser.add_argument(
        "--build",
        help="Build directory for WARC files (if not set, output directory is used)",
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

    parser.add_argument(
        "--version",
        help="Display scraper version and exit",
        action="version",
        version=f"Zimit {__version__}",
    )

    parser.add_argument(
        "--logging",
        help="Crawler logging configuration",
    )

    parser.add_argument(
        "--custom-behaviors",
        help="JS code for custom behaviors to customize crawler. Single string with "
        "individual JS files URL/path separated by a comma",
    )

    parser.add_argument(
        "--warcs",
        help="Directly convert WARC archives to ZIM, by-passing the crawling phase. "
        "This argument must contain the path or HTTP(S) URL to either warc.gz files or"
        "to a tar.gz containing the warc.gz files. Single value with individual "
        "path/URLs separated by comma",
    )

    zimit_args, warc2zim_args = parser.parse_known_args(raw_args)

    # pass a scraper suffix to warc2zim so that both zimit and warc2zim versions are
    # associated with the ZIM ; make it a CSV for easier parsing
    warc2zim_args.append("--scraper-suffix")
    warc2zim_args.append(f"zimit {__version__}")

    # pass url and output to warc2zim also
    if zimit_args.output:
        warc2zim_args.append("--output")
        warc2zim_args.append(zimit_args.output)

    url = zimit_args.url

    user_agent_suffix = zimit_args.userAgentSuffix
    if zimit_args.adminEmail:
        user_agent_suffix += f" {zimit_args.adminEmail}"

    if url:
        url = get_cleaned_url(url)
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

    if zimit_args.long_description:
        warc2zim_args.append("--long-description")
        warc2zim_args.append(zimit_args.long_description)

    if zimit_args.zim_lang:
        warc2zim_args.append("--lang")
        warc2zim_args.append(zimit_args.zim_lang)

    logger.info("----------")
    logger.info("Testing warc2zim args")
    logger.info("Running: warc2zim " + " ".join(warc2zim_args))
    res = warc2zim(warc2zim_args)
    if res != NORMAL_WARC2ZIM_EXIT_CODE:
        logger.info("Exiting, invalid warc2zim params")
        return EXIT_CODE_WARC2ZIM_CHECK_FAILED

    # make temp dir for this crawl
    if zimit_args.build:
        temp_root_dir = Path(tempfile.mkdtemp(dir=zimit_args.build, prefix=".tmp"))
    else:
        temp_root_dir = Path(tempfile.mkdtemp(dir=zimit_args.output, prefix=".tmp"))

    if not zimit_args.keep:

        def cleanup():
            logger.info("")
            logger.info("----------")
            logger.info(f"Cleanup, removing temp dir: {temp_root_dir}")
            shutil.rmtree(temp_root_dir)

        atexit.register(cleanup)

    # copy / download custom behaviors to one single folder and configure crawler
    if zimit_args.custom_behaviors:
        behaviors_dir = temp_root_dir / "custom-behaviors"
        behaviors_dir.mkdir()
        for custom_behavior in [
            custom_behavior.strip()
            for custom_behavior in zimit_args.custom_behaviors.split(",")
        ]:
            behaviors_file = tempfile.NamedTemporaryFile(
                dir=behaviors_dir,
                prefix="behavior_",
                suffix=".js",
                delete_on_close=False,
            )
            if re.match(r"^https?\://", custom_behavior):
                logger.info(
                    f"Downloading browser profile from {custom_behavior} "
                    f"to {behaviors_file.name}"
                )
                resp = requests.get(custom_behavior, timeout=REQUESTS_TIMEOUT)
                resp.raise_for_status()
                Path(behaviors_file.name).write_bytes(resp.content)
            else:
                logger.info(
                    f"Copying browser profile from {custom_behavior} "
                    f"to {behaviors_file.name}"
                )
                shutil.copy(custom_behavior, behaviors_file.name)
        zimit_args.customBehaviors = str(behaviors_dir)
    else:
        zimit_args.customBehaviors = None

    cmd_args = get_node_cmd_line(zimit_args)
    if url:
        cmd_args.append("--url")
        cmd_args.append(url)

    cmd_args.append("--userAgentSuffix")
    cmd_args.append(user_agent_suffix)

    if not zimit_args.noMobileDevice:
        cmd_args.append("--mobileDevice")
        cmd_args.append(zimit_args.mobileDevice)

    cmd_args.append("--cwd")
    cmd_args.append(str(temp_root_dir))

    # setup inotify crawler progress watcher
    if zimit_args.statsFilename:
        watcher = ProgressFileWatcher(
            Path(zimit_args.output), Path(zimit_args.statsFilename)
        )
        logger.info(f"Writing progress to {watcher.stats_path}")
        # update crawler command
        cmd_args.append("--statsFilename")
        cmd_args.append(str(watcher.crawl_path))
        # update warc2zim command
        warc2zim_args.append("-v")
        warc2zim_args.append("--progress-file")
        warc2zim_args.append(str(watcher.warc2zim_path))
        watcher.watch()

    cmd_line = " ".join(cmd_args)

    logger.info("")
    logger.info("----------")
    logger.info(
        f"Output to tempdir: {temp_root_dir} - "
        f"{'will keep' if zimit_args.keep else 'will delete'}"
    )

    # if warc files are passed, do not run browsertrix crawler but fetch the files if
    # they are provided as an HTTP URL + extract the archive if it is a tar.gz
    warc_files: list[Path] = []
    if zimit_args.warcs:
        for warc_location in [
            warc_location.strip() for warc_location in zimit_args.warcs.split(",")
        ]:
            suffix = "".join(Path(urllib.parse.urlparse(warc_location).path).suffixes)
            if suffix not in {".tar.gz", ".warc", ".warc.gz"}:
                raise Exception(f"Unsupported file at {warc_location}")

            filename = tempfile.NamedTemporaryFile(
                dir=temp_root_dir,
                prefix="warc_",
                suffix=suffix,
                delete_on_close=False,
            )

            if not re.match(r"^https?\://", warc_location):
                # warc_location is not a URL, so it is a path, simply add it to the list
                if not Path(warc_location).exists():
                    raise Exception(f"Impossible to find file at {warc_location}")

                # if it is a plain warc or warc.gz, simply add it to the list
                if suffix in {".warc", ".warc.gz"}:
                    warc_files.append(Path(warc_location))
                    continue

                # otherwise extract tar.gz but do not delete it afterwards
                extract_path = temp_root_dir / f"{filename.name}_files"
                logger.info(
                    f"Extracting WARC(s) from {warc_location} to {extract_path}"
                )
                with tarfile.open(warc_location, "r:gz") as fh:
                    # Extract all the contents to the specified directory
                    fh.extractall(path=extract_path, filter="data")
                warc_files.append(Path(extract_path))
                continue

            # warc_location is a URL, let's download it to a temp name to avoid name
            # collisions
            warc_file = Path(filename.name)
            logger.info(f"Downloading WARC(s) from {warc_location} to {warc_file}")
            resp = requests.get(warc_location, timeout=REQUESTS_TIMEOUT)
            resp.raise_for_status()
            warc_file.write_bytes(resp.content)

            # if it is a plain warc or warc.gz, simply add it to the list
            if suffix in {".warc", ".warc.gz"}:
                warc_files.append(warc_file)
                continue

            # otherwise extract tar.gz and delete it afterwards
            extract_path = temp_root_dir / f"{filename.name}_files"
            logger.info(f"Extracting WARC(s) from {warc_file} to {extract_path}")
            with tarfile.open(warc_file, "r:gz") as fh:
                # Extract all the contents to the specified directory
                fh.extractall(path=extract_path, filter="data")
            logger.info(f"Deleting archive at {warc_file}")
            warc_file.unlink()
            warc_files.append(Path(extract_path))

    else:

        logger.info(f"Running browsertrix-crawler crawl: {cmd_line}")
        crawl = subprocess.run(cmd_args, check=False)
        if crawl.returncode == EXIT_CODE_CRAWLER_LIMIT_HIT:
            logger.info("crawl interupted by a limit")
        elif crawl.returncode != 0:
            raise subprocess.CalledProcessError(crawl.returncode, cmd_args)

        if zimit_args.collection:
            warc_files = [
                temp_root_dir.joinpath(f"collections/{zimit_args.collection}/archive/")
            ]

        else:
            warc_dirs = list(temp_root_dir.rglob("collections/crawl-*/archive/"))
            if len(warc_dirs) == 0:
                raise RuntimeError(
                    "Failed to find directory where WARC files have been created"
                )
            elif len(warc_dirs) > 1:
                logger.info(
                    "Found many WARC files directories, only last one will be used"
                )
                for directory in warc_dirs:
                    logger.info(f"- {directory}")
            warc_files = [warc_dirs[-1]]

    logger.info("")
    logger.info("----------")
    logger.info(
        f"Processing WARC files in/at "
        f'{" ".join(str(warc_file) for warc_file in warc_files)}'
    )
    warc2zim_args.extend(str(warc_file) for warc_file in warc_files)

    logger.info(f"Calling warc2zim with these args: {warc2zim_args}")

    return warc2zim(warc2zim_args)


def get_cleaned_url(url: str):
    parsed_url = urllib.parse.urlparse(url)

    # remove explicit port in URI for default-for-scheme as browsers does it
    if parsed_url.scheme == "https" and parsed_url.port == 443:  # noqa: PLR2004
        parsed_url = rebuild_uri(parsed_url, port="")
    if parsed_url.scheme == "http" and parsed_url.port == 80:  # noqa: PLR2004
        parsed_url = rebuild_uri(parsed_url, port="")

    return parsed_url.geturl()


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
        "lang",
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
        "logging",
        "customBehaviors",
    ]:
        value = getattr(args, arg)
        if arg == "userAgent":
            # - strip leading whitespace which are not allowed on some websites
            # - strip trailing whitespace which are either not allowed if no suffix is
            # used, or duplicate with the automatically added one if a suffix is there
            # - value is None when userAgent is not passed
            if value:
                value = value.strip()
            if not value:
                # ignore empty userAgent arg and keep crawler default value if empty
                continue
        if value is None or (isinstance(value, bool) and value is False):
            continue
        node_cmd.append("--" + arg)
        if not isinstance(value, bool):
            node_cmd.append(str(value))

    return node_cmd


def sigint_handler(*args):  # noqa: ARG001
    logger.info("")
    logger.info("")
    logger.info("SIGINT/SIGTERM received, stopping zimit")
    logger.info("")
    logger.info("")
    sys.exit(3)


def zimit():
    run(sys.argv[1:])


signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)


if __name__ == "__main__":
    zimit()
