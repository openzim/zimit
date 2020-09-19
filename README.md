zimit
=====

This version of Zimit runs a single-site headless-Chrome based crawl in a Docker container and produces a ZIM of the crawled content.

The system uses:
 - `oldwebtoday/chrome` - to install a recent version of Chrome 84
 - `puppeteer-cluster` - for running Chrome browsers in parallel
 - `pywb` - in recording mode for capturing the content
 - `warc2zim` - to convert the crawled WARC files into a ZIM

The driver in `index.js` crawls a given URL using puppeteer-cluster.

After the crawl is done, warc2zim is used to write a zim to the `/output` directory, which can be mounted as a volume.

## Usage

`zimit` is intended to be run in Docker.

The following is an example usage. The `--cap-add` and `--shm-size` flags are needed for Chrome.

The image accepts the following parameters:

- "<URL>" - the url to be crawled (required)
- `--workers N` - number of crawl workers to be run in parallel
- `--wait-until` - Puppeteer setting for how long to wait for page load. See [page.goto waitUntil options](https://github.com/puppeteer/puppeteer/blob/main/docs/api.md#pagegotourl-options). The default is `load`, but for static sites, `--wait-until domcontentloaded` may be used to speed up the crawl (to avoid waiting for ads to load for example).
- `--name` - Name of ZIM file (defaults to the hostname of the URL)
- `--output` - output directory (defaults to `/output`)



Example command:

```
docker run  -v /output:/output --cap-add=SYS_ADMIN --cap-add=NET_ADMIN --shm-size=1gb openzim/zimit "<URL>" --name myzimfile --workers 2 --wait-until domcontentloaded
```

<hr>

## Previous version

A first version of a generic HTTP scraper was created in 2016 during the [Wikimania Esino Lario Hackathon](https://wikimania2016.wikimedia.org/wiki/Programme/Kiwix-dedicated_Hackathon).

That version is now considered outdated and [archived in `2016` branch](https://github.com/openzim/zimit/tree/2016).
