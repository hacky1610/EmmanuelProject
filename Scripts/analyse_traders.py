from pandas import DataFrame
from BL import ConfigReader
from Connectors.deal_store import DealStore
from Connectors.market_store import MarketStore
from Connectors.trader_store import TraderStore
import pymongo

def make_clickable(url):
    return '<a href="{}" rel="noopener noreferrer" target="_blank">Zulu</a>'.format(url)

conf_reader = ConfigReader("DEMO")
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")

db = client["ZuluDB"]
ts = TraderStore(db)
df = DataFrame()
ms = MarketStore(db)
ds = DealStore(db,"LIVE")


for trader in ts.get_all_traders():
    try:
        print(f"{trader.name}")
        if trader.hist.has_history():
            #trader.calc_ig(ms)
            #ts.save(trader)
            stat = trader.get_statistic()
            live_deals = ds.get_deals_of_trader_as_df(trader.id)
            all_deals = ds.get_deals_of_trader_as_df(trader.id, consider_account_type = False)
            stat["IG Live Profit"] = 0
            stat["IG All Profit"] = 0
            if len(live_deals) > 0:
                stat["IG Live Profit"] = live_deals.profit.sum()
            if len(all_deals) > 0:
                stat["IG All Profit"] = all_deals.profit.sum()
            stat["IG Traded"] = len(all_deals) > 0
            stat["Link"] = f"https://www.zulutrade.com/trader/{trader.id}/trading?t=10000&m=1"
            print(stat)
            df = df.append(stat, ignore_index=True)
    except Exception as ex:
        print(f"Error {ex}")

df['Link'] = df.apply(lambda x: make_clickable(x['Link']), axis=1)
df = df.sort_values(by=["ig_custom"], ascending=False)
df.to_html("/home/daniel/trader_stats_new.html")
df.to_excel("/home/daniel/trader_stats_new.xlsx")



