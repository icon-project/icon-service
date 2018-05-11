from iconservice.database.db import IconScoreDatabase


class MockDB(IconScoreDatabase):

    @staticmethod
    def make_dict():
        return dict()

    def __init__(self, dict_obj: dict, context_db: 'ContextDatabase'=None, prefix: bytes=b''):
        super().__init__(context_db)
        self.__db = dict_obj

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

    def get_sub_db(self, key: bytes) -> IconScoreDatabase:
        if key not in self.__db:
            sub_db = MockDB(MockDB.make_dict())
            self.__db[key] = sub_db

        return self.__db[key]

    def iterator(self):
        return iter(self.__db.items())
