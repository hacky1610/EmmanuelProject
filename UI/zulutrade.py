import re
import time

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from BL.datatypes import OpenPosition
from Connectors.trader_store import Trader


class ZuluTradeUI:

    def __init__(self, driver:WebDriver):
        self._driver = driver

    def login(self):
        self._driver.get("https://www.zulutrade.com/login")
        elem = self._driver.find_element(By.NAME, "username")
        elem.send_keys("daniel.hackbarth@siemens.com")
        elem = self._driver.find_element(By.NAME, "password")
        elem.send_keys("Daytona1610!")
        login = self._driver.find_element(By.CLASS_NAME, "fillBtn")
        login.click()
        time.sleep(5)

    def get_favorites(self):
        self._driver.get("https://www.zulutrade.com/watchlist")
        favs = []
        for fav_container in self._driver.find_elements(By.CLASS_NAME, "watchlist-col"):

            link =fav_container.find_element(By.CLASS_NAME, "rounded-circle").get_attribute("src")
            f = re.search("id=(\d+)",
                          link)
            if f != None:
                favs.append(Trader(id=f.groups()[0],
                                name=fav_container.find_element(By.TAG_NAME, "a").text))


        return favs


    def get_open_positions(self, id: str):
        self._open_portfolio(id)

        overview = self._driver.find_element(By.CLASS_NAME, "overViewInvestors")
        nav = overview.find_element(By.ID, "tabs-nav")
        nav.find_elements(By.TAG_NAME, "li")[1].click()

        table = overview.find_element(By.CLASS_NAME , "currencyTable")
        rows = table.find_elements(By.TAG_NAME, "tr")

        open_positions = []
        for i in range(1, len(rows)):
            p = OpenPosition()
            columns = rows[i].find_elements(By.TAG_NAME,"td")
            p.TICKER = columns[0].text.replace("/","")
            p.TYPE = columns[1].text
            p.DATE_OPEN = columns[3].text
            open_positions.append(p)


        return open_positions



    def _open_portfolio(self, id:str):
        self._driver.get(f"https://www.zulutrade.com/trader/{id}/trading?t=30&m=1")
        tabs = self._driver.find_element(By.ID, "tabs-nav")
        portfolio = tabs.find_elements(By.TAG_NAME, "li")[1]
        portfolio.click()

    def get_user_statistic(self, id:str):
        self._open_portfolio(id)

        footer = self._driver.find_element(By.CLASS_NAME, "tableFooter")
        select = footer.find_element(By.TAG_NAME, "select")
        select.find_elements(By.TAG_NAME, "option")[3].click()

        time.sleep(4)

        success = self._driver.find_elements(By.CLASS_NAME, "success1")
        fails = self._driver.find_elements(By.CLASS_NAME, "error1")

        result = 0
        for el in success:
            result += float(re.search("\d+\.\d+",el.text)[0])

        for el in fails:
            result -= float(re.search("\d+\.\d+", el.text)[0])

        return result

