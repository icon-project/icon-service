from iconservice import *
from .role_based_access_control import RoleBasedAccessControl


class Blacklist(RoleBasedAccessControl):
    __ROLE_BLACKLIST = 'blacklist'

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db)

    def add_address_to_blacklist(self, user: Address):
        self.add(user, self.__ROLE_BLACKLIST)

    def remove_address_from_blacklist(self, user: Address):
        self.remove(user, self.__ROLE_BLACKLIST)

    def is_blacklisted(self, user: Address) -> bool:
        return self.has(user, self.__ROLE_BLACKLIST)
