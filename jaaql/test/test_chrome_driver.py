"""
The email service starts its Chrome (DrivenChrome) with the image's chromedriver named, so that Selenium Manager never runs in the
image: it would look the driver up on every Chrome start, sending usage statistics to plausible.io and waiting on the network when there
is none. Outside the image, where there is no /usr/local/bin/chromedriver, Selenium Manager still finds the driver.

    python -m unittest jaaql.test.test_chrome_driver

The unit tests stand in for Chrome and need only the package's requirements. TestChromeInTheImage starts the real Chrome as the email
service does and prints a page to PDF; it runs only where the image's chromedriver and Chrome are installed
"""
import os
import shutil
import unittest
from unittest import mock

from selenium.webdriver.common import driver_finder

from jaaql.email import email_manager_service
from jaaql.email.email_manager_service import DrivenChrome, PATH__image_chromedriver


def driven_chrome():
    # A DrivenChrome without the threads its constructor starts: initialize_chrome_driver needs only these
    chrome = DrivenChrome.__new__(DrivenChrome)
    chrome.is_deployed = True
    chrome.page_load_timeout = 20
    chrome.render_timeout = 60
    return chrome


class TestChromeDriverService(unittest.TestCase):
    def service_started_with(self, image_driver_exists):
        real_exists = os.path.exists
        exists = lambda path: image_driver_exists if path == PATH__image_chromedriver else real_exists(path)
        with mock.patch.object(email_manager_service.webdriver, "Chrome") as chrome, mock.patch("os.path.exists", exists):
            driven_chrome().initialize_chrome_driver()
        return chrome.call_args.kwargs["service"]

    def test_in_the_image_its_driver_is_named(self):
        self.assertEqual(self.service_started_with(image_driver_exists=True).path, PATH__image_chromedriver)

    def test_outside_the_image_selenium_manager_finds_the_driver(self):
        self.assertFalse(self.service_started_with(image_driver_exists=False).path)


@unittest.skipUnless(os.path.exists(PATH__image_chromedriver) and shutil.which("google-chrome"),
                     "runs where the image's chromedriver and Chrome are installed")
class TestChromeInTheImage(unittest.TestCase):
    def test_chrome_starts_without_selenium_manager_and_prints_a_pdf(self):
        chrome = driven_chrome()
        with mock.patch.object(driver_finder.SeleniumManager, "binary_paths", side_effect=AssertionError("Selenium Manager ran")):
            chrome.initialize_chrome_driver()
        try:
            chrome.driver.get("data:text/html,<p>JAAQL</p>")
            pdf = chrome.driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True})
            self.assertTrue(pdf["data"].startswith("JVBERi0"))  # base64 of %PDF-
        finally:
            chrome.driver.quit()


if __name__ == "__main__":
    unittest.main()
