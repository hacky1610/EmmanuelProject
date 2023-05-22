from Connectors.dropboxservice import DropBoxService
import pandas as pd
import io
from pandas import DataFrame

class DropBoxCache:

    def __init__(self,dropbox_servie:DropBoxService):
        self.dropbox_servie = dropbox_servie


    def load(self,name:str) -> DataFrame:
        res = self.dropbox_servie.load( f"Cache/{name}")
        if res == None:
            return DataFrame()
        df =  pd.read_csv(io.StringIO(res), sep=",")
        df = df.filter(["date", "open", "high", "low", "close"])
        return df


    def save(self,data:DataFrame, name:str):
        self.dropbox_servie.upload_data(data.to_csv(),f"Cache/{name}")