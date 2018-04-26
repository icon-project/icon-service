import unittest
from iconservice.iconscore.icon_score_base import IconScoreBase, score, external, payable
# from iconservice.base.address import Address, AddressPrefix
from iconservice.iconscore.icon_score_context import IconScoreContext, Message
from iconservice.base.exception import ExternalException, PayableException


@score
class CallClass(IconScoreBase):

    def genesis_init(self, *args, **kwargs) -> None:
        pass

    def __init__(self, db, *args, **kwargs):
        super().__init__(db, *args, **kwargs)

    @external(readonly=True)
    def func1(self):
        pass

    @external()
    def func2(self):
        pass

    @external(readonly=True)
    @payable
    def func3(self):
        pass

    @external()
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
        self.ins = CallClass(None)
        # self.test_context = IconScoreContext(Message(Address(AddressPrefix.EOA, hex(0).encode()), 1))
        # self.empty_context = IconScoreContext(Message(Address(AddressPrefix.EOA, hex(1).encode()), 0))
        self.test_context = IconScoreContext(msg=Message('test1', 1))
        self.empty_context = IconScoreContext(msg=Message('test2', 0))
        pass

    def tearDown(self):
        self.ins = None
        self.test_context = None
        self.empty_context = None

    def test_success_call_method(self):
        self.ins.set_context(self.empty_context)
        self.ins.call_method('func1')
        self.ins.call_method('func2')
        # self.ins.call_method('func3')
        self.ins.call_method('func4')
        # self.ins.call_method('func5')
        # self.ins.call_method('func6')

    def test_fail_call_method(self):
        self.ins.set_context(self.test_context)
        self.assertRaises(PayableException, self.ins.call_method, 'func1')
        self.assertRaises(PayableException, self.ins.call_method, 'func2')
        self.assertRaises(PayableException, self.ins.call_method, 'func3')
        # self.assertRaises(PayableException, self.ins.call_method, 'func4')
        self.assertRaises(ExternalException, self.ins.call_method, 'func5')
        self.assertRaises(ExternalException, self.ins.call_method, 'func6')

        self.ins.set_context(self.empty_context)
        self.assertRaises(PayableException, self.ins.call_method, 'func3')
        # self.assertRaises(PayableException, self.ins.call_method, 'func4')
        self.assertRaises(ExternalException, self.ins.call_method, 'func5')
        self.assertRaises(ExternalException, self.ins.call_method, 'func6')
