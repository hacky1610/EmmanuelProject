import signal
import sys
import time
import socket
import dropbox
from selenium.webdriver.chrome.options import Options
from BL import ConfigReader, EnvReader
from BL.zulu_trader import ZuluTrader
from Connectors.IG import IG
from Connectors.deal_store import DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.tiingo import Tiingo
from Connectors.trader_store import TraderStore
from Connectors.zulu_api import ZuluApi
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.LogglyTracer import LogglyTracer
from selenium import webdriver
import pymongo
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from Tracing.multi_tracer import MultiTracer
from UI.zulutrade import ZuluTradeUI

if socket.gethostname() == "acer":
    account_type = "DEMO"
    is_docker = False
    conf_reader = ConfigReader(account_type)
else:
    conf_reader = EnvReader()
    is_docker = True
    account_type = conf_reader.get("Type")

client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ts = TraderStore(db)
ds = DealStore(db)

tracer = MultiTracer([LogglyTracer(conf_reader.get("loggly_api_key"), account_type), ConsoleTracer(True)])
zuluApi = ZuluApi(tracer)
ig = IG(tracer=tracer, conf_reader=conf_reader, acount_type=account_type)
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
dropbox_service = DropBoxService(dbx, account_type)
cache = DropBoxCache(dropbox_service)
tiingo = Tiingo(conf_reader,cache)
options= Options()
options.add_argument('--headless')
#options.add_argument('--disable-dev-shm-usage')

service=Service(ChromeDriverManager().install())


# Funktion, die die Timeout-Behandlung durchführt
def timeout_handler(signum, frame):
    raise TimeoutError("Die Funktion hat zu lange gedauert")

def set_timeout():
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(240)  #

try:
    tracer.write("Start")
    set_timeout()

    zuluUI = ZuluTradeUI(webdriver.Chrome(options=options, service=service))

    zulu_trader = ZuluTrader(deal_storage=ds, zulu_api=zuluApi, ig=ig,
                             trader_store=ts, tracer=tracer, zulu_ui=zuluUI,
                             tiingo=tiingo, account_type=account_type)

    zuluUI.login()

    zulu_trader.trade()
    zuluUI.close()
    tracer.write("End")

except TimeoutError as e:
    tracer.error(f"Timeout Error: {e} ")
except Exception as e:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    tracer.error(f"Error: {e} File:{exc_traceback.tb_frame.f_code.co_filename} - {exc_traceback.tb_lineno}")



