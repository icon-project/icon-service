from iconservice import *
from .ownership.ownable import only_owner
from .token.standard_token import StandardToken
from .ownership.blacklist import Blacklist
from .ownership.role import Role

def check_blacklist(func):
    """
    Check if sender is blacklisted.
    """
    @wraps(func)
    def __wrapper(cls, *args, **kwargs):
        if isinstance(cls, StandardTokenSupportBlacklist):
            if cls._blacklist.is_blacklisted(cls.msg.sender):
                cls.revert(f"user is blacklisted.")
        return func(cls, *args, **kwargs)

    return __wrapper


def only_operator(func):
    if not isfunction(func):
        raise IconScoreException(f"{func} isn't function.")

    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):
        if isinstance(calling_obj, StandardTokenSupportBlacklist):
            sender = calling_obj.tx.origin if calling_obj.tx else calling_obj.msg.sender
            if calling_obj.is_ownership_user(sender):
                return func(calling_obj, *args, **kwargs)

            raise IconScoreException(f"{sender} don't have authority'")
        raise IconScoreException(f"invalid operation")

    return __wrapper


class StandardTokenSupportBlacklist(StandardToken):
    """
    Standard token support blacklist.
    The blacklisted user can't transfer and approve.
    """
    __ROLE_OWNERSHIP = 'ownership'

    @eventlog(indexed=1)
    def AddBlacklist(self, user: Address):
        pass

    @eventlog(indexed=1)
    def RemoveBlacklist(self, user: Address):
        pass

    @eventlog(indexed=1)
    def AddOwnership(self, user: Address):
        pass

    @eventlog(indexed=1)
    def RemoveOwnership(self, user: Address):
        pass

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db)
        self._blacklist = Blacklist(db)
        self.__ownership = Role(db, self.__ROLE_OWNERSHIP)

    def on_install(self, **kwargs):
        super().on_install(**kwargs)
        self.add_ownership_user(self.msg.sender)
        Logger.debug(f"StandardTokenSupportBlacklist install ownership operator is [{self.msg.sender}]")

    @only_owner
    @external
    def add_ownership_user(self, user: Address, message: str = None):
        self.__ownership.add(user)
        self.AddOwnership(user)

    @only_owner
    @external
    def remove_ownership_user(self, user: Address, message: str = None):
        self.__ownership.remove(user)
        self.RemoveOwnership(user)

    @only_owner
    @external(readonly=True)
    def is_ownership_user(self, user: Address) -> bool:
        return self.__ownership.has(user)

    @only_operator
    @external
    def add_blacklist(self, user: Address, message: str = None):
        if user.is_contract:
            self.revert("user address is invalid")

        self._blacklist.add_address_to_blacklist(user)
        self.AddBlacklist(user)

    @only_operator
    @external
    def remove_blacklist(self, user: Address, message: str = None):
        if user.is_contract:
            self.revert("user address is invalid")

        self._blacklist.remove_address_from_blacklist(user)
        self.RemoveBlacklist(user)

    @only_operator
    @external(readonly=True)
    def is_blacklisted(self, user: Address) -> bool:
        return self._blacklist.is_blacklisted(user)

    @check_blacklist
    @external
    def transfer(self, to_addr: Address, value: int, message: str = None) -> bool:
        return super().transfer(to_addr, value, message)

    @check_blacklist
    @external
    def approve(self, spender: Address, value: int) -> bool:
        return super().approve(spender, value)

    @check_blacklist
    @external
    def increase_approval(self, spender: Address, value: int) -> bool:
        return super().increase_approval(spender, value)

    @check_blacklist
    @external
    def decrease_approval(self, spender: Address, value: int) -> bool:
        return super().decrease_approval(spender, value)

    @check_blacklist
    @external
    def transfer_from(self, from_addr: Address, to_addr: Address, value: int) -> bool:
        return super().transfer_from(from_addr, to_addr, value)
