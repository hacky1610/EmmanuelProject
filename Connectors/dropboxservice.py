import dropbox
import os

class DropBoxService:

    def __init__(self,dropbox_:dropbox,type:str,basepath:str="/Privat/EmmanuelProject"):
        self._dropbox = dropbox_
        self._basepath = f"{basepath}/{type}"

    def upload_file(self, source: str, destination: str):
        with open(source, "rb") as f:
            byte_array = f.read()

        try:
            self._dropbox.files_upload(byte_array, f"{self._basepath}/{destination}")
        except Exception as e:
            print("Error uploading file")

    def upload_data(self, data:str, destination):

        byte_data = bytes(data, encoding='utf-8')
        try:
            self._dropbox.files_upload(byte_data, f"{self._basepath}/{destination}", mode=dropbox.files.WriteMode("overwrite"))
        except Exception as e:
            print("Error uploading file")

    def load(self, source:str):
        try:
            meta, res = self._dropbox.files_download(f"{self._basepath}/{source}")
            return res.content.decode()
        except Exception as e:
            print(f"Error loading file {source} {e}")
            return None