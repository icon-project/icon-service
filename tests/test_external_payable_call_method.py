# import unittest
#
# from iconservice.iconscore.icon_score_base import IconScoreBase, external, payable, interface
# from iconservice.iconscore.icon_score_context import Message, ContextContainer
# from iconservice.iconscore.icon_score_context import IconScoreContextFactory, IconScoreContextType
# from iconservice.base.address import Address, AddressPrefix, create_address
# from iconservice.base.block import Block
# from iconservice.base.transaction import Transaction
# from iconservice.base.exception import ExternalException, PayableException, IconScoreException
# from iconservice.database.db import IconScoreDatabase
# from tests.mock_db import create_mock_icon_score_db
# from functools import wraps
#
#
# def decorator(func):
#     @wraps(func)
#     def __wrapper(calling_obj: object, *args, **kwargs):
#         print('!!')
#         res = func(calling_obj, *args, **kwargs)
#         return res
#     return __wrapper
#
#
# class CallClass1(IconScoreBase):
#     def on_install(self, params: dict) -> None:
#         pass
#
#     def on_update(self, params: dict) -> None:
#         pass
#
#     def __init__(self, db: IconScoreDatabase, owner: Address):
#         super().__init__(db, owner)
#
#     @external(readonly=True)
#     def func1(self):
#         pass
#
#     @external
#     @decorator
#     def func2(self):
#         pass
#
#     @payable
#     @external
#     def func3(self):
#         pass
#
#     @payable
#     @external
#     def func4(self):
#         pass
#
#     @payable
#     def func5(self):
#         pass
#
#     def func6(self):
#         pass
#
#     @payable
#     def fallback(self):
#         pass
#
#
# class CallClass2(CallClass1):
#     def on_install(self, params) -> None:
#         super().on_install(params)
#
#     def on_update(self, params) -> None:
#         super().on_update(params)
#
#     def __init__(self, db: IconScoreDatabase, owner: Address):
#         super().__init__(db, owner)
#
#     def func1(self):
#         pass
#
#     @payable
#     @external
#     def func5(self):
#         pass
#
#     def fallback(self):
#         pass
#
#
# class TestContextContainer(ContextContainer):
#     pass
#
#
# class TestCallMethod(unittest.TestCase):
#
#     def setUp(self):
#         self._factory = IconScoreContextFactory(max_size=1)
#         self._context = self._factory.create(IconScoreContextType.GENESIS)
#         self._context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 0)
#         self._context.tx = Transaction('test_01', origin=create_address(AddressPrefix.EOA, b'owner'))
#         self._context.block = Block(1, 'block_hash', 0)
#
#         self._context_container = TestContextContainer()
#         self._context_container._put_context(self._context)
#
#     def tearDown(self):
#         self.ins = None
#
#     def test_success_call_method(self):
#         self.ins = CallClass2(create_mock_icon_score_db(), create_address(AddressPrefix.EOA, b'test'))
#         self._context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 0)
#         self._context.type = IconScoreContextType.INVOKE
#         func = getattr(self.ins, '_IconScoreBase__call_method')
#         # func('func1', {})
#         func('func2', {})
#         self._context.type = IconScoreContextType.QUERY
#         # func('func3', {})
#         self._context.type = IconScoreContextType.INVOKE
#         func('func4', {})
#         func('func5', {})
#         # func('func6', {})
#
#     def test_fail_call_method(self):
#         self.ins = CallClass2(create_mock_icon_score_db(), create_address(AddressPrefix.EOA, b'test'))
#         self._context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 1)
#         func = getattr(self.ins, '_IconScoreBase__call_method')
#         self.assertRaises(ExternalException, func, 'func1', {})
#         self.assertRaises(PayableException, func, 'func2', {})
#         # self._context.type = IconScoreContextType.GENESIS
#         # self.assertRaises(ExternalException, func, 'func3', {})
#         self._context.type = IconScoreContextType.QUERY
#         self.assertRaises(IconScoreException, func, 'func4', {})
#         self.assertRaises(IconScoreException, func, 'func5', {})
#
#         self.assertRaises(ExternalException, func, 'func6', {})
#
#         self._context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 0)
#         # self.assertRaises(PayableException, func, 'func3', {})
#         # self.assertRaises(PayableException, func, 'func4', {})
#         # self.assertRaises(ExternalException, func, 'func5', {})
#         self.assertRaises(ExternalException, func, 'func6', {})
#
#     def test_func2_with_decorator(self):
#         self.ins = CallClass2(create_mock_icon_score_db(), create_address(AddressPrefix.EOA, b'test'))
#         func = getattr(self.ins, '_IconScoreBase__call_method')
#         func('func2', {})
#
