from BL import ConfigReader
from Connectors.IG import IG
from Connectors.deal_store import Deal, DealStore
from Connectors.tiingo import TradeType
from Connectors.trader_store import TraderStore, Trader
from Connectors.zulu_api import ZuluApi
from Tracing.LogglyTracer import LogglyTracer
from datetime import datetime

import pymongo

# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["ZuluDB"]
ts = TraderStore(db)
ds = DealStore(db)
zuluApi = ZuluApi()
max_minutes = 6000

type_ = "DEMO"
if type_ == "DEMO":

    live = False
else:
    live = True

conf_reader = ConfigReader(live_config=live)
tracer = LogglyTracer(conf_reader.get("loggly_api_key"), type_)
ig = IG(tracer=tracer, conf_reader=conf_reader, live=live)

for open_deal in ds.get_open_deals():
    for op in zuluApi.get_opened_positions(open_deal["trader_id"], ""):
        if open_deal["id"] == op.get_id():
            print("Position is still open")
            continue
        print("Position is closed")
        result, deal_respons = ig.close(epic=open_deal["epic"],
                                        direction=IG.get_inverse(op.get_direction()),
                                        deal_id=open_deal["deal_id"])
        if result:
            print("Position closed")
            ds.update_state(op.get_id(), "Closed")

positions = []
for trader in ts.get_all_traders():
    positions = positions + zuluApi.get_opened_positions(trader["id"], trader["name"])

markets = ig.get_markets(trade_type=TradeType.FX, tradeable=False)

for p in positions:
    diff = datetime.utcnow() - p.get_open_time()
    if diff.seconds / 60 < max_minutes:
        for m in markets:
            if m["symbol"] == p.get_ticker():
                result, deal_respons = ig.open(epic=m["epic"], direction=p.get_direction(), currency=m["currency"])
                if result:
                    d = Deal(zulu_id=p.get_id(), ticker=p.get_ticker(),
                             dealReference=deal_respons["dealReference"],
                             dealId=deal_respons["dealId"], trader_id=p.get_trader_id())
                    ds.save(d)

    else:
        print(f"Position is to old. Older than {max_minutes} minites")

print("")
