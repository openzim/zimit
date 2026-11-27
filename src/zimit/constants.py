import logging

from zimscraperlib.logging import getLogger

# codes mirroring browsertrix-crawler's own ExitCodes enum (SizeLimit/TimeLimit),
# kept equal to the crawler's actual values so comparisons against its returncode
# stay meaningful ; not to be confused with zimit's own codes below
EXIT_CODE_CRAWLER_SIZE_LIMIT_HIT = 14
EXIT_CODE_CRAWLER_TIME_LIMIT_HIT = 15

# code returned by warc2zim itself (not zimit) when called with no inputs, used to
# validate warc2zim arguments early ; not a zimit-owned code
NORMAL_WARC2ZIM_EXIT_CODE = 100

# zimit's own exit codes, kept in a dedicated 100+ range so they never collide with
# browsertrix-crawler's own exit codes (0-22) or with NORMAL_WARC2ZIM_EXIT_CODE above
EXIT_CODE_WARC2ZIM_CHECK_FAILED = 101
EXIT_CODE_SIGINT_RECEIVED = 102
EXIT_CODE_WARC2ZIM_TEST_CRAWL_FAILED = 103

REQUESTS_TIMEOUT = 10

logger = getLogger(name="zimit", level=logging.INFO)
