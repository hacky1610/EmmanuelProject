import re
import time
import uuid
from datetime import datetime
import time
from pandas import DataFrame, Series
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from Connectors.trader_store import Trader
from selenium.webdriver.support import expected_conditions as EC


class ZuluTradeUI:

    def __init__(self, driver: WebDriver):
        self._driver = driver

    def login(self):
        self._driver.get("https://www.zulutrade.com/login")
        wait = WebDriverWait(self._driver, 4)
        wait.until(EC.presence_of_element_located((By.NAME, "username")))

        elem = self._driver.find_element(By.NAME, "username")
        elem.send_keys("daniel.hackbarth@siemens.com")
        elem = self._driver.find_element(By.NAME, "password")
        elem.send_keys("Daytona1610!")
        login = self._driver.find_element(By.CLASS_NAME, "fillBtn")
        login.click()
        time.sleep(5)

    def close(self):
        self._driver.close()

    def get_favorites(self):
        self._driver.get("https://www.zulutrade.com/watchlist")
        favs = []
        for fav_container in self._driver.find_elements(By.CLASS_NAME, "watchlist-col"):

            link = fav_container.find_element(By.CLASS_NAME, "rounded-circle").get_attribute("src")
            f = re.search("id=(\d+)",
                          link)
            if f != None:
                favs.append(Trader(id=f.groups()[0],
                                   name=fav_container.find_element(By.TAG_NAME, "a").text))
            else:
                print("Foo")

        return favs

    def _open_portfolio(self, id: str):
        self._driver.get(f"https://www.zulutrade.com/trader/{id}/trading?t=30&m=1")
        tabs = self._driver.find_element(By.ID, "tabs-nav")
        portfolio = tabs.find_elements(By.TAG_NAME, "li")[1]
        portfolio.click()

    def get_user_statistic(self, id: str):
        self._open_portfolio(id)

        footer = self._driver.find_element(By.CLASS_NAME, "tableFooter")
        select = footer.find_element(By.TAG_NAME, "select")
        select.find_elements(By.TAG_NAME, "option")[3].click()

        time.sleep(4)

        success = self._driver.find_elements(By.CLASS_NAME, "success1")
        fails = self._driver.find_elements(By.CLASS_NAME, "error1")

        result = 0
        for el in success:
            result += float(re.search("\d+\.\d+", el.text)[0])

        for el in fails:
            result -= float(re.search("\d+\.\d+", el.text)[0])

        return result

    def get_leaders(self):

        self._driver.get("https://www.zulutrade.com/traders/list/75932")
        tabs = self._driver.find_element(By.CLASS_NAME, "zuluTabs")
        links = tabs.find_elements(By.TAG_NAME,"a")

        leaders = []

        for l in links:
            l.click()
            leaders += self._read_leader_grid()

        return leaders

    def _read_leader_grid(self):
        leader_cards = self._driver.find_elements(By.CLASS_NAME, "card-body")

        leaders = []

        for leader_card in leader_cards:
            id = ""
            links = leader_card.find_elements(By.TAG_NAME,"a")
            for l in links:
                r = re.search("https:\/\/www\.zulutrade\.com\/trader\/(\d+)\/trading", l.get_attribute("href"))
                if r is not None:
                    id = r.groups()[0]
            if id != "":
                name =  a = leader_card.find_element(By.TAG_NAME,"h6")
                leaders.append({"id":id, "name":name.text})

        return leaders


    def get_my_open_positions(self) -> DataFrame:
        self._driver.get("https://www.zulutrade.com/dashboard")
        #time.sleep(4)
        table = self._driver.find_element(By.ID, "example")
        rows = table.find_elements(By.TAG_NAME, "tr")

        df = DataFrame()
        for row in rows[1:]:
            cols = row.find_elements(By.TAG_NAME, "td")
            r = re.search("([A-Z]{3}\/[A-Z]{3})\s(\d\d \w{3} \d{4}, \d\d:\d\d \w\w)\s(\w{3,4})",
                          cols[0].text)
            ticker = r.groups()[0].replace("/", "")
            opentime = datetime.strptime(r.groups()[1], '%d %b %Y, %I:%M %p')
            direction = r.groups()[2]
            position_id = f"{ticker}_{direction}_{cols[1].text}_{opentime.isoformat()}"
            df = df.append(Series(data=[position_id,
                                        ticker,
                                        opentime,
                                        direction,
                                        cols[1].text,
                                        cols[2].text,
                                        cols[3].text,
                                        cols[4].text],
                                  index=["position_id",
                                         "ticker",
                                         "time",
                                         "direction",
                                         "trader_name",
                                         "lots",
                                         "units",
                                         "open_price"]),
                           ignore_index=True)
        return df

    def get_my_closed_positions(self) -> DataFrame:
        self._driver.get("https://www.zulutrade.com/dashboard")
        time.sleep(7)
        tabs_nav = self._driver.find_elements(By.ID,"tabs-nav")[1]
        tabs = tabs_nav.find_elements(By.TAG_NAME,"li")

        btn_close = self._driver.find_element(By.CLASS_NAME, "btn-close")
        if btn_close is not None:
            btn_close.click()
        time.sleep(4)

        while True:
            try:
                tabs[2].click()
                break
            except:
                pass

        time.sleep(5)
        rows = self._driver.find_elements(By.CLASS_NAME, "megaDropInnerTable")

        df = DataFrame()
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            r = re.search("([A-Z]{3}\/[A-Z]{3})\s(\d\d \w{3} \d{4}, \d\d:\d\d \w\w)\s(\w{3,4})",
                          cols[0].text)
            ticker = r.groups()[0].replace("/", "")
            opentime = datetime.strptime(r.groups()[1], '%d %b %Y, %I:%M %p')
            direction = r.groups()[2]
            position_id = f"{ticker}_{direction}_{cols[1].text}_{opentime.isoformat()}"
            df = df.append(Series(data=[position_id,
                                        ticker,
                                        opentime,
                                        direction,
                                        cols[1].text,
                                        cols[2].text,
                                        cols[3].text,
                                        cols[4].text],
                                  index=["position_id",
                                         "ticker",
                                         "time",
                                         "direction",
                                         "trader_name",
                                         "profit",
                                         "open_date",
                                         "close_date"]),
                           ignore_index=True)
        return df
