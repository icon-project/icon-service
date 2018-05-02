from iconservice.database.db import InternalScoreDatabase


class MockDB(InternalScoreDatabase):

    @staticmethod
    def make_dict():
        return dict()

    def __init__(self, dict_obj: dict):
        self.__db = dict_obj
        self.address = None

    def put(self, key: bytes, value: bytes) -> bytes:
        self.__db[key] = value

    def get(self, key: bytes) -> bytes:
        if key not in self.__db:
            return None
        return self.__db[key]

    def delete(self, key: bytes) -> bytes:
        pass

    def close(self):
        pass

    def get_sub_db(self, key: bytes) -> InternalScoreDatabase:
        if key not in self.__db:
            sub_db = MockDB(MockDB.make_dict())
            self.__db[key] = sub_db

        return self.__db[key]

    def iterator(self):
        return iter(self.__db.items())
