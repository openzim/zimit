"""
Main zimit run script
This script validates arguments with warc2zim, checks permissions
and then calls the Node based driver
"""

import atexit
import json
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
from warc2zim.main import main as warc2zim
from zimscraperlib.uri import rebuild_uri

from zimit.__about__ import __version__
from zimit.constants import (
    EXIT_CODE_CRAWLER_SIZE_LIMIT_HIT,
    EXIT_CODE_CRAWLER_TIME_LIMIT_HIT,
    EXIT_CODE_WARC2ZIM_CHECK_FAILED,
    NORMAL_WARC2ZIM_EXIT_CODE,
    logger,
)
from zimit.utils import download_file

temp_root_dir: Path | None = None


class ProgressFileWatcher:
    def __init__(
        self, crawl_stats_path: Path, warc2zim_stats_path, zimit_stats_path: Path
    ):
        self.crawl_stats_path = crawl_stats_path
        self.warc2zim_stats_path = warc2zim_stats_path
        self.zimit_stats_path = zimit_stats_path

        # touch them all so inotify is not unhappy on add_watch
        self.crawl_stats_path.touch()
        self.warc2zim_stats_path.touch()
        self.process = None

    def stop(self):
        if not self.process:
            return
        self.process.join(0.1)
        self.process.terminate()

    def watch(self):
        self.process = Process(
            target=self.inotify_watcher,
            args=(
                str(self.crawl_stats_path),
                str(self.warc2zim_stats_path),
                str(self.zimit_stats_path),
            ),
        )
        self.process.daemon = True
        self.process.start()

    def inotify_watcher(self, crawl_fpath: str, warc2zim_fpath: str, zimit_fpath: str):
        ino = inotify.adapters.Inotify()
        ino.add_watch(crawl_fpath, inotify.constants.IN_MODIFY)  # pyright: ignore
        ino.add_watch(warc2zim_fpath, inotify.constants.IN_MODIFY)  # pyright: ignore

        def crawl_conv(data):
            # we consider crawl to be 90% of the workload so total = craw_total * 90%
            return {
                "done": data["crawled"],
                "total": int(data["total"] / 0.9),
            }

        def warc2zim_conv(data):
            # we consider warc2zim to be 10% of the workload so
            # warc2zim_total = 10% and  total = 90 + warc2zim_total * 10%
            return {
                "done": int(
                    data["total"]
                    * (0.9 + (float(data["written"]) / data["total"]) / 10)
                ),
                "total": data["total"],
            }

        for _, _, fpath, _ in ino.event_gen(yield_nones=False):  # pyright: ignore
            func = {crawl_fpath: crawl_conv, warc2zim_fpath: warc2zim_conv}.get(fpath)
            if not func:
                continue
            # open input and output separatly as to not clear output on error
            with open(fpath) as ifh:
                try:
                    out = func(json.load(ifh))
                except Exception:  # nosec # noqa: S112
                    # simply ignore progress update should an error arise
                    # might be malformed input for instance
                    continue
                if not out:
                    continue
                with open(zimit_fpath, "w") as ofh:
                    json.dump(out, ofh)


def cleanup():
    if not temp_root_dir:
        logger.warning("Temporary root dir not already set, cannot clean this up")
        return
    logger.info("")
    logger.info("----------")
    logger.info(f"Cleanup, removing temp dir: {temp_root_dir}")
    shutil.rmtree(temp_root_dir)


def cancel_cleanup():
    logger.info(
        f"Temporary files have been kept in {temp_root_dir}, please clean them"
        " up manually once you don't need them anymore"
    )
    atexit.unregister(cleanup)


