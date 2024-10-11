## Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (as of version 1.2.0).

## [Unreleased]

### Changed

- Upgrade to browsertrix crawler 1.3.3 (#411)

## [2.1.3] - 2024-10-08

### Changed

- Upgrade to browsertrix crawler 1.3.2, warc2zim 2.1.2 and other dependencies (#406)

### Fixed

- Fix help (#393)

## [2.1.2] - 2024-09-09

### Changed

- Upgrade to browsertrix crawler 1.3.0-beta.1 (#387) (fixes "Ziming a website with huge assets (e.g. PDFs) is failing to proceed" - #380)

## [2.1.1] - 2024-09-05

### Added

- Add support for uncompressed tar archive in --warcs (#369)

### Changed

- Upgrade to browsertrix crawler 1.3.0-beta.0 (#379), including upgrage to Ubuntu Noble (#307)

### Fixed

- Stream files downloads to not exhaust memory (#373)
- Fix documentation on `--diskUtilization` setting (#375)

## [2.1.0] - 2024-08-09

### Added

- Add `--custom-behaviors` argument to support path/HTTP(S) URL custom behaviors to pass to the crawler (#313)
- Add daily automated end-to-end tests of a page with Youtube player (#330)
- Add `--warcs` option to directly process WARC files (#301)

### Changed

- Make it clear that `--profile` argument can be an HTTP(S) URL (and not only a path) (#288)
- Fix README imprecisions + add back warc2zim availability in docker image (#314)
- Enhance integration test to assert final content of the ZIM (#287)
- Stop fetching and passing browsertrix crawler version as scraperSuffix to warc2zim (#354)
- Do not log number of WARC files found (#357)
- Upgrade dependencies (warc2zim 2.1.0)

### Fixed

- Sort WARC directories found by modification time (#366)

## [2.0.6] - 2024-08-02

### Changed

- Upgraded Browsertrix Crawler to 1.2.6

## [2.0.5] - 2024-07-24

### Changed

- Upgraded Browsertrix Crawler to 1.2.5
- Upgraded warc2zim to 2.0.3

## [2.0.4] - 2024-07-15

### Changed

- Upgraded Browsertrix Crawler to 1.2.4 (fixes retrieve automatically the assets present in a data-xxx tag #316)

## [2.0.3] - 2024-06-24

### Changed

- Upgraded Browsertrix Crawler to 1.2.0 (fixes Youtube videos issue #323)

## [2.0.2] - 2024-06-18

### Changed

- Upgrade dependencies (mainly warc2zim 2.0.2)


## [2.0.1] - 2024-06-13

### Changed

- Upgrade dependencies (especially warc2zim 2.0.1 and browsertrix crawler 1.2.0-beta.0) (#318)

### Fixed

- Crawler is not correctly checking disk size / usage (#305)

## [2.0.0] - 2024-06-04

### Added

- New `--version` flag to display Zimit version (#234)
- New `--logging` flag to adjust Browsertrix Crawler logging (#273)
- Use new `--scraper-suffix` flag of warc2zim to enhance ZIM "Scraper" metadata (#275)
- New `--noMobileDevice` CLI argument
- Publish Docker image for `linux/arm64` (in addition to `linux/amd64`) (#178)

### Changed

- **Use `warc2zim` version 2**, which works without Service Worker anymore (#193)
- Upgraded Browsertrix Crawler to 1.1.3
- Adopt Python bootstrap conventions
- Upgrade to Python 3.12 + upgrade dependencies
- Removed handling of redirects by zimit, they are handled by browsertrix crawler and detected properly by warc2zim (#284)
- Drop initial check of URL in Python (#256)
- `--userAgent` CLI argument overrides again the `--userAgentSuffix` and `--adminEmail` values
- `--userAgent` CLI arguement is not mandatory anymore

### Fixed

- Fix support for Youtube videos (#291)
- Fix crawler `--waitUntil` values (#289)

## [1.6.3] - 2024-01-18

### Changed

- Adapt to new `warc2zim` code structure
- Using browsertrix-crawler 0.12.4
- Using warc2zim 1.5.5

### Added

- New `--build` parameter (optional) to specify the directory holding Browsertrix files ; if not set, `--output`
directory is used ; zimit creates one subdir of this folder per invocation to isolate datasets ; subdir is kept only
if `--keep` is set.

### Fixed

- `--collection` parameter was not working (#252)

## [1.6.2] - 2023-11-17

### Changed

- Using browsertrix-crawler 0.12.3

### Fixed

- Fix logic passing args to crawler to support value '0' (#245)
- Fix documentation about Chrome and headless (#248)

## [1.6.1] - 2023-11-06

### Changed

- Using browsertrix-crawler 0.12.1

## [1.6.0] - 2023-11-02

### Changed

- Scraper fails for all HTTP error codes returned when checking URL at startup (#223)
- User-Agent now has a default value (#228)
- Manipulation of spaces with UA suffix and adminEmail has been modified
- Same User-Agent is used for check_url (Python) and Browsertrix crawler (#227)
- Using browsertrix-crawler 0.12.0

## [1.5.3] - 2023-10-02

### Changed

- Using browsertrix-crawler 0.11.2

## [1.5.2] - 2023-09-19

### Changed

- Using browsertrix-crawler 0.11.1

## [1.5.1] - 2023-09-18

### Changed

- Using browsertrix-crawler 0.11.0
- Scraper stat file is not created empty (#211)
- Crawler statistics are not available anymore (#213)
- Using warc2zim 1.5.4

## [1.5.0] - 2023-08-23

### Added

- `--long-description` param

## [1.4.1] - 2023-08-23

### Changed

- Using browsertrix-crawler 0.10.4
- Using warc2zim 1.5.3

## [1.4.0] - 2023-08-02

### Added

- `--title` to set ZIM title
- `--description` to set ZIM description
- New crawler options: `--maxPageLimit`, `--delay`, `--diskUtilization`
- `--zim-lang` param to set warc2zim's `--lang` (ISO-639-3)

### Changed

- Using browsertrix-crawler 0.10.2
- Default and accepted values for `--waitUntil` from crawler's update
- Using warc2zim 1.5.2
- Disabled Chrome updates to prevent incidental inclusion of update data in WARC/ZIM (#172)
- `--failOnFailedSeed` used inconditionally
- `--lang` now passed to crawler (ISO-639-1)

### Removed

- `--newContext` from crawler's update

## [1.3.1] - 2023-02-06

### Changed

- Using browsertrix-crawler 0.8.0
- Using warc2zim version 1.5.1 with wabac.js 2.15.2

## [1.3.0] - 2023-02-02

### Added

- Initial url check normalizes homepage redirects to standart ports – 80/443 (#137)

### Changed

- Using warc2zim version 1.5.0 with scope conflict fix and videos fix
- Using browsertrix-crawler 0.8.0-beta.1
- Fixed `--allowHashUrls` being a boolean param
- Increased `check_url` timeout (12s to connect, 27s to read) instead of 10s

## [1.2.0] - 2022-06-21

### Added

- `--urlFile` browsertrix crawler parameter
- `--depth` browsertrix crawler parameter
- `--extraHops`, parameter
- `--collection` browsertrix crawler parameter
- `--allowHashUrls` browsertrix crawler parameter
- `--userAgentSuffix` browsertrix crawler parameter
- `--behaviors`, parameter
- `--behaviorTimeout` browsertrix crawler parameter
- `--profile` browsertrix crawler parameter
- `--sizeLimit` browsertrix crawler parameter
- `--timeLimit` browsertrix crawler parameter
- `--healthCheckPort`, parameter
- `--overwrite` parameter

### Changed

- using browsertrix-crawler `0.6.0` and warc2zim `1.4.2`
- default WARC location after crawl changed
from `collections/capture-*/archive/` to `collections/crawl-*/archive/`

### Removed

- `--scroll` browsertrix crawler parameter (see `--behaviors`)
- `--scope` browsertrix crawler parameter (see `--scopeType`, `--include` and `--exclude`)


## [1.1.5]

- using crawler 0.3.2 and warc2zim 1.3.6

## [1.1.4]

- Defaults to `load,networkidle0` for waitUntil param (same as crawler)
- Allows setting combinations of values for waitUntil param
- Updated warc2zim to 1.3.5
- Updated browsertrix-crawler to 0.3.1
- Warc to zim now written to `{temp_root_dir}/collections/capture-*/archive/` where
  `capture-*` is dynamic and includes the datetime. (from browsertrix-crawler)

## [1.1.3]

- allows same first-level-domain redirects
- fixed redirects to URL in scope
- updated crawler to 0.2.0
- `statsFilename` now informs whether limit was hit or not

## [1.1.2]

- added support for --custom-css
- added domains block list (dfault)

## [1.1.1]

- updated browsertrix-crawler to 0.1.4
  - autofetcher script to be injected by defaultDriver to capture srcsets + URLs in dynamically added stylesheets

## [1.0]

- initial version using browsertrix-crawler:0.1.3 and warc2zim:1.3.3
