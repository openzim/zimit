## Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (as of version 1.2.0).

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
