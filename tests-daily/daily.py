import logging
import os
import subprocess
from time import sleep

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

KIWIX_SERVE_START_SLEEP = 1

ZIM_NAME = "tests_eng_test-website"
YOUTUBE_VIDEO_PATH = "youtube.fuzzy.replayweb.page/embed/g5skcrNXdDM"

SKIP_YOUTUBE_TEST = os.getenv("SKIP_YOUTUBE_TEST", "False").lower() == "true"

CHECK_VIDEO_IS_PLAYING_AFTER_SECS = 30

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def chrome_driver():
    """Start chrome and setup chrome driver / selenium"""

    logger.info("Starting Chrome")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    # Other options of interest:
    # --disable-dev-shm-usage (not needed anymore with recent chrome versions)
    # --disable-gpu (important for some versions of Chrome)
    # --remote-debugging-port=9222 (should you need to remote debug)

    # Set path to Chrome binary
    chrome_options.binary_location = "/opt/chrome/chrome-linux64/chrome"

    # Set path to ChromeDriver
    chrome_service = ChromeService(
        executable_path="/opt/chromedriver/chromedriver-linux64/chromedriver"
    )

    # Set up driver
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    yield driver

    # Cleanup
    logger.info("Quitting Chrome")
    driver.quit()


@pytest.fixture(scope="module")
def kiwix_serve():
    """Start  kiwix-serve with given ZIM"""

    logger.info("Starting kiwix-serve")
    process = subprocess.Popen(
        [
            "/usr/bin/env",
            "/usr/local/bin/kiwix-serve",
            f"/output/{ZIM_NAME}.zim",
        ]
    )

    logger.info(
        f"Waiting {KIWIX_SERVE_START_SLEEP} secs to be 'sure' that kiwix-serve is ready"
    )
    sleep(KIWIX_SERVE_START_SLEEP)

    if process.poll() is not None:
        raise Exception("kiwix-serve has terminated too early")

    yield process

    # Cleanup
    logger.info("Quitting kiwix-serve")
    process.terminate()


@pytest.mark.skipif(SKIP_YOUTUBE_TEST, reason="Youtube test disabled by environment")
def test_youtube_video(chrome_driver, kiwix_serve):  # noqa: ARG001
    """Test that youtube video loads, and still plays after a while"""

    chrome_driver.get(f"http://localhost:80/content/{ZIM_NAME}/{YOUTUBE_VIDEO_PATH}")

    if chrome_driver.title == "Content not found":
        raise Exception("Wrong URL, kiwix-serve said that content is not found")

    button = WebDriverWait(chrome_driver, 1).until(
        expected_conditions.presence_of_element_located(
            (By.XPATH, "//button[@title='Play']")
        )
    )

    logger.info("Play button found in page")

    button.click()

    video = WebDriverWait(chrome_driver, 1).until(
        expected_conditions.presence_of_element_located((By.TAG_NAME, "video"))
    )

    logger.info("Video found in page")

    # arguments[0] is the video tag passed to execute_script
    if not chrome_driver.execute_script("return arguments[0].paused === false", video):
        raise Exception("Video is not playing, failed to start probably")

    logger.info("Video is playing")

    logger.info(
        f"Waiting {CHECK_VIDEO_IS_PLAYING_AFTER_SECS} secs to check video is still "
        "playing"
    )
    sleep(CHECK_VIDEO_IS_PLAYING_AFTER_SECS)

    # arguments[0] is the video tag passed to execute_script
    if not chrome_driver.execute_script("return arguments[0].paused === false", video):
        raise Exception(
            "Video is not playing anymore after "
            f"{CHECK_VIDEO_IS_PLAYING_AFTER_SECS} secs"
        )
    logger.info("Video is still playing")
