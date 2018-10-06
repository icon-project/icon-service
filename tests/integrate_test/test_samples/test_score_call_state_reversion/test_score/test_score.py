from iconservice import *


class TestScore(IconScoreBase):

    @eventlog
    def Event(self, _scoreName: str, _at: str, _sender: Address):
        pass

    @eventlog
    def ExcetionEvent(self, msg: str):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._name = VarDB('_name', db, value_type=str)
        self._next_address = VarDB('_next_address', db, value_type=Address)
        self._next_function = VarDB('_next_function', db, value_type=str)
        self._should_handle_exception = VarDB('_should_handle_exception', db, value_type=bool)
        self._invoked = VarDB('_invoked', db, value_type=bool)

    def on_install(self,
                   _name: str,
                   _nextAddress: Address = None,
                   _nextFunction: str = None,
                   _shouldHandleException: bool = False) -> None:
        super().on_install()
        self._name.set(_name)
        if _nextAddress:
            self._next_address.set(_nextAddress)
        if _nextFunction:
            self._next_function.set(_nextFunction)
        self._should_handle_exception.set(_shouldHandleException)

    def on_update(self) -> None:
        super().on_update()

    @external
    @payable
    def invoke(self) -> None:
        self.Event(self._name.get(), 'start', self.msg.sender)
        print(f'context is readonly at {self._name.get()} start:{self._context.readonly}')
        if self._should_handle_exception.get():
            try:
                self.handle_invoke()
            except BaseException as e:
                # self.ExcetionEvent(f'{self._name.get()} {e.message}')
                pass
        else:
            self.handle_invoke()
        print(f'context is readonly at {self._name.get()} end:{self._context.readonly}')
        self.Event(self._name.get(), 'end', self.msg.sender)

    @external(readonly=True)
    def query(self) -> int:
        print(f'context is readonly at {self._name.get()} start:{self._context.readonly}')
        self.handle_query()
        print(f'context is readonly at {self._name.get()} end:{self._context.readonly}')
        return 1

    @external(readonly=True)
    def getInvoked(self) -> bool:
        print(f'getInvoked')
        return self._invoked.get()

    def handle_invoke(self):
        self._invoked.set(True)
        if self._next_address.get() is None:
            revert('reverted in invoke')
        else:
            next_function = self._next_function.get()
            print(f'next_function:{next_function}')
            ret = self.call(
                self._next_address.get(),
                next_function,
                {},
                self.msg.value // 2 if next_function == 'invoke' else 0)
            print(f'ret:{ret}')

    def handle_query(self):
        if self._next_address.get() is None:
            revert('reverted in query')
        else:
            self.call(
                self._next_address.get(),
                self._next_function.get(),
                {})
