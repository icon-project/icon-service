from iconservice import *
from .role_based_access_control import RoleBasedAccessControl


class Role(RoleBasedAccessControl):
    def __init__(self, db: IconScoreDatabase, role_name: str):
        super().__init__(db)
        self.__role_name = role_name

    def has(self, user: Address, role_name=None) -> bool:
        return super().has(user, self.__role_name)

    def add(self, user: Address, role_name=None):
        super().add(user, self.__role_name)

    def remove(self, user: Address, role_name=None):
        super().remove(user, self.__role_name)
