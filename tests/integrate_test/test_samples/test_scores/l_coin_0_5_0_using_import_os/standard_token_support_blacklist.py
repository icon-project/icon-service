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
        revert(f"{func} isn't function.")

    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):
        if isinstance(calling_obj, StandardTokenSupportBlacklist):
            sender = calling_obj.tx.origin if calling_obj.tx else calling_obj.msg.sender
            if calling_obj.isOwnershipUser(sender):
                return func(calling_obj, *args, **kwargs)
            revert(f"{sender} don't have authority'")
        revert(f"invalid operation")

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

    def on_install(self, **kwargs) -> None:
        super().on_install(**kwargs)
        self.addOwnershipUser(self.msg.sender)
        Logger.debug(f"StandardTokenSupportBlacklist install ownership operator is [{self.msg.sender}]")

    @only_owner
    @external
    def addOwnershipUser(self, user: Address, message: str = None):
        self.__ownership.add(user)
        self.AddOwnership(user)

    @only_owner
    @external
    def removeOwnershipIUser(self, user: Address, message: str = None):
        self.__ownership.remove(user)
        self.RemoveOwnership(user)

    @only_owner
    @external(readonly=True)
    def isOwnershipUser(self, user: Address) -> bool:
        return self.__ownership.has(user)

    @only_operator
    @external
    def addBlacklist(self, user: Address, message: str = None):
        if user.is_contract:
            self.revert("user address is invalid")

        self._blacklist.add_address_to_blacklist(user)
        self.AddBlacklist(user)

    @only_operator
    @external
    def removeBlacklist(self, user: Address, message: str = None):
        if user.is_contract:
            self.revert("user address is invalid")

        self._blacklist.remove_address_from_blacklist(user)
        self.RemoveBlacklist(user)

    @only_operator
    @external(readonly=True)
    def isBlacklisted(self, user: Address) -> bool:
        return self._blacklist.is_blacklisted(user)

    @check_blacklist
    @external
    def transfer(self, toAddr: Address, value: int, message: str = None) -> bool:
        return super().transfer(toAddr, value, message)

    @check_blacklist
    @external
    def approve(self, spender: Address, value: int) -> bool:
        return super().approve(spender, value)

    @check_blacklist
    @external
    def increaseApproval(self, spender: Address, value: int) -> bool:
        return super().increaseApproval(spender, value)

    @check_blacklist
    @external
    def decreaseApproval(self, spender: Address, value: int) -> bool:
        return super().decreaseApproval(spender, value)

    @check_blacklist
    @external
    def transferFrom(self, fromAddr: Address, toAddr: Address, value: int) -> bool:
        return super().transferFrom(fromAddr, toAddr, value)
