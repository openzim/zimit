Zimit
=====

Zimit is a scraper allowing to create [ZIM file](https://en.wikipedia.org/wiki/ZIM_(file_format)) from any Web site.

[![CodeFactor](https://www.codefactor.io/repository/github/openzim/zimit/badge)](https://www.codefactor.io/repository/github/openzim/zimit)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Docker](https://ghcr-badge.egpl.dev/openzim/zimit/latest_tag?label=docker)](https://ghcr.io/openzim/zimit)

Zimit adheres to openZIM's [Contribution Guidelines](https://github.com/openzim/overview/wiki/Contributing).

Zimit has implemented openZIM's [Python bootstrap, conventions and policies](https://github.com/openzim/_python-bootstrap/blob/main/docs/Policy.md) **v1.0.1**.

Capabilities and known limitations
--------------------

While we would like to support as many websites as possible, making an offline archive of any website with a versatile tool obviously has some limitations.

Most capabilities and known limitations are documented in [warc2zim README](https://github.com/openzim/warc2zim/blob/main/README.md). There are also some limitations in Browsertrix Crawler (used to fetch the website) and wombat (used to properly replay dynamic web requests), but these are not (yet?) clearly documented.

Technical background
--------------------

Zimit runs a fully automated browser-based crawl of a website property and produces a ZIM of the crawled content. Zimit runs in a Docker container.

The system:
- runs a website crawl with [Browsertrix Crawler](https://github.com/webrecorder/browsertrix-crawler), which produces WARC files
- converts the crawled WARC files to a single ZIM using [warc2zim](https://github.com/openzim/warc2zim)

The `zimit.py` is the entrypoint for the system.

After the crawl is done, warc2zim is used to write a zim to the `/output` directory, which should be mounted as a volume to not loose the ZIM created when container stops.

Using the `--keep` flag, the crawled WARCs and few other artifacts will also be kept in a temp directory inside `/output`

Usage
-----

`zimit` is intended to be run in Docker. Docker image is published at https://github.com/orgs/openzim/packages/container/package/zimit.

The image accepts the following parameters, **as well as any of the [Browsertrix crawler](https://crawler.docs.browsertrix.com/user-guide/cli-options/) and [warc2zim](https://github.com/openzim/warc2zim) ones**:

- Required: `--seeds URL` - the url to start crawling from ; multiple URLs can be separated by a comma (even if **usually not needed**, these are just the **seeds** of the crawl) ; first seed URL is used as ZIM homepage
- Required: `--name` - Name of ZIM file
- `--output` - output directory (defaults to `/output`)
- `--pageLimit U` - Limit capture to at most U URLs
- `--scopeExcludeRx <regex>` - skip URLs that match the regex from crawling. Can be specified multiple times. An example is `--scopeExcludeRx="(\?q=|signup-landing\?|\?cid=)"`, where URLs that contain either `?q=` or `signup-landing?` or `?cid=` will be excluded.
- `--workers N` - number of crawl workers to be run in parallel
- `--waitUntil` - Puppeteer setting for how long to wait for page load. See [page.goto waitUntil options](https://github.com/puppeteer/puppeteer/blob/main/docs/api.md#pagegotourl-options). The default is `load`, but for static sites, `--waitUntil domcontentloaded` may be used to speed up the crawl (to avoid waiting for ads to load for example).
- `--keep` - in case of failure, WARC files and other temporary files (which are stored as a subfolder of output directory) are always kept, otherwise they are automatically deleted. Use this flag to always keep WARC files, even in case of success.

Example command:

```bash
docker run ghcr.io/openzim/zimit zimit --help
docker run ghcr.io/openzim/zimit warc2zim --help
docker run  -v /output:/output ghcr.io/openzim/zimit zimit --seeds URL --name myzimfile
```

**Note**: Image automatically filters out a large number of ads by using the 3 blocklists from [anudeepND](https://github.com/anudeepND/blacklist). If you don't want this filtering, disable the image's entrypoint in your container (`docker run --entrypoint="" ghcr.io/openzim/zimit ...`).

To re-build the Docker image locally run:

```bash
docker build -t ghcr.io/openzim/zimit .
```

FAQ
---

The Zimit contributor's team maintains [a page with most Frequently Asked Questions](https://github.com/openzim/zimit/wiki/Frequently-Asked-Questions).

Nota bene
---------

While Zimit 1.x relied on a Service Worker to display the ZIM content, this is not anymore the case
since Zimit 2.x which does not have any special requirements anymore.

It should also be noted that a first version of a generic HTTP scraper was created in 2016 during
the [Wikimania Esino Lario
Hackathon](https://wikimania2016.wikimedia.org/wiki/Programme/Kiwix-dedicated_Hackathon).

That version is now considered outdated and [archived in `2016`
branch](https://github.com/openzim/zimit/tree/2016).

License
-------

[GPLv3](https://www.gnu.org/licenses/gpl-3.0) or later, see
[LICENSE](LICENSE) for more details.
