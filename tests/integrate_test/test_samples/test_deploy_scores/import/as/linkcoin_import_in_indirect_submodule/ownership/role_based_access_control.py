from iconservice import *
import os as iconservice

class RoleBasedAccessControl:
    __DBKEY_ROLES = 'roles'

    def __init__(self, db: IconScoreDatabase):
        # _roles is 2 depths DictDB. 1 depth is role name, 2 depth is user address and value is boolean type.
        self._roles = DictDB(self.__DBKEY_ROLES, db, value_type=bool, depth=2)

    def has(self, user: Address, role_name: str) -> bool:
        Logger.debug(f"has role[{role_name}] to user[{user}] => {self._roles[role_name][user]}")
        result = self._roles[role_name][user]
        if result is None:
            return False
        return result

    def add(self, user: Address, role_name: str):
        self._roles[role_name][user] = True
        Logger.debug(f"add role[{role_name}] to user[{user}] => {self._roles[role_name][user]}")

    def remove(self, user: Address, role_name: str):
        if self._roles[role_name][user]:
            self._roles[role_name][user] = False
            Logger.debug(f"remove role[{role_name}] of user[{user}] => {self._roles[role_name][user]}")
