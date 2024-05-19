import dropbox
import pymongo
from pandas import Series, DataFrame

from BL import DataProcessor, ConfigReader
from BL.analytics import Analytics
from BL.indicators import Indicators
from Connectors.IG import IG
from Connectors.deal_store import DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.tiingo import Tiingo, TradeType
from Predictors.generic_predictor import GenericPredictor
from Tracing.LogglyTracer import LogglyTracer
from UI.plotly_viewer import PlotlyViewer

account_type = "DEMO"
conf_reader = ConfigReader(False)

dataProcessor = DataProcessor()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
tracer = LogglyTracer(conf_reader.get("loggly_api_key"), account_type)
tiingo = Tiingo(tracer=tracer, conf_reader=conf_reader, cache=cache)
ig = IG(conf_reader=conf_reader, tracer=tracer, live=False)
predictor_class_list = [GenericPredictor]
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ds = DealStore(db, account_type)
analytics = Analytics(ms, tracer)
indicators = Indicators(tracer=tracer)
viewer = PlotlyViewer(cache=cache)

deals = ds.get_all_deals()

df = DataFrame()
for d in deals:
    if "predictor_data" in d:
        if d["predictor_data"] is not None and d["status"] == "Closed":
            pg = GenericPredictor(indicators=Indicators(), config=d["predictor_data"])

            s = Series(data=[d['profit'],
                             d["ticker"],
                             pg.get_last_result().get_average_reward(),
                             pg.get_last_result().get_trades(),
                             
                             pg.get_last_result().get_win_loss()],
                       index=["profit",
                              "ticker",
                              "AvgReward",
                              "Trades",
                              "WL"])
            df =  df.append(s, ignore_index=True)

for ticker in df["ticker"].unique():
    print(f"-------- {ticker}  ------------")
    e = df[df.ticker == ticker]
    print(f"Result:{e.profit.sum()}")
    print(f"AvgRew:{e.AvgReward.median()}")
    print(f"Trades:{e.Trades.median()}")
    print(f"WL:{e.WL.median()}")
    df, df_eval = tiingo.load_test_data(ticker, dataProcessor, TradeType.FX)
    predictor = GenericPredictor(indicators=indicators, cache=cache, viewer=viewer)
    predictor.load(ticker)
    ev_result = analytics.evaluate(predictor=predictor,
                                   df=df,
                                   df_eval=df_eval,
                                   viewer=viewer,
                                   symbol=ticker,
                                   only_one_position=True,
                                   scaling=1)


