api = "hETjlv7NTUEPC0BzSIhbIiVkyoBtZOnd"

import requests


class FundamentalDataFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"

    def get_fundamentals(self, symbol, years=8):
        results = {}

        # 1. Ratios: EPS, Book Value per Share, PEG Ratio, Free Cashflow/Share
        ratios = self._get_json(f"/ratios/{symbol}?limit={years}")
        results["Jahr"] = [r["date"][:4] for r in ratios]
        income = self._get_json(f"/income-statement/{symbol}?limit={years}")
        eps = []
        for entry in income:
            ni = entry.get("netIncome")
            shares = entry.get("weightedAverageShsOut")
            eps.append(self._komma(ni / shares) if ni and shares else "")
        results["EPS ($)"] = eps
        results["Book Value/Share ($)"] = [self._komma(r.get("bookValue")) for r in ratios]
        results["FCF/Share ($)"] = [self._komma(r.get("freeCashFlowPerShareTTM")) for r in ratios]
        results["PEG Ratio (5J)"] = [self._komma(r.get("pegRatio")) for r in ratios]

        # 2. Revenue: Mio. $, keine Kommas
        income = self._get_json(f"/income-statement/{symbol}?limit={years}")
        results["Revenue (Mio. $)"] = [self._million(r["revenue"]) for r in income]

        # 3. Verschuldung: Eigenkapital + Verbindlichkeiten
        balance = self._get_json(f"/balance-sheet-statement/{symbol}?limit={years}")
        equity = [r.get("totalStockholdersEquity") for r in balance]
        liabilities = [r.get("totalLiabilities") for r in balance]
        results["Equity (Mio. $)"] = [self._million(v) for v in equity]
        results["Liabilities (Mio. $)"] = [self._million(v) for v in liabilities]
        results["Verschuldung (Mio. $)"] = [self._million(
            (e or 0) + (l or 0)) for e, l in zip(equity, liabilities)]





        return results

    def _get_json(self, endpoint):
        url = f"{self.base_url}{endpoint}&apikey={self.api_key}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Fehler bei Abruf {endpoint}: {response.status_code}")
            return []
        return response.json()

    def _komma(self, value):
        if value is None:
            return ""
        return f"{value:.2f}".replace(".", ",")

    def _million(self, value):
        if value is None:
            return ""
        return str(int(round(value / 1_000_000)))  # Keine Punkte oder Kommas


# Beispielverwendung:
if __name__ == "__main__":
    api_key = api
    symbol = "NVDA"  # z. B. Apple

    fetcher = FundamentalDataFetcher(api_key)
    daten = fetcher.get_fundamentals(symbol)

    for eintrag in daten:
        print(eintrag)