import dropbox
import os

class DropBoxService:

    def __init__(self,dropbox_:dropbox,type:str,basepath:str="/Privat/EmmanuelProject"):
        self._dropbox = dropbox_
        self._basepath = os.path.join(basepath,type)

    def upload(self,source:str,destination):
        with open(source, "rb") as f:
            byte_array = f.read()

        self._dropbox.files_upload(byte_array, f"{self._basepath}/{destination}")