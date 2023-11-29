import re
import time
import uuid
from datetime import datetime
import time

import pandas as pd
from bs4 import BeautifulSoup
from pandas import DataFrame, Series
from selenium.common import StaleElementReferenceException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from Connectors.trader_store import Trader
from selenium.webdriver.support import expected_conditions as EC


class FxUi:

    def __init__(self, driver: WebDriver):
        self._driver = driver

    def close(self):
        self._driver.close()

    def get_stop(self, ticker: str):
        self._driver.get("https://widgets-m.techsubservices.com/calculators/loss-profit")
        self._driver.find_elements(By.CLASS_NAME, "select2-arrow")[0].click()
        list = self._driver.find_element(By.ID, "select2-results-1")
        list_elements = list.find_elements(By.TAG_NAME, "li")
        found = False
        for le in list_elements:
            if le.text == ticker:
                le.click()
                found = True
                break

        if not found:
            print(f"{ticker} not found")

        self._driver.find_element(By.CLASS_NAME, "button_blue").click()
        time.sleep(3)

        pips = self._driver.find_element(By.CLASS_NAME, "result-loss-pip").text

        value_str = re.search(r"\d+\.\d+", pips).group()
        value = float(value_str) / 100

        print(f"{ticker} - {value}")

        return value
