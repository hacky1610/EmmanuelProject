import os
import re
from typing import Optional
from pathlib import Path


class FileOperations:

    @staticmethod
    def get_folder_by_regex(parent_directory: Optional[Path], reg_value: str):
        assert os.path.exists(parent_directory)

        dirs = os.listdir(parent_directory)
        r = re.compile(reg_value)

        result = list(filter(r.match, dirs))
        if len(result) == 1:
            return os.path.join(parent_directory, result[0])
        else:
            return None
