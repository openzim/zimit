Zimit
=====

Zimit is a scraper allowing to create ZIM file from any Web site.

[![Docker](https://ghcr-badge.deta.dev/openzim/zimit/latest_tag?label=docker)](https://ghcr.io/openzim/zimit)
[![Build](https://github.com/openzim/zimit/workflows/CI/badge.svg?query=branch%3Amain)](https://github.com/openzim/zimit/actions?query=branch%3Amain)
[![CodeFactor](https://www.codefactor.io/repository/github/openzim/zimit/badge)](https://www.codefactor.io/repository/github/openzim/zimit)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

⚠️ **Important**: this tool uses [warc2zim](https://github.com/openzim/warc2zim) to create Zim files and thus require the Zim reader to support *Service Workers*. At the time of `zimit:1.0`, that's mostly kiwix-android and kiwix-serve. Note that service workers have protocol restrictions as well so you'll need to run it either from `localhost` or over HTTPS.

Technical background
--------------------

This version of Zimit runs a single-site headless-Chrome based crawl in a Docker container and produces a ZIM of the crawled content.

The system extends the crawling system in [Browsertrix Crawler](https://github.com/webrecorder/browsertrix-crawler) and converts
the crawled WARC files to ZIM using [warc2zim](https://github.com/openzim/warc2zim)

The `zimit.py` is the entrypoint for the system.

After the crawl is done, warc2zim is used to write a zim to the
`/output` directory, which can be mounted as a volume.

Using the `--keep` flag, the crawled WARCs will also be kept in a temp directory inside `/output`

Usage
-----

`zimit` is intended to be run in Docker.

To build locally run:

```bash
docker build -t ghcr.io/openzim/zimit .
```

The image accepts the following parameters, **as well as any of the [warc2zim](https://github.com/openzim/warc2zim) ones**; useful for setting metadata, for instance:

- `--url URL` - the url to be crawled (required)
- `--workers N` - number of crawl workers to be run in parallel
- `--wait-until` - Puppeteer setting for how long to wait for page load. See [page.goto waitUntil options](https://github.com/puppeteer/puppeteer/blob/main/docs/api.md#pagegotourl-options). The default is `load`, but for static sites, `--wait-until domcontentloaded` may be used to speed up the crawl (to avoid waiting for ads to load for example).
- `--name` - Name of ZIM file (defaults to the hostname of the URL)
- `--output` - output directory (defaults to `/output`)
- `--limit U` - Limit capture to at most U URLs
- `--exclude <regex>` - skip URLs that match the regex from crawling. Can be specified multiple times. An example is `--exclude="(\?q=|signup-landing\?|\?cid=)"`, where URLs that contain either `?q=` or `signup-landing?` or `?cid=` will be excluded. 
- `--scroll [N]` - if set, will activate a simple auto-scroll behavior on each page to scroll for upto N seconds
- `--keep` - if set, keep the WARC files in a temp directory inside the output directory

The following is an example usage. The `--shm-size` flags is [needed to run Chrome in Docker](https://github.com/puppeteer/puppeteer/blob/v1.0.0/docs/troubleshooting.md#tips).

Example command:

```bash
docker run ghcr.io/openzim/zimit zimit --help
docker run ghcr.io/openzim/zimit warc2zim --help
docker run  -v /output:/output \
       --shm-size=1gb ghcr.io/openzim/zimit zimit --url URL --name myzimfile --workers 2 --waitUntil domcontentloaded
```

The puppeteer-cluster provides monitoring output which is enabled by
default and prints the crawl status to the Docker log.

**Note**: Image automatically filters out a large number of ads by using the 3 blocklists from [anudeepND](https://github.com/anudeepND/blacklist). If you don't want this filtering, disable the image's entrypoint in your container (`docker run --entrypoint="" ghcr.io/openzim/zimit ...`).

Nota bene
---------

A first version of a generic HTTP scraper was created in 2016 during
the [Wikimania Esino Lario
Hackathon](https://wikimania2016.wikimedia.org/wiki/Programme/Kiwix-dedicated_Hackathon).

That version is now considered outdated and [archived in `2016`
branch](https://github.com/openzim/zimit/tree/2016).

License
-------

[GPLv3](https://www.gnu.org/licenses/gpl-3.0) or later, see
[LICENSE](LICENSE) for more details.
