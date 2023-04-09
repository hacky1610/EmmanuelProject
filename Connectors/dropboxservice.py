import dropbox

class DropBoxService:

    def __init__(self,dropbox_:dropbox,basepath:str="/Privat/EmmanuelProject"):
        self._dropbox = dropbox_
        self._basepath =basepath

    def upload(self,source:str,destination):
        with open(source, "rb") as f:
            byte_array = f.read()

        self._dropbox.files_upload(byte_array, f"{self._basepath}/{destination}")