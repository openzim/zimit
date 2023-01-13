## Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (as of version 1.2.0).


## [Unreleased]

### Added

- Initial url check normalizes homepage redirects to standart ports – 80/443 (#137)

### Changed

- Using warc2zim version xxx ⚠️ use released warc2zim before releasing
- Using browsertrix-crawler 0.8.0-beta.0
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
