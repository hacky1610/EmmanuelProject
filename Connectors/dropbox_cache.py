import json
import os

from Connectors.dropboxservice import DropBoxService
import pandas as pd
import io
from pandas import DataFrame


class BaseCache:

    def load_cache(self, name: str) -> DataFrame:
        return DataFrame()

    def save_cache(self, data: DataFrame, name: str):
        pass

    def load_settings(self, name: str) -> DataFrame:
        return DataFrame()

    def save_settings(self, data: DataFrame, name: str):
        pass

    def load_deal_info(self, name: str):
        pass

    def save_deal_info(self, data: str, name: str):
        pass

    def save_report(self, data: DataFrame, name: str):
        pass

    def save_report_image(self, source: str, destination: str):
        pass


class DropBoxCache(BaseCache):

    def __init__(self, dropbox_servie: DropBoxService, use_local_cache=False ):
        self.dropbox_servie = dropbox_servie
        self.use_local_cache = use_local_cache

    def load_cache(self, name: str) -> DataFrame:
        if self.use_local_cache:
            path = f"D:\\tmp\\{name}"
            if os.path.exists(path):
                df = pd.read_csv(path)
                df = df.reset_index(drop=True)
            else:
                res = self.dropbox_servie.load(f"Cache/{name}")
                if res == None:
                    return DataFrame()
                df = pd.read_csv(io.StringIO(res), sep=",")
                df.to_csv(path)
            df = df.filter(["date", "open", "high", "low", "close"])
            return df
        else:
            res = self.dropbox_servie.load(f"Cache/{name}")
            if res == None:
                raise Exception(f"Cache {name} not found")
            df = pd.read_csv(io.StringIO(res), sep=",")
            df = df.filter(["date", "open", "high", "low", "close"])
            return df


    def save_cache(self, data: DataFrame, name: str):
        if self.use_local_cache:
            data.to_csv(f"D:\\tmp\\{name}")
        else:
            self.dropbox_servie.upload_data(data.to_csv(), f"Cache/{name}")

    def load_settings(self, name: str):
        res = self.dropbox_servie.load(f"Settings/{name}")
        if res is not None:
            return json.loads(res)
        return None

    def save_settings(self, data: str, name: str):
        self.dropbox_servie.upload_data(data, f"Settings/{name}")

    def load_deal_info(self, name: str):
        res = self.dropbox_servie.load(f"deals/{name}.json")
        if res is not None:
            return json.loads(res)
        return None

    def save_deal_info(self, data: str, name: str):
        self.dropbox_servie.upload_data(data, f"deals/{name}.json")

    def save_report(self, data: DataFrame, name: str):
        self.dropbox_servie.upload_data(data.to_csv(), f"Report/{name}")

    def save_report_image(self, source: str, destination: str):
        self.dropbox_servie.upload_file(source, destination)
