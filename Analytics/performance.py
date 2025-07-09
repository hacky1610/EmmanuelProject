import pandas as pd
import requests
from datetime import datetime, timedelta
from collections import defaultdict

from BL import ConfigReader
from Connectors.IG import IG
from Connectors.tiingo import Tiingo


class FundamentalData:
    def __init__(self, raw_data: dict):
        self.date: str = raw_data.get('date', '')
        self.year: int = raw_data.get('year', 0)
        self.quarter: int = raw_data.get('quarter', 0)
        statement_data = raw_data.get('statementData', {})
        self.balanceSheet = self._parse_section(statement_data.get('balanceSheet', []))
        self.cashFlow = self._parse_section(statement_data.get('cashFlow', []))
        self.incomeStatement = self._parse_section(statement_data.get('incomeStatement', []))
        self.overview = self._parse_section(statement_data.get('overview', []))
        self.profit_margin = raw_data.get('profit_margin', None)

    def _parse_section(self, section_list):
        return {item['dataCode']: item['value'] for item in section_list if 'dataCode' in item}

    def __repr__(self):
        return f"<FundamentalData {self.year}Q{self.quarter} date={self.date}>"


class FundamentalAnalyzer:
    def __init__(self, ticker, api_key, period="quarter", years=1, max_date="2024-06-30"):
        self.ticker = ticker
        self.api_key = api_key
        self.period = period
        self.years = years
        self.name = None
        self.max_date = max_date
        self.fundamental_data = []
        self.summary = {}
        self.current_price = None
        self.market_cap = None

    def fetch_fundamentals(self):
        end_date = datetime.strptime(self.max_date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=365)
        url = f"https://api.tiingo.com/tiingo/fundamentals/{self.ticker}/statements"
        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "statement": "income",
            "period": self.period,
            "token": self.api_key
        }
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            raise Exception(f"Fehler beim Laden der Fundamentaldaten: {resp.text}")
        data = resp.json()
        filtered = [q for q in data if q["date"] <= self.max_date]
        self.fundamental_data = filtered[-4:]

    def fetch_name(self):
        url = f"https://api.tiingo.com/tiingo/daily/{self.ticker}"
        headers = {'Authorization': f'Token {self.api_key}'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            self.name =  data.get("name")  # z. B. "Apple Inc"


    def fetch_price_nearest_before(self, date_str, max_lookback_days=7):
        """
        Versucht, den Schlusskurs für den gegebenen Tag zu holen.
        Wenn kein Kurs vorhanden ist (z.B. Wochenende), sucht rückwärts bis zu max_lookback_days zurück.
        """
        date = datetime.strptime(date_str, "%Y-%m-%d")
        for _ in range(max_lookback_days):
            date_check = date.strftime("%Y-%m-%d")
            url = f"https://api.tiingo.com/tiingo/daily/{self.ticker}/prices"
            params = {
                "startDate": date_check,
                "endDate": date_check,
                "token": self.api_key
            }
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                result = resp.json()
                if result:
                    return result[0].get("close")
            date -= timedelta(days=1)
        return None  # Kein Kurs innerhalb von max_lookback_days gefunden


    def fetch_current_price(self):
        return self.fetch_price_nearest_before("2025-07-08")

    def analyze_market_cap(self):
        latest = FundamentalData(self.fundamental_data[-1]) if self.fundamental_data else None
        shares = latest.balanceSheet.get("sharesBasic") if latest else None
        price = self.fetch_current_price()
        self.current_price = price
        if price and shares:
            self.market_cap = price * shares
            self.summary["market_cap"] = self.market_cap
        else:
            self.market_cap = None

    def analyze_price_performance(self):
        today = datetime.today()
        periods = {
            "1y": today - timedelta(days=365),
            "3y": today - timedelta(days=3*365),
            "5y": today - timedelta(days=5*365),
        }
        self.summary["price_changes"] = {}
        for label, date in periods.items():
            past_price = self.fetch_price_nearest_before(date.strftime("%Y-%m-%d"))
            if self.current_price and past_price:
                change = (self.current_price  - past_price) / past_price
                self.summary["price_changes"][label] = change

    def rate_stock(self):
        changes = self.summary.get("price_changes", {})
        mc = self.summary.get("market_cap", 0)
        rating = "Bad"
        if changes.get("5y", 0) > 1.0 and mc > 50e9:
            rating = "Good"
        self.summary["rating"] = rating

    def report(self):
        print(f"\nFundamentaldaten und Kursanalyse für {self.name}({self.ticker}):")
        print("=" * 70)
        if self.market_cap:
            print(f"Marktkapitalisierung: {self.market_cap / 1e9:.2f} Mrd USD")
        print("Kursveränderung:")
        for label, pct in self.summary.get("price_changes", {}).items():
            print(f"  {label}: {pct:.2%}")
        print(f"Bewertung: {self.summary.get('rating', '-')}")
        print("=" * 70)

class StockOverview:
    def __init__(self, tickers, api_key):
        self.tickers = tickers
        self.api_key = api_key
        self.data = []

    def fetch_company_info(self, ticker):
        url = f"https://api.tiingo.com/tiingo/daily/{ticker}"
        headers = {"Authorization": f"Token {self.api_key}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return {}


    def fetch_fundamentals(self, ticker):
        end_date = datetime.strptime("2025-07-07", "%Y-%m-%d")
        start_date = end_date - timedelta(days=365)
        url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker}/statements"
        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "statement": "income",
            "period": "quarter",
            "token": self.api_key
        }
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            raise Exception(f"Fehler beim Laden der Fundamentaldaten: {resp.text}")
        data = resp.json()
        #filtered = [q for q in data if q["date"] <= "2024-06-30"]
        self.fundamental_data = data[0]


    def fetch_price_nearest_before(self, ticker, date_str, max_lookback_days=7):
        """
        Versucht, den Schlusskurs für den gegebenen Tag zu holen.
        Wenn kein Kurs vorhanden ist (z.B. Wochenende), sucht rückwärts bis zu max_lookback_days zurück.
        """
        date = datetime.strptime(date_str, "%Y-%m-%d")
        for _ in range(max_lookback_days):
            date_check = date.strftime("%Y-%m-%d")
            url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
            params = {
                "startDate": date_check,
                "endDate": date_check,
                "token": self.api_key
            }
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                result = resp.json()
                if result:
                    return result[0].get("adjClose")
            date -= timedelta(days=1)
        return None  # Kein Kurs innerhalb von max_lookback_days gefunden

    def calculate_growth(self, ticker, today):
        growth = {}
        current_price = self.fetch_price_nearest_before(ticker, today)
        if not current_price:
            return None

        def get_growth(years):
            past_date = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=365*years)).strftime("%Y-%m-%d")
            past_price = self.fetch_price_nearest_before(ticker, past_date)
            if past_price:
                return (current_price - past_price) / past_price
            return None

        growth["growth_1y"] = get_growth(1)
        growth["growth_3y"] = get_growth(3)
        growth["growth_5y"] = get_growth(5)
        return growth

    def analyze_all(self):
        today = datetime.today().strftime("%Y-%m-%d")
        for ticker in self.tickers:
            info = self.fetch_company_info(ticker)
            self.fetch_fundamentals(ticker)
            name = info.get("name", "N/A")
            shares_outstanding = None
            for entry in self.fundamental_data["statementData"]["balanceSheet"]:
                if entry["dataCode"] == "sharesBasic":
                    shares_outstanding = entry["value"]
                    break
            price = self.fetch_price_nearest_before(ticker, today)

            market_cap = price * shares_outstanding
            sector = info.get("sector", "")
            industry = info.get("industryGroup", "")

            growth = self.calculate_growth(ticker, today)
            if growth is None:
                continue

            is_good = (
                growth.get("growth_5y", 0) > 1.0 and  # +100%
                market_cap >= 50_000_000_000          # > 50 Mrd
            )
            rating = "✅ Good" if is_good else "❌ Bad"

            self.data.append({
                "Ticker": ticker,
                "Name": name,
                "MarketCap (Mrd €)": round(market_cap / 1e9, 2),
                "1Y Growth": f"{growth['growth_1y']*100:.1f}%" if growth['growth_1y'] else "N/A",
                "3Y Growth": f"{growth['growth_3y']*100:.1f}%" if growth['growth_3y'] else "N/A",
                "5Y Growth": f"{growth['growth_5y']*100:.1f}%" if growth['growth_5y'] else "N/A",
                "Rating": rating,
                "Sector": sector,
                "Industry": industry,
            })

    def display(self):
        df = pd.DataFrame(self.data)
        print(df.to_string(index=False))

import yfinance as yf

class StockOverviewYahoo:
    def __init__(self, tickers):
        self.tickers = tickers
        self.data = []

    def fetch_price_on(self, ticker, date_str, max_lookback_days=7):
        """
        Hole Schlusskurs an einem bestimmten Tag, ggf. rückwärts suchen (z. B. Wochenende).
        """
        target = datetime.strptime(date_str, "%Y-%m-%d")
        for _ in range(max_lookback_days):
            date_check = target.strftime("%Y-%m-%d")
            hist = yf.Ticker(ticker).history(start=date_check, end=(target + timedelta(days=1)).strftime("%Y-%m-%d"))
            if not hist.empty:
                return hist["Close"].iloc[0]
            target -= timedelta(days=1)
        return None

    def calculate_growth(self, ticker, today):
        growth = {}
        current_price = self.fetch_price_on(ticker, today)
        if not current_price:
            return None

        def get_growth(years):
            past_date = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=365 * years)).strftime("%Y-%m-%d")
            past_price = self.fetch_price_on(ticker, past_date)
            if past_price:
                return (current_price - past_price) / past_price
            return None

        growth["growth_1y"] = get_growth(1)
        growth["growth_3y"] = get_growth(3)
        growth["growth_5y"] = get_growth(5)
        return growth

    def analyze_all(self):
        today = datetime.today().strftime("%Y-%m-%d")
        for ticker in self.tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info

                name = info.get("longName") or info.get("shortName", ticker)
                sector = info.get("sector", "N/A")
                industry = info.get("industry", "N/A")
                market_cap = info.get("marketCap", 0)

                growth = self.calculate_growth(ticker, today)
                if growth is None:
                    continue

                is_good = (
                    growth.get("growth_5y", 0) > 1.0 and
                    market_cap >= 50_000_000_000
                )
                rating = "✅ Good" if is_good else "❌ Bad"

                self.data.append({
                    "Ticker": ticker,
                    "Name": name,
                    "MarketCap (Mrd €)": round(market_cap / 1e9, 2),
                    "1Y Growth": f"{growth['growth_1y'] * 100:.1f}%" if growth['growth_1y'] else "N/A",
                    "3Y Growth": f"{growth['growth_3y'] * 100:.1f}%" if growth['growth_3y'] else "N/A",
                    "5Y Growth": f"{growth['growth_5y'] * 100:.1f}%" if growth['growth_5y'] else "N/A",
                    "Rating": rating,
                    "Sector": sector,
                    "Industry": industry,
                })
            except Exception as e:
                print(f"⚠️ Fehler bei {ticker}: {e}")

    def display(self):
        df = pd.DataFrame(self.data)
        print(df.to_string(index=False))


if __name__ == "__main__":
    api_key = "78e5c8035fba0e55ee50d130ec6ea476ecb5f734"
    tickers = ["AAPL", "MSFT", "JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD", "DIS",
               "INTC", "CSCO", "KO", "PFE", "MRK", "TRV", "AXP", "MCD", "CVX", "XOM",
               "IBM", "BA", "MMM", "NKE", "GS", "CAT", "WBA", "DOW", "HON", "AMGN"]

    overview = StockOverviewYahoo(tickers)
    overview.analyze_all()
    overview.display()
