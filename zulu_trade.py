import traceback

from selenium.webdriver.chrome.options import Options

from BL import BaseReader
from BL.zulu_trader import ZuluTrader
from Connectors.IG import IG
from Connectors.deal_store import DealStore
from Connectors.market_store import MarketStore
from Connectors.trader_store import TraderStore
from Connectors.zulu_api import ZuluApi
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.LogglyTracer import LogglyTracer
from selenium import webdriver
import pymongo
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from Tracing.MultiTracer import MultiTracer
from UI.zulutrade import ZuluTradeUI


def trade(conf_reader: BaseReader, account_type: str = "DEMO"):
    client = pymongo.MongoClient(
        f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
    db = client["ZuluDB"]
    ts = TraderStore(db)
    ds = DealStore(db, account_type)
    ms = MarketStore(db)
    tracer = MultiTracer([LogglyTracer(conf_reader.get("loggly_api_key"), account_type), ConsoleTracer(True)])
    zulu_api = ZuluApi(tracer)
    ###############################################################
    #CHEATttttttttttttttttttttttttttttttttt
    ############################################################
    ig = IG(tracer=tracer, conf_reader=conf_reader)
    options = Options()
    options.add_argument('--headless')
    service = Service(ChromeDriverManager().install())

    check_crash = conf_reader.get_bool("check_crash")
    trading_size = conf_reader.get_float("trading_size",1.0)
    check_trader = conf_reader.get_bool("check_trader")

    try:
        tracer.debug(f"Check Crash {check_crash}  Trading Size {trading_size}"
                     f"Check Trader {check_trader} ")
        driver = webdriver.Chrome(options=options, service=service)
        driver.implicitly_wait(15)
        zulu_ui = ZuluTradeUI(driver, tracer)

        zulu_trader = ZuluTrader(deal_storage=ds, zulu_api=zulu_api, ig=ig,
                                 trader_store=ts, tracer=tracer, zulu_ui=zulu_ui,
                                 account_type=account_type,
                                 check_for_crash=check_crash, check_trader_quality=check_trader,
                                 market_storage=ms, trading_size=trading_size)

        zulu_ui.login()

        zulu_trader.trade()
        zulu_ui.close()
        tracer.debug("End")

    except Exception as e:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        tracer.error(f"MainException: {e} File:{traceback_str}")