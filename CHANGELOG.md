# 1.1.4

- Defaults to `load,networkidle0` for waitUntil param (same as crawler)
- Allows setting combinations of values for waitUntil param
- Updated warc2zim to 1.3.5
- Updated browsertrix-crawler to 0.3.1
- Warc to zim now written to `{temp_root_dir}/collections/capture-*/archive/` where
  `capture-*` is dynamic and includes the datetime. (from browsertrix-crawler)

# 1.1.3

- allows same first-level-domain redirects
- fixed redirects to URL in scope
- updated crawler to 0.2.0
- `statsFilename` now informs whether limit was hit or not

# 1.1.2

- added support for --custom-css
- added domains block list (dfault)

# 1.1.1

- updated browsertrix-crawler to 0.1.4
  - autofetcher script to be injected by defaultDriver to capture srcsets + URLs in dynamically added stylesheets

# 1.0

- initial version using browsertrix-crawler:0.1.3 and warc2zim:1.3.3
