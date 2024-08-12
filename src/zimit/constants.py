import logging

from zimscraperlib.logging import getLogger

EXIT_CODE_WARC2ZIM_CHECK_FAILED = 2
EXIT_CODE_CRAWLER_LIMIT_HIT = 11
NORMAL_WARC2ZIM_EXIT_CODE = 100
REQUESTS_TIMEOUT = 10

logger = getLogger(name="zimit", level=logging.INFO)
