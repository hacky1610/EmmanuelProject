from Connectors.IG import IG
from Predictors.trainer import Trainer
from BL.utils import ConfigReader
import os
import tempfile
from datetime import datetime
from Connectors.dropboxservice import DropBoxService
import dropbox

dbx = dropbox.Dropbox(ConfigReader().get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
temp_file = os.path.join(tempfile.gettempdir(), f"evaluate.xlsx")
trainer = Trainer()
markets = IG(conf_reader=ConfigReader()).get_markets(tradebale=False)

for m in markets:
    symbol = m["symbol"]
    res = trainer.train_RSI_STOCH(symbol)
    res.to_excel(temp_file)
    t = datetime.now().strftime("%Y_%m_%d_%H:%M:%S")
    ds.upload(temp_file, os.path.join("Training", f"{t}_{symbol}.xlsx"))








