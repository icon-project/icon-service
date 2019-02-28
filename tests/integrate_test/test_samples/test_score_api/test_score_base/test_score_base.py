from iconservice import *


class TestScoreBaseInterface(InterfaceScore):
    @interface
    def exchange(self, fromServiceName: str, toServiceName: str, to: Address, value: int) -> bool:
        pass

    @interface
    def addContract(self, score: Address):
        pass


class TestScoreBase(IconScoreBase):

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)

    def on_install(self, value: int=1000) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def hello(self) -> str:
        return "Hello"

    @external(readonly=True)
    def get_value(self) -> int:
        return self._value.get()

    @external
    def set_value(self, value: int):
        self._value.set(value)
        self.Changed(value)
        return True

    @external(readonly=True)
    def test_revert_readonly(self) -> bool:
        revert("test_msg")
        return True

    @external
    def test_revert(self, value: int):
        revert("revert message!!")
        self._value.set(value)
        self.Changed(value)

    @external(readonly=True)
    def test_sha3_256_readonly(self, data: bytes) -> bytes:
        return sha3_256(data)

    @external
    def test_sha3_256(self, data: bytes):
        sha3_256(data)
        self._value.set(10**18)
        self.Changed(10**18)

    @external(readonly=True)
    def test_json_dumps_readonly(self) -> str:
        data = {"key1": 1, "key2": 2, "key3": "value3"}
        return json_dumps(data)

    @external
    def test_json_dumps(self):
        data = {"key1": 1, "key2": 2, "key3": "value3"}
        return_value = json_dumps(data)
        assert type(return_value) == str
        self._value.set(10**18)
        self.Changed(10**18)

    @external(readonly=True)
    def test_json_dumps_none(self) -> str:
        data = {"key1": None, "key2": 2, "key3": "value3"}
        return json_dumps(data)

    @external(readonly=True)
    def test_json_loads_readonly(self) -> str:
        data = json_dumps({"key1": 1, "key2": 2, "key3": "value3"})
        return json_loads(data)

    @external
    def test_json_loads(self):
        data = json_dumps({"key1": 1, "key2": 2, "key3": "value3"})
        return_value = json_loads(data)
        assert type(return_value) == dict
        self._value.set(10**18)
        self.Changed(10**18)

    @external(readonly=True)
    def test_is_score_active_readonly(self, address: Address) -> bool:
        return self.is_score_active(address)

    @external
    def test_is_score_active(self, address: Address):
        assert self.is_score_active(address) in (True, False)
        self._value.set(10**18)
        self.Changed(10**18)

    @external(readonly=True)
    def test_get_owner_readonly(self, address: Address) -> Address:
        return self.get_owner(address)

    @external
    def test_get_owner(self, address: Address) -> bool:
        assert type(self.get_owner(address)) == Address
        self._value.set(10**18)
        self.Changed(10**18)

    @external(readonly=True)
    def test_create_interface_score_readonly(self, address: Address) -> bool:
        return_value = self.create_interface_score(address, TestScoreBaseInterface)
        assert type(type(return_value)) == type(TestScoreBaseInterface)
        return True

    @external
    def test_create_interface_score(self, address: Address):
        self.create_interface_score(address, TestScoreBaseInterface)
        self._value.set(10 ** 18)
        self.Changed(10 ** 18)

    @external(readonly=True)
    def test_deploy_readonly(self, tx_hash: bytes) -> bool:
        self.deploy(tx_hash)
        return True

    @external
    def test_deploy(self, tx_hash: bytes):
        self.deploy(tx_hash)

    @external(readonly=True)
    def test_get_tx_hashes_by_score_address_readonly(self, address: Address) -> bytes:
        return self.get_tx_hashes_by_score_address(address)

    @external
    def test_get_tx_hashes_by_score_address(self, address: Address):
        tx_hashes = self.get_tx_hashes_by_score_address(address)
        assert type(tx_hashes) == tuple
        self._value.set(10 ** 18)
        self.Changed(10 ** 18)

    @external(readonly=True)
    def test_get_score_address_by_tx_hash_readonly(self, tx_hash: bytes) -> Address:
        return self.get_score_address_by_tx_hash(tx_hash)

    @external
    def test_get_score_address_by_tx_hash(self, tx_hash: bytes):
        score_address = self.get_score_address_by_tx_hash(tx_hash)
        if score_address:
            assert type(score_address) == Address
        self._value.set(10 ** 18)
        self.Changed(10 ** 18)
