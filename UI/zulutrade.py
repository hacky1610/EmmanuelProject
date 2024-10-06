import re
from datetime import datetime
import time
import pandas as pd
from bs4 import BeautifulSoup
from pandas import DataFrame
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Tracing.Tracer import Tracer


class ZuluTradeUI:

    def __init__(self, driver: WebDriver, tracer: Tracer):
        self._driver = driver
        self._tracer = tracer

    def login(self):
        self._driver.get("https://www.zulutrade.com/login")
        wait = WebDriverWait(self._driver, 4)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "login-content")))

        login_form = self._driver.find_element(By.CLASS_NAME, "login-content")
        inputs = login_form.find_elements(By.TAG_NAME, "input")
        inputs[0].send_keys("daniel.hackbarth@siemens.com")
        inputs[1].send_keys("Daytona1610!")
        login = self._driver.find_element(By.CLASS_NAME, "fillBtn")
        login.click()
        time.sleep(5)

    def close(self):
        self._driver.close()

    def _open_portfolio(self, trader_id: str):
        self._driver.get(f"https://www.zulutrade.com/trader/{trader_id}/trading?t=30&m=1")
        tabs = self._driver.find_element(By.ID, "tabs-nav")
        portfolio = tabs.find_elements(By.TAG_NAME, "li")[1]
        portfolio.click()

    def get_user_statistic(self, trader_id: str):
        self._open_portfolio(trader_id)

        footer = self._driver.find_element(By.CLASS_NAME, "tableFooter")
        select = footer.find_element(By.TAG_NAME, "select")
        select.find_elements(By.TAG_NAME, "option")[3].click()

        time.sleep(4)

        success = self._driver.find_elements(By.CLASS_NAME, "success1")
        fails = self._driver.find_elements(By.CLASS_NAME, "error1")

        result = 0
        for el in success:
            result += float(re.search(r"\d+\.\d+", el.text)[0])

        for el in fails:
            result -= float(re.search(r"\d+\.\d+", el.text)[0])

        return result

    def get_leaders(self):

        self._driver.get("https://www.zulutrade.com/traders/list/75932")
        tabs = self._driver.find_element(By.CLASS_NAME, "zuluTabs")
        links = tabs.find_elements(By.TAG_NAME, "a")

        leaders = []

        for link in links:
            link.click()
            leaders += self._read_leader_grid()

        return leaders

    def _read_leader_grid(self):
        leader_cards = self._driver.find_elements(By.CLASS_NAME, "card-body")

        leaders = []

        for leader_card in leader_cards:
            _id = ""
            links = leader_card.find_elements(By.TAG_NAME, "a")
            for link in links:
                r = re.search(r"https:\/\/www\.zulutrade\.com\/trader\/(\d+)\/trading", link.get_attribute("href"))
                if r is not None:
                    _id = r.groups()[0]
            if _id != "":
                name = leader_card.find_element(By.TAG_NAME, "h6")
                leaders.append({"id": _id, "name": name.text})

        return leaders

    def get_my_open_positions(self) -> DataFrame:
        self._driver.get("https://www.zulutrade.com/dashboard")
        time.sleep(10)
        page_source = self._driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        table = soup.find("table", {"id": "example"})
        rows = table.findAll("tr")[1:]

        data = []
        for row in rows:
            cols = row.findAll("td")
            position_text = cols[0].text.strip()

            r = re.search(r"([A-Z]{3}\/[A-Z]{3})\s*(\d\d \w{3} \d{4}, \d\d:\d\d \w\w)\s*(\w{3,4})", position_text)
            if r:
                ticker, open_time_str, direction = r.groups()
                ticker = ticker.replace("/", "")
                open_time = datetime.strptime(open_time_str, '%d %b %Y, %I:%M %p')

                position_id = f"{ticker}_{direction}_{cols[1].text}_{open_time.isoformat()}"
                data.append({
                    "position_id": position_id,
                    "ticker": ticker,
                    "time": open_time,
                    "direction": direction,
                    "trader_name": cols[1].text,
                    "lots": cols[2].text,
                    "units": cols[3].text,
                    "open_price": cols[4].text
                })

        df = pd.DataFrame(data)
        return df

    def get_my_closed_positions(self) -> DataFrame:
        self._driver.get("https://www.zulutrade.com/dashboard")
        time.sleep(7)
        self._tracer.debug("opened dashboard")
        tabs_nav = self._driver.find_elements(By.ID, "tabs-nav")[1]
        tabs = tabs_nav.find_elements(By.TAG_NAME, "li")
        self._tracer.debug("Try to close modal")
        btn_close = self._driver.find_element(By.CLASS_NAME, "btn-close")
        if btn_close is not None:
            btn_close.click()
        time.sleep(4)
        self._tracer.debug("modal closed")

        trial = 0
        while trial < 5:
            try:
                tabs[2].click()
                break
            except Exception as ex:
                trial += 1
                self._tracer.warning(f"Error during open closed {ex}")
        self._tracer.debug("switched to closed pos")

        time.sleep(5)
        page_source = self._driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        rows = soup.findAll("table", {"class": "megaDropInnerTable"})

        data = []
        for row in rows:
            self._tracer.debug("iter row start")
            cols = row.findAll("td")
            r = re.search(r"([A-Z]{3}\/[A-Z]{3})\s*(\d\d \w{3} \d{4}, \d\d:\d\d \w\w)\s*(\w{3,4})",
                          cols[0].text)
            ticker, open_time, direction = r.groups()
            ticker = ticker.replace("/", "")
            open_time = datetime.strptime(open_time, '%d %b %Y, %I:%M %p')
            position_id = f"{ticker}_{direction}_{cols[1].text}_{open_time.isoformat()}"

            data.append([position_id,
                         ticker,
                         open_time,
                         direction,
                         cols[1].text,
                         cols[2].text,
                         cols[3].text,
                         cols[4].text])
            self._tracer.debug("iter row end")

        columns = ["position_id", "ticker", "time", "direction", "trader_name", "profit", "open_date", "close_date"]
        df = pd.DataFrame(data, columns=columns)
        return df