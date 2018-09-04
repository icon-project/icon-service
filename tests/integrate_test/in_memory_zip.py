import io
import os
import zipfile


class InMemoryZip:
    """Class for Make zip data in memory using BytesIO."""

    def __init__(self):
        self._in_memory = io.BytesIO()

    @property
    def data(self) -> bytes:
        """Returns zip data

        :return: zip data
        """
        self._in_memory.seek(0)
        return self._in_memory.read()

    def zip_in_memory(self, path):
        """Make zip data(bytes) in memory.

        :param path: The path of the directory to be zipped.
        """
        try:
            with zipfile.ZipFile(self._in_memory, 'a', zipfile.ZIP_DEFLATED, False) as zf:
                if os.path.isfile(path):
                    zf.write(path)
                else:
                    for root, folders, files in os.walk(path):
                        if root.find('__pycache__') != -1:
                            continue
                        if root.find('/.') != -1:
                            continue
                        for file in files:
                            if file.startswith('.'):
                                continue
                            full_path = os.path.join(root, file)
                            zf.write(full_path)
        except:
            raise Exception