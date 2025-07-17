api = "hETjlv7NTUEPC0BzSIhbIiVkyoBtZOnd"

import requests


class FundamentalDataFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"

    def get_ratios(self, symbol, years=8):
        url = f"{self.base_url}/ratios/{symbol}?limit={years}&apikey={self.api_key}"
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(f"Fehler beim Abrufen der Daten: {response.status_code}")

        data = response.json()
        results = []

        for entry in data:
            year_data = {
                "Jahr": entry.get("date", "")[:4],
                "Book Value per Share ($)": self._format_decimal(entry.get("bookValue")),
                "Earnings per Share (EPS) ($)": self._format_decimal(entry.get("eps")),
            }
            results.append(year_data)

        return results

    @staticmethod
    def _format_decimal(value):
        if value is None:
            return ""
        # Konvertiert zu String mit Komma statt Punkt, 2 Nachkommastellen
        return f"{value:.2f}".replace(".", ",")


# Beispielverwendung:
if __name__ == "__main__":
    api_key = api
    symbol = "AAPL"  # z. B. Apple

    fetcher = FundamentalDataFetcher(api_key)
    daten = fetcher.get_ratios(symbol)

    for eintrag in daten:
        print(eintrag)