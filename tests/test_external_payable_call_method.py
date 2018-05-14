import unittest

from iconservice.iconscore.icon_score_base import IconScoreBase, external, payable
from iconservice.iconscore.icon_score_context import Message, ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContextFactory, IconScoreContextType
from iconservice.base.address import Address, AddressPrefix, create_address
from iconservice.base.block import Block
from iconservice.base.transaction import Transaction
from iconservice.base.exception import ExternalException, PayableException
from iconservice.database.db import IconScoreDatabase
from tests.mock_db import create_mock_icon_score_db


class CallClass1(IconScoreBase):
    def genesis_init(self, *args, **kwargs) -> None:
        pass

    def __init__(self, db: IconScoreDatabase, owner: Address):
        super().__init__(db, owner)

    @external(readonly=True)
    def func1(self):
        pass

    @external
    def func2(self):
        pass

    @external(readonly=True)
    @payable
    def func3(self):
        pass

    @external
    @payable
    def func4(self):
        pass

    @payable
    def func5(self):
        pass

    def func6(self):
        pass

    # @external
    @payable
    def fallback(self):
        pass


class CallClass2(CallClass1):
    def genesis_init(self, *args, **kwargs) -> None:
        super().genesis_init(*args, **kwargs)
        pass

    def __init__(self, db: IconScoreDatabase, owner: Address):
        super().__init__(db, owner)

    def func1(self):
        pass

    @external
    @payable
    def func5(self):
        pass

    def fallback(self):
        pass


class TestContextContainer(ContextContainer):
    pass


class TestCallMethod(unittest.TestCase):

    def setUp(self):
        self._factory = IconScoreContextFactory(max_size=1)
        self._context = self._factory.create(IconScoreContextType.GENESIS)
        self._context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 0)
        self._context.tx = Transaction('test_01', origin=create_address(AddressPrefix.EOA, b'owner'))
        self._context.block = Block(1, 'block_hash', 0)

        self._context_container = TestContextContainer()
        self._context_container._put_context(self._context)
        self.ins = CallClass2(create_mock_icon_score_db(), create_address(AddressPrefix.EOA, b'test'))

    def tearDown(self):
        self.ins = None

    def test_success_call_method(self):
        self._context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 0)
        # self.ins.call_method('func1', {})
        self.ins.call_method('func2', {})
        self.ins.call_method('func3', {})
        self.ins.call_method('func4', {})
        self.ins.call_method('func5', {})
        # self.ins.call_method('func6', {})

    def test_fail_call_method(self):
        self._context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 1)
        self.assertRaises(ExternalException, self.ins.call_method, 'func1', {})
        self.assertRaises(PayableException, self.ins.call_method, 'func2', {})
        # self.assertRaises(PayableException, self.ins.call_method, 'func3', {})
        # self.assertRaises(PayableException, self.ins.call_method, 'func4', {})
        # self.assertRaises(ExternalException, self.ins.call_method, 'func5', {})
        self.assertRaises(ExternalException, self.ins.call_method, 'func6', {})

        self._context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 0)
        # self.assertRaises(PayableException, self.ins.call_method, 'func3', {})
        # self.assertRaises(PayableException, self.ins.call_method, 'func4', {})
        # self.assertRaises(ExternalException, self.ins.call_method, 'func5', {})
        self.assertRaises(ExternalException, self.ins.call_method, 'func6', {})