def run(raw_args):
    parser = ArgumentParser(
        description="Run a browser-based crawl on the specified URL and convert to ZIM"
    )

    parser.add_argument(
        "--seeds",
        help="The seed URL(s) to start crawling from. Multile seed URL must be "
        "separated by a comma (usually not needed, these are just the crawl seeds). "
        "First seed URL is used as ZIM homepage",
    )

    parser.add_argument("--title", help="WARC and ZIM title")
    parser.add_argument("--description", help="WARC and ZIM description")
    parser.add_argument("--long-description", help="ZIM long description metadata")

    parser.add_argument(
        "--seedFile",
        help="If set, read a list of seed urls, one per line. Can be a local file or "
        "the HTTP(s) URL to an online file.",
    )

    parser.add_argument(
        "-w", "--workers", type=int, help="Number of parallel workers. Default is 1."
    )

    parser.add_argument(
        "--crawlId",
        help="A user provided ID for this crawl or crawl configuration (can also be "
        "set via CRAWL_ID env var, defaults to machine hostname)",
    )

    parser.add_argument(
        "--waitUntil",
        help="Puppeteer page.goto() condition to wait for before continuing. One of "
        "load, domcontentloaded, networkidle0 or networkidle2, or a "
        "comma-separated combination of those. Default is load,networkidle2",
    )

    parser.add_argument(
        "--depth",
        help="The depth of the crawl for all seeds. Default is -1 (infinite).",
        type=int,
    )

    parser.add_argument(
        "--extraHops",
        help="Number of extra 'hops' to follow, beyond the current scope. "
        "Default is 0.",
        type=int,
    )

    parser.add_argument(
        "--pageLimit",
        help="Limit crawl to this number of pages. Default is 0 (no limit).",
        type=int,
    )

    parser.add_argument(
        "--maxPageLimit",
        help="Maximum pages to crawl, overriding pageLimit if both are set. Default is "
        "0 (no limit)",
        type=int,
    )

    parser.add_argument(
        "--pageLoadTimeout",
        help="Timeout for each page to load (in seconds). Default is 90 secs.",
        type=int,
    )

    parser.add_argument(
        "--scopeType",
        help="A predfined scope of the crawl. For more customization, "
        "use 'custom' and set scopeIncludeRx/scopeExcludeRx regexes. Default is custom"
        "if scopeIncludeRx is set, prefix otherwise.",
        choices=["page", "page-spa", "prefix", "host", "domain", "any", "custom"],
    )

    parser.add_argument(
        "--scopeIncludeRx",
        help="Regex of page URLs that should be included in the crawl (defaults to "
        "the immediate directory of URL)",
    )

    parser.add_argument(
        "--scopeExcludeRx",
        help="Regex of page URLs that should be excluded from the crawl",
    )

    parser.add_argument(
        "--allowHashUrls",
        help="Allow Hashtag URLs, useful for single-page-application crawling or "
        "when different hashtags load dynamic content",
        action="store_true",
    )

    parser.add_argument(
        "--selectLinks",
        help="One or more selectors for extracting links, in the format "
        "[css selector]->[property to use],[css selector]->@[attribute to use]",
    )

    parser.add_argument(
        "--clickSelector",
        help="Selector for elements to click when using the autoclick behavior. Default"
        " is 'a'",
    )

    parser.add_argument(
        "--blockRules",
        help="Additional rules for blocking certain URLs from being loaded, by URL "
        "regex and optionally via text match in an iframe",
    )

    parser.add_argument(
        "--blockMessage",
        help="If specified, when a URL is blocked, a record with this error message is"
        " added instead",
    )

    parser.add_argument(
        "--blockAds",
        help="If set, block advertisements from being loaded (based on Stephen Black's"
        " blocklist). Note that some bad domains are also blocked by zimit"
        " configuration even if this option is not set.",
    )

    parser.add_argument(
        "--adBlockMessage",
        help="If specified, when an ad is blocked, a record with this error message is"
        " added instead",
    )

    parser.add_argument(
        "--collection",
        help="Collection name to crawl to (replay will be accessible "
        "under this name in pywb preview). Default is crawl-@ts.",
    )

    parser.add_argument(
        "--headless",
        help="Run in headless mode, otherwise start xvfb",
        action="store_true",
    )

    parser.add_argument(
        "--driver",
        help="Custom driver for the crawler, if any",
    )

    parser.add_argument(
        "--generateCDX",
        help="If set, generate index (CDXJ) for use with pywb after crawl is done",
        action="store_true",
    )

    parser.add_argument(
        "--combineWARC",
        help="If set, combine the warcs",
        action="store_true",
    )

    parser.add_argument(
        "--rolloverSize",
        help="If set, declare the rollover size. Default is 1000000000.",
        type=int,
    )

    parser.add_argument(
        "--generateWACZ",
        help="If set, generate WACZ on disk",
        action="store_true",
    )

    parser.add_argument(
        "--logging",
        help="Crawler logging configuration",
    )

    parser.add_argument(
        "--logLevel",
        help="Comma-separated list of log levels to include in logs",
    )

    parser.add_argument(
        "--logContext",
        help="Comma-separated list of contexts to include in logs",
        choices=[
            "general",
            "worker",
            "recorder",
            "recorderNetwork",
            "writer",
            "state",
            "redis",
            "storage",
            "text",
            "exclusion",
            "screenshots",
            "screencast",
            "originOverride",
            "healthcheck",
            "browser",
            "blocking",
            "behavior",
            "behaviorScript",
            "jsError",
            "fetch",
            "pageStatus",
            "memoryStatus",
            "crawlStatus",
            "links",
            "sitemap",
            "wacz",
            "replay",
            "proxy",
        ],
    )

    parser.add_argument(
        "--logExcludeContext",
        help="Comma-separated list of contexts to NOT include in logs. Default is "
        "recorderNetwork,jsError,screencast",
        choices=[
            "general",
            "worker",
            "recorder",
            "recorderNetwork",
            "writer",
            "state",
            "redis",
            "storage",
            "text",
            "exclusion",
            "screenshots",
            "screencast",
            "originOverride",
            "healthcheck",
            "browser",
            "blocking",
            "behavior",
            "behaviorScript",
            "jsError",
            "fetch",
            "pageStatus",
            "memoryStatus",
            "crawlStatus",
            "links",
            "sitemap",
            "wacz",
            "replay",
            "proxy",
        ],
    )

    parser.add_argument(
        "--text",
        help="Extract initial (default) or final text to pages.jsonl or WARC resource"
        " record(s)",
    )

    # cwd is manipulated directly by zimit, based on --output / --build, we do not want
    # to expose this setting

    parser.add_argument(
        "--mobileDevice",
        help="Emulate mobile device by name from "
        "https://github.com/puppeteer/puppeteer/blob/"
        "main/packages/puppeteer-core/src/common/Device.ts",
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
        "--sitemapFromDate",
        help="If set, filter URLs from sitemaps to those greater than or equal to (>=)"
        " provided ISO Date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or partial date)",
    )

    parser.add_argument(
        "--sitemapToDate",
        help="If set, filter URLs from sitemaps to those less than or equal to (<=) "
        "provided ISO Date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or partial date)",
    )

    parser.add_argument(
        "--statsFilename",
        help="If set, output crawl stats as JSON to this file. Relative filename "
        "resolves to output directory, see --output.",
    )

    parser.add_argument(
        "--zimit-progress-file",
        help="If set, output zimit stats as JSON to this file. Forces the creation of"
        "crawler and warc2zim stats as well. If --statsFilename and/or "
        "--warc2zim-progress-file are not set, default temporary files will be used. "
        "Relative filename resolves to output directory, see --output.",
    )

    parser.add_argument(
        "--warc2zim-progress-file",
        help="If set, output warc2zim stats as JSON to this file. Relative filename "
        "resolves to output directory, see --output.",
    )

    parser.add_argument(
        "--behaviors",
        help="Which background behaviors to enable on each page. Default is autoplay,"
        "autofetch,autoscroll,siteSpecific",
    )

    parser.add_argument(
        "--behaviorTimeout",
        help="If >0, timeout (in seconds) for in-page behavior will run on each page. "
        "If 0, a behavior can run until finish. Default is 90.",
        type=int,
    )

    parser.add_argument(
        "--postLoadDelay",
        help="If >0, amount of time to sleep (in seconds) after page has loaded, before"
        " taking screenshots / getting text / running behaviors. Default is 0.",
        type=int,
    )

    parser.add_argument(
        "--pageExtraDelay",
        help="If >0, amount of time to sleep (in seconds) after behaviors "
        "before moving on to next page. Default is 0.",
        type=int,
    )

    parser.add_argument(
        "--dedupPolicy",
        help="Deduplication policy. Default is skip",
        choices=["skip", "revisit", "keep"],
    )

    parser.add_argument(
        "--profile",
        help="Path or HTTP(S) URL to tar.gz file which contains the browser profile "
        "directory",
    )

    parser.add_argument(
        "--screenshot",
        help="Screenshot options for crawler. One of view, thumbnail, fullPage, "
        "fullPageFinal or a comma-separated combination of those.",
    )

    parser.add_argument(
        "--screencastPort",
        help="If set to a non-zero value, starts an HTTP server with screencast "
        "accessible on this port.",
        type=int,
    )

    parser.add_argument(
        "--screencastRedis",
        help="If set, will use the state store redis pubsub for screencasting",
        action="store_true",
    )

    parser.add_argument(
        "--warcInfo",
        help="Optional fields added to the warcinfo record in combined WARCs",
    )

    parser.add_argument(
        "--saveState",
        help="If the crawl state should be serialized to the crawls/ directory. "
        "Defaults to 'partial', only saved when crawl is interrupted",
        choices=["never", "partial", "always"],
    )

    parser.add_argument(
        "--saveStateInterval",
        help="If save state is set to 'always', also save state during the crawl at "
        "this interval (in seconds). Default to 300.",
        type=int,
    )

    parser.add_argument(
        "--saveStateHistory",
        help="Number of save states to keep during the duration of a crawl. "
        "Default to 5.",
        type=int,
    )

    size_group = parser.add_mutually_exclusive_group()
    size_group.add_argument(
        "--sizeSoftLimit",
        help="If set, save crawl state and stop crawl if WARC size exceeds this value. "
        "ZIM will still be created.",
        type=int,
    )
    size_group.add_argument(
        "--sizeHardLimit",
        help="If set, exit crawler and fail the scraper immediately if WARC size "
        "exceeds this value",
        type=int,
    )

    parser.add_argument(
        "--diskUtilization",
        help="Save state and exit if disk utilization exceeds this percentage value."
        " Default (if not set) is 90%%. Set to 0 to disable disk utilization check.",
        type=int,
        default=90,
    )

    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument(
        "--timeSoftLimit",
        help="If set, save crawl state and stop crawl if WARC WARC(s) creation takes "
        "longer than this value, in seconds. ZIM will still be created.",
        type=int,
    )
    time_group.add_argument(
        "--timeHardLimit",
        help="If set, exit crawler and fail the scraper immediately if WARC(s) creation"
        " takes longer than this value, in seconds",
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
    )

    parser.add_argument(
        "--waitOnDone",
        help="if set, wait for interrupt signal when finished instead of exiting",
        action="store_true",
    )

    parser.add_argument(
        "--restartsOnError",
        help="if set, assume will be restarted if interrupted, don't run post-crawl "
        "processes on interrupt",
        action="store_true",
    )

    parser.add_argument(
        "--netIdleWait",
        help="If set, wait for network idle after page load and after behaviors are "
        "done (in seconds). if -1 (default), determine based on scope.",
        type=int,
    )

    parser.add_argument(
        "--lang",
        help="if set, sets the language used by the browser, should be ISO 639 "
        "language[-country] code",
    )

    parser.add_argument(
        "--originOverride",
        help="if set, will redirect requests from each origin in key to origin in the "
        "value, eg. --originOverride https://host:port=http://alt-host:alt-port",
    )

    parser.add_argument(
        "--logErrorsToRedis",
        help="If set, write error messages to redis",
        action="store_true",
    )

    parser.add_argument(
        "--writePagesToRedis",
        help="If set, write page objects to redis",
        action="store_true",
    )

    parser.add_argument(
        "--maxPageRetries",
        help="If set, number of times to retry a page that failed to load before page"
        " is considered to have failed. Default is 2.",
        type=int,
    )

    parser.add_argument(
        "--failOnFailedSeed",
        help="If set, crawler will fail with exit code 1 if any seed fails. When "
        "combined with --failOnInvalidStatus, will result in crawl failing with exit "
        "code 1 if any seed has a 4xx/5xx response",
        action="store_true",
    )

    parser.add_argument(
        "--failOnFailedLimit",
        help="If set, save state and exit if number of failed pages exceeds this value",
        action="store_true",
    )

    parser.add_argument(
        "--failOnInvalidStatus",
        help="If set, will treat pages with 4xx or 5xx response as failures. When "
        "combined with --failOnFailedLimit or --failOnFailedSeed may result in crawl "
        "failing due to non-200 responses",
        action="store_true",
    )

    # customBehaviors not included because it has special handling
    # debugAccessRedis not included due to custom redis engine in zimit

    parser.add_argument(
        "--debugAccessBrowser",
        help="if set, allow debugging browser on port 9222 via CDP",
        action="store_true",
    )

    parser.add_argument(
        "--warcPrefix",
        help="prefix for WARC files generated, including WARCs added to WACZ",
    )

    parser.add_argument(
        "--serviceWorker",
        help="service worker handling: disabled, enabled or disabled-if-profile. "
        "Default: disabled.",
    )

    parser.add_argument(
        "--proxyServer",
        help="if set, will use specified proxy server. Takes precedence over any env "
        "var proxy settings",
    )

    parser.add_argument(
        "--dryRun",
        help="If true, no archive data is written to disk, only pages and logs (and "
        "optionally saved state).",
        action="store_true",
    )

    parser.add_argument(
        "--qaSource",
        help="Required for QA mode. Path to the source WACZ or multi WACZ file for QA",
    )

    parser.add_argument(
        "--qaDebugImageDiff",
        help="if specified, will write crawl.png, replay.png and diff.png for each "
        "page where they're different",
        action="store_true",
    )

    parser.add_argument(
        "--sshProxyPrivateKeyFile",
        help="path to SSH private key for SOCKS5 over SSH proxy connection",
    )

    parser.add_argument(
        "--sshProxyKnownHostsFile",
        help="path to SSH known hosts file for SOCKS5 over SSH proxy connection",
    )

    parser.add_argument(
        "--keep",
        help="In case of failure, WARC files and other temporary files (which are "
        "stored as a subfolder of output directory) are always kept, otherwise "
        "they are automatically deleted. Use this flag to always keep WARC files, "
        "even in case of success.",
        action="store_true",
    )

    parser.add_argument(
        "--output",
        help="Output directory for ZIM. Default to /output.",
        default="/output",
    )

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
        "--zim-lang",
        help="Language metadata of ZIM "
        "(warc2zim --lang param). ISO-639-3 code. "
        "Retrieved from homepage if found, fallback to `eng`",
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
        "to a tar or tar.gz containing the warc.gz files. Single value with individual "
        "path/URLs separated by comma",
    )

    parser.add_argument(
        "--acceptable-crawler-exit-codes",
        help="Non-zero crawler exit codes to consider as acceptable to continue with "
        " conversion of WARC to ZIM. Flag partialZim will be set in statsFilename (if "
        " used). Single value with individual error codes separated by comma",
    )

    # by design, all unknown args are for warc2zim ; known one are either for crawler
    # or shared
    known_args, warc2zim_args = parser.parse_known_args(raw_args)

    # pass a scraper suffix to warc2zim so that both zimit and warc2zim versions are
    # associated with the ZIM ; make it a CSV for easier parsing
    warc2zim_args.append("--scraper-suffix")
    warc2zim_args.append(f"zimit {__version__}")

    # pass url and output to warc2zim also
    if known_args.output:
        warc2zim_args.append("--output")
        warc2zim_args.append(known_args.output)

    user_agent_suffix = known_args.userAgentSuffix
    if known_args.adminEmail:
        user_agent_suffix += f" {known_args.adminEmail}"

    # set temp dir to use for this crawl
    global temp_root_dir  # noqa: PLW0603
    if known_args.build:
        # use build dir argument if passed
        temp_root_dir = Path(known_args.build)
        temp_root_dir.mkdir(parents=True, exist_ok=True)
    else:
        # make new randomized temp dir
        temp_root_dir = Path(tempfile.mkdtemp(dir=known_args.output, prefix=".tmp"))

    seeds = []
    if known_args.seeds:
        seeds += [get_cleaned_url(url) for url in known_args.seeds.split(",")]
    if known_args.seedFile:
        if re.match(r"^https?\://", known_args.seedFile):
            with tempfile.NamedTemporaryFile(
                dir=temp_root_dir,
                prefix="seeds_",
                suffix=".txt",
                delete_on_close=True,
            ) as filename:
                seed_file = Path(filename.name)
                download_file(known_args.seedFile, seed_file)
                seeds += [
                    get_cleaned_url(url) for url in seed_file.read_text().splitlines()
                ]
        else:
            seeds += [
                get_cleaned_url(url)
                for url in Path(known_args.seedFile).read_text().splitlines()
            ]
    warc2zim_args.append("--url")
    warc2zim_args.append(seeds[0])

    if known_args.custom_css:
        warc2zim_args += ["--custom-css", known_args.custom_css]

    if known_args.title:
        warc2zim_args.append("--title")
        warc2zim_args.append(known_args.title)

    if known_args.description:
        warc2zim_args.append("--description")
        warc2zim_args.append(known_args.description)

    if known_args.long_description:
        warc2zim_args.append("--long-description")
        warc2zim_args.append(known_args.long_description)

    if known_args.zim_lang:
        warc2zim_args.append("--lang")
        warc2zim_args.append(known_args.zim_lang)

    logger.info("----------")
    logger.info("Testing warc2zim args")
    logger.info("Running: warc2zim " + " ".join(warc2zim_args))
    res = warc2zim(warc2zim_args)
    if res != NORMAL_WARC2ZIM_EXIT_CODE:
        logger.info("Exiting, invalid warc2zim params")
        return EXIT_CODE_WARC2ZIM_CHECK_FAILED

    # only trigger cleanup when the keep argument is passed without a custom build dir.
    if not known_args.build and not known_args.keep:
        atexit.register(cleanup)

    # copy / download custom behaviors to one single folder and configure crawler
    if known_args.custom_behaviors:
        behaviors_dir = temp_root_dir / "custom-behaviors"
        behaviors_dir.mkdir()
        for custom_behavior in [
            custom_behavior.strip()
            for custom_behavior in known_args.custom_behaviors.split(",")
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
                download_file(custom_behavior, Path(behaviors_file.name))
            else:
                logger.info(
                    f"Copying browser profile from {custom_behavior} "
                    f"to {behaviors_file.name}"
                )
                shutil.copy(custom_behavior, behaviors_file.name)
        known_args.customBehaviors = str(behaviors_dir)
    else:
        known_args.customBehaviors = None

    crawler_args = get_crawler_cmd_line(known_args)
    for seed in seeds:
        crawler_args.append("--seeds")
        crawler_args.append(seed)

    crawler_args.append("--userAgentSuffix")
    crawler_args.append(user_agent_suffix)

    crawler_args.append("--cwd")
    crawler_args.append(str(temp_root_dir))

    output_dir = Path(known_args.output)
    warc2zim_stats_file = (
        Path(known_args.warc2zim_progress_file)
        if known_args.warc2zim_progress_file
        else temp_root_dir / "warc2zim.json"
    )
    if not warc2zim_stats_file.is_absolute():
        warc2zim_stats_file = output_dir / warc2zim_stats_file
        warc2zim_stats_file.parent.mkdir(parents=True, exist_ok=True)
    warc2zim_stats_file.unlink(missing_ok=True)

    crawler_stats_file = (
        Path(known_args.statsFilename)
        if known_args.statsFilename
        else temp_root_dir / "crawl.json"
    )
    if not crawler_stats_file.is_absolute():
        crawler_stats_file = output_dir / crawler_stats_file
        crawler_stats_file.parent.mkdir(parents=True, exist_ok=True)
    crawler_stats_file.unlink(missing_ok=True)

    zimit_stats_file = (
        Path(known_args.zimit_progress_file)
        if known_args.zimit_progress_file
        else temp_root_dir / "stats.json"
    )
    if not zimit_stats_file.is_absolute():
        zimit_stats_file = output_dir / zimit_stats_file
        zimit_stats_file.parent.mkdir(parents=True, exist_ok=True)
    zimit_stats_file.unlink(missing_ok=True)

    if known_args.zimit_progress_file:
        # setup inotify crawler progress watcher
        watcher = ProgressFileWatcher(
            zimit_stats_path=zimit_stats_file,
            crawl_stats_path=crawler_stats_file,
            warc2zim_stats_path=warc2zim_stats_file,
        )
        logger.info(
            f"Writing zimit progress to {watcher.zimit_stats_path}, crawler progress to"
            f" {watcher.crawl_stats_path} and warc2zim progress to "
            f"{watcher.warc2zim_stats_path}"
        )
        # update crawler command
        crawler_args.append("--statsFilename")
        crawler_args.append(str(crawler_stats_file))
        # update warc2zim command
        warc2zim_args.append("-v")
        warc2zim_args.append("--progress-file")
        warc2zim_args.append(str(warc2zim_stats_file))
        watcher.watch()
    else:
        if known_args.statsFilename:
            logger.info(f"Writing crawler progress to {crawler_stats_file}")
            crawler_args.append("--statsFilename")
            crawler_args.append(str(crawler_stats_file))
        if known_args.warc2zim_progress_file:
            logger.info(f"Writing warc2zim progress to {warc2zim_stats_file}")
            warc2zim_args.append("-v")
            warc2zim_args.append("--progress-file")
            warc2zim_args.append(str(warc2zim_stats_file))

    cmd_line = " ".join(crawler_args)

    logger.info("")
    logger.info("----------")
    logger.info(
        f"Output to tempdir: {temp_root_dir} - "
        f"{'will keep' if known_args.keep else 'will delete'}"
    )

    partial_zim = False

    # if warc files are passed, do not run browsertrix crawler but fetch the files if
    # they are provided as an HTTP URL + extract the archive if it is a tar.gz
    warc_files: list[Path] = []
    if known_args.warcs:
        for warc_location in [
            warc_location.strip() for warc_location in known_args.warcs.split(",")
        ]:
            suffix = "".join(Path(urllib.parse.urlparse(warc_location).path).suffixes)
            if suffix not in {".tar", ".tar.gz", ".warc", ".warc.gz"}:
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
                with tarfile.open(warc_location, "r") as fh:
                    # Extract all the contents to the specified directory
                    fh.extractall(path=extract_path, filter="data")
                warc_files.append(Path(extract_path))
                continue

            # warc_location is a URL, let's download it to a temp name to avoid name
            # collisions
            warc_file = Path(filename.name)
            logger.info(f"Downloading WARC(s) from {warc_location} to {warc_file}")
            download_file(warc_location, warc_file)

            # if it is a plain warc or warc.gz, simply add it to the list
            if suffix in {".warc", ".warc.gz"}:
                warc_files.append(warc_file)
                continue

            # otherwise extract tar.gz and delete it afterwards
            extract_path = temp_root_dir / f"{filename.name}_files"
            logger.info(f"Extracting WARC(s) from {warc_file} to {extract_path}")
            with tarfile.open(warc_file, "r") as fh:
                # Extract all the contents to the specified directory
                fh.extractall(path=extract_path, filter="data")
            logger.info(f"Deleting archive at {warc_file}")
            warc_file.unlink()
            warc_files.append(Path(extract_path))

    else:

        logger.info(f"Running browsertrix-crawler crawl: {cmd_line}")
        crawl = subprocess.run(crawler_args, check=False)
        if (
            crawl.returncode == EXIT_CODE_CRAWLER_SIZE_LIMIT_HIT
            and known_args.sizeSoftLimit
        ):
            logger.info(
                "Crawl size soft limit hit. Continuing with warc2zim conversion."
            )
            if known_args.zimit_progress_file:
                partial_zim = True
        elif (
            crawl.returncode == EXIT_CODE_CRAWLER_TIME_LIMIT_HIT
            and known_args.timeSoftLimit
        ):
            logger.info(
                "Crawl time soft limit hit. Continuing with warc2zim conversion."
            )
            if known_args.zimit_progress_file:
                partial_zim = True
        elif crawl.returncode != 0:
            logger.error(
                f"Crawl returned an error: {crawl.returncode}, scraper exiting"
            )
            cancel_cleanup()
            return crawl.returncode

        if known_args.collection:
            warc_files = [
                temp_root_dir.joinpath(f"collections/{known_args.collection}/archive/")
            ]

        else:
            warc_dirs = sorted(
                temp_root_dir.rglob("collections/crawl-*/archive/"),
                key=lambda path: path.lstat().st_mtime,
            )
            if len(warc_dirs) == 0:
                raise RuntimeError(
                    "Failed to find directory where WARC files have been created"
                )
            elif len(warc_dirs) > 1:
                logger.info(
                    "Found many WARC files directories, combining pages from all of them"
                )
                for directory in warc_dirs:
                    logger.info(f"- {directory}")
            warc_files = warc_dirs

    logger.info("")
    logger.info("----------")
    logger.info(
        f"Processing WARC files in/at "
        f'{" ".join(str(warc_file) for warc_file in warc_files)}'
    )
    warc2zim_args.extend(str(warc_file) for warc_file in warc_files)

    logger.info(f"Calling warc2zim with these args: {warc2zim_args}")

    warc2zim_exit_code = warc2zim(warc2zim_args)

    if known_args.zimit_progress_file:
        stats_content = json.loads(zimit_stats_file.read_bytes())
        stats_content["partialZim"] = partial_zim
        zimit_stats_file.write_text(json.dumps(stats_content))

    # also call cancel_cleanup when --keep, even if it is not supposed to be registered,
    # so that we will display temporary files location just like in other situations
    if warc2zim_exit_code or known_args.keep:
        cancel_cleanup()

    return warc2zim_exit_code


def get_cleaned_url(url: str):
    parsed_url = urllib.parse.urlparse(url)

    # remove explicit port in URI for default-for-scheme as browsers does it
    if parsed_url.scheme == "https" and parsed_url.port == 443:  # noqa: PLR2004
        parsed_url = rebuild_uri(parsed_url, port="")
    if parsed_url.scheme == "http" and parsed_url.port == 80:  # noqa: PLR2004
        parsed_url = rebuild_uri(parsed_url, port="")

    return parsed_url.geturl()


def get_crawler_cmd_line(args):
    """Build the command line for Browsertrix crawler"""
    node_cmd = ["crawl"]
    for arg in [
        "title",
        "description",
        "workers",
        "crawlId",
        "waitUntil",
        "depth",
        "extraHops",
        "pageLimit",
        "maxPageLimit",
        "pageLoadTimeout",
        "scopeType",
        "scopeIncludeRx",
        "scopeExcludeRx",
        "collection",
        "allowHashUrls",
        "selectLinks",
        "clickSelector",
        "blockRules",
        "blockMessage",
        "blockAds",
        "adBlockMessage",
        "collection",
        "headless",
        "driver",
        "generateCDX",
        "combineWARC",
        "rolloverSize",
        "generateWACZ",
        "logging",
        "logLevel",
        "logContext",
        "logExcludeContext",
        "text",
        "mobileDevice",
        "userAgent",
        # userAgentSuffix (manipulated),
        "useSitemap",
        "sitemapFromDate",
        "sitemapToDate",
        # statsFilename (manipulated),
        "behaviors",
        "behaviorTimeout",
        "postLoadDelay",
        "pageExtraDelay",
        "dedupPolicy",
        "profile",
        "screenshot",
        "screencastPort",
        "screencastRedis",
        "warcInfo",
        "saveState",
        "saveStateInterval",
        "saveStateHistory",
        "sizeSoftLimit",
        "sizeHardLimit",
        "diskUtilization",
        "timeSoftLimit",
        "timeHardLimit",
        "healthCheckPort",
        "overwrite",
        "waitOnDone",
        "restartsOnError",
        "netIdleWait",
        "lang",
        "originOverride",
        "logErrorsToRedis",
        "writePagesToRedis",
        "maxPageRetries",
        "failOnFailedSeed",
        "failOnFailedLimit",
        "failOnInvalidStatus",
        "debugAccessBrowser",
        "warcPrefix",
        "serviceWorker",
        "proxyServer",
        "dryRun",
        "qaSource",
        "qaDebugImageDiff",
        "sshProxyPrivateKeyFile",
        "sshProxyKnownHostsFile",
        "customBehaviors",
        "config",
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
        node_cmd.append(
            "--"
            + (
                "sizeLimit"
                if arg in ["sizeSoftLimit", "sizeHardLimit"]
                else "timeLimit" if arg in ["timeSoftLimit", "timeHardLimit"] else arg
            )
        )
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
    sys.exit(run(sys.argv[1:]))


signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)


if __name__ == "__main__":
    zimit()
