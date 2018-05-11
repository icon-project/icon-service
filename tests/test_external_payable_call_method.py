import unittest

from iconservice.iconscore.icon_score_base import IconScoreBase, score, external, payable
from iconservice.iconscore.icon_score_context import IconScoreContext, Message, ContextContainer
from iconservice.base.address import Address, AddressPrefix, create_address
from iconservice.base.exception import ExternalException, PayableException
from iconservice.database.db import ContextDatabase
from tests.mock_db import MockDB


@score
class CallClass(IconScoreBase, ContextContainer):

    def genesis_init(self, *args, **kwargs) -> None:
        pass

    def __init__(self, db, owner):
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

    # @external()
    @payable
    def fallback(self):
        pass


class TestCallMethod(unittest.TestCase):

    def setUp(self):
        self.owner = create_address(AddressPrefix.EOA, b'owner')
        self.db = MockDB(MockDB.make_dict(), ContextDatabase(None, self.owner))
        self.ins = CallClass(self.db, self.owner)
        self.test_context1 = IconScoreContext(msg=Message(Address(AddressPrefix.EOA, hex(0).encode()), 0))
        self.test_context2 = IconScoreContext(msg=Message(Address(AddressPrefix.EOA, hex(1).encode()), 1))

    def tearDown(self):
        self.ins = None
        self.test_context = None
        self.empty_context = None

    def test_success_call_method(self):
        self.ins._put_context(self.test_context1)
        self.ins.call_method('func1', {})
        self.ins.call_method('func2', {})
        self.ins.call_method('func3', {})
        self.ins.call_method('func4', {})
        # self.ins.call_method('func5', {})
        # self.ins.call_method('func6', {})

    def test_fail_call_method(self):
        self.ins._put_context(self.test_context2)
        self.assertRaises(PayableException, self.ins.call_method, 'func1', {})
        self.assertRaises(PayableException, self.ins.call_method, 'func2', {})
        # self.assertRaises(PayableException, self.ins.call_method, 'func3', {})
        # self.assertRaises(PayableException, self.ins.call_method, 'func4', {})
        self.assertRaises(ExternalException, self.ins.call_method, 'func5', {})
        self.assertRaises(ExternalException, self.ins.call_method, 'func6', {})

        # self.assertRaises(PayableException, self.ins.call_method, 'func3', {})
        # self.assertRaises(PayableException, self.ins.call_method, 'func4', {})
        self.assertRaises(ExternalException, self.ins.call_method, 'func5', {})
        self.assertRaises(ExternalException, self.ins.call_method, 'func6', {})
