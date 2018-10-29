# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from iconservice import *

TAG = 'Governance'
DEBUG = False

CURRENT = 'current'
NEXT = 'next'
STATUS = 'status'
DEPLOY_TX_HASH = 'deployTxHash'
AUDIT_TX_HASH = 'auditTxHash'
VALID_STATUS_KEYS = [STATUS, DEPLOY_TX_HASH, AUDIT_TX_HASH]

STATUS_PENDING = 'pending'
STATUS_ACTIVE = 'active'
STATUS_INACTIVE = 'inactive'
STATUS_REJECTED = 'rejected'

STEP_TYPE_DEFAULT = 'default'
STEP_TYPE_CONTRACT_CALL = 'contractCall'
STEP_TYPE_CONTRACT_CREATE = 'contractCreate'
STEP_TYPE_CONTRACT_UPDATE = 'contractUpdate'
STEP_TYPE_CONTRACT_DESTRUCT = 'contractDestruct'
STEP_TYPE_CONTRACT_SET = 'contractSet'
STEP_TYPE_GET = 'get'
STEP_TYPE_SET = 'set'
STEP_TYPE_REPLACE = 'replace'
STEP_TYPE_DELETE = 'delete'
STEP_TYPE_INPUT = 'input'
STEP_TYPE_EVENT_LOG = 'eventLog'
STEP_TYPE_API_CALL = 'apiCall'
INITIAL_STEP_COST_KEYS = [STEP_TYPE_DEFAULT,
                          STEP_TYPE_CONTRACT_CALL, STEP_TYPE_CONTRACT_CREATE, STEP_TYPE_CONTRACT_UPDATE,
                          STEP_TYPE_CONTRACT_DESTRUCT, STEP_TYPE_CONTRACT_SET,
                          STEP_TYPE_GET, STEP_TYPE_SET, STEP_TYPE_REPLACE, STEP_TYPE_DELETE, STEP_TYPE_INPUT,
                          STEP_TYPE_EVENT_LOG, STEP_TYPE_API_CALL]

CONTEXT_TYPE_INVOKE = 'invoke'
CONTEXT_TYPE_QUERY = 'query'


class StepCosts:
    """
    DB for stepCosts management.
    It is combined DictDB and ArrayDB in order to iterate items.
    """
    _STEP_TYPES = 'step_types'
    _STEP_COSTS = 'step_costs'

    def __init__(self, db: IconScoreDatabase):
        self._step_types = ArrayDB(self._STEP_TYPES, db, value_type=str)
        self._step_costs = DictDB(self._STEP_COSTS, db, value_type=int)

    def __setitem__(self, step_type: str, cost: int):
        if step_type not in self._step_costs:
            self._step_types.put(step_type)

        self._step_costs[step_type] = cost

    def __getitem__(self, step_type: str):
        return self._step_costs[step_type]

    def __delitem__(self, step_type: str):
        # delete does not actually do delete but set zero
        if step_type in self._step_costs:
            self._step_costs[step_type] = 0

    def __contains__(self, step_type: str):
        return step_type in self._step_costs

    def __iter__(self):
        return self._step_types.__iter__()

    def __len__(self):
        return self._step_types.__len__()

    def items(self):
        for step_type in self._step_types:
            yield (step_type, self._step_costs[step_type])


class Governance(IconSystemScoreBase):
    _SCORE_STATUS = 'score_status'  # legacy
    _AUDITOR_LIST = 'auditor_list'
    _DEPLOYER_LIST = 'deployer_list'
    _SCORE_BLACK_LIST = 'score_black_list'
    _STEP_PRICE = 'step_price'
    _MAX_STEP_LIMITS = 'max_step_limits'
    _VERSION = 'version'
    _IMPORT_WHITE_LIST = 'import_white_list'
    _IMPORT_WHITE_LIST_KEYS = 'import_white_list_keys'
    _SERVICE_CONFIG = 'service_config'
    _AUDIT_STATUS = 'audit_status'
    _REJECT_STATUS = 'reject_status'
    _REVISION_CODE = 'revision_code'
    _REVISION_NAME = 'revision_name'

    @eventlog(indexed=1)
    def Accepted(self, txHash: str, warning: str):
        pass

    @eventlog(indexed=1)
    def Rejected(self, txHash: str, reason: str):
        pass

    @eventlog(indexed=1)
    def StepPriceChanged(self, stepPrice: int):
        pass

    @eventlog(indexed=1)
    def StepCostChanged(self, stepType: str, cost: int):
        pass

    @eventlog(indexed=1)
    def MaxStepLimitChanged(self, contextType: str, value: int):
        pass

    @eventlog(indexed=0)
    def AddImportWhiteListLog(self, addList: str, addCount: int):
        pass

    @eventlog(indexed=0)
    def RemoveImportWhiteListLog(self, removeList: str, removeCount: int):
        pass

    @eventlog(indexed=0)
    def UpdateServiceConfigLog(self, serviceFlag: int):
        pass

    @property
    def import_white_list_cache(self) -> dict:
        return self._get_import_white_list()

    @property
    def service_config(self) -> int:
        return self._service_config.get()

    @property
    def revision_code(self) -> int:
        return self._revision_code.get()

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        # self._score_status = DictDB(self._SCORE_STATUS, db, value_type=bytes, depth=3)
        self._auditor_list = ArrayDB(self._AUDITOR_LIST, db, value_type=Address)
        self._deployer_list = ArrayDB(self._DEPLOYER_LIST, db, value_type=Address)
        self._score_black_list = ArrayDB(self._SCORE_BLACK_LIST, db, value_type=Address)
        self._step_price = VarDB(self._STEP_PRICE, db, value_type=int)
        self._step_costs = StepCosts(db)
        self._max_step_limits = DictDB(self._MAX_STEP_LIMITS, db, value_type=int)
        self._version = VarDB(self._VERSION, db, value_type=str)
        self._import_white_list = DictDB(self._IMPORT_WHITE_LIST, db, value_type=str)
        self._import_white_list_keys = ArrayDB(self._IMPORT_WHITE_LIST_KEYS, db, value_type=str)
        self._service_config = VarDB(self._SERVICE_CONFIG, db, value_type=int)
        self._audit_status = DictDB(self._AUDIT_STATUS, db, value_type=bytes)
        self._reject_status = DictDB(self._REJECT_STATUS, db, value_type=bytes)
        self._revision_code = VarDB(self._REVISION_CODE, db, value_type=int)
        self._revision_name = VarDB(self._REVISION_NAME, db, value_type=str)

    def on_install(self, stepPrice: int = 10 ** 10) -> None:
        super().on_install()
        # add owner into initial auditor list
        Logger.debug(f'on_install: owner = "{self.owner}"', TAG)
        self._auditor_list.put(self.owner)
        # add owner into initial deployer list
        self._deployer_list.put(self.owner)
        # set initial step price
        self._step_price.set(stepPrice)
        # set initial step costs
        self._set_initial_step_costs()
        # set initial max step limits
        self._set_initial_max_step_limits()
        # set initial import white list
        self._set_initial_import_white_list()
        # set initial service config
        self._set_initial_service_config()
        # set initial revision
        self._set_initial_revision()

    def on_update(self) -> None:
        super().on_update()

        if self.is_less_than_target_version('0.0.2'):
            self._migrate_v0_0_2()
        if self.is_less_than_target_version('0.0.3'):
            self._migrate_v0_0_3()
        if self.is_less_than_target_version('0.0.4'):
            self._migrate_v0_0_4()
        if self.is_less_than_target_version('0.0.5'):
            self._migrate_v0_0_5()
        if self.is_less_than_target_version('0.0.6'):
            self._migrate_v0_0_6()

        self._version.set('0.0.6')

    def is_less_than_target_version(self, target_version: str) -> bool:
        last_version = self._version.get()
        return self._versions(last_version) < self._versions(target_version)

    def _migrate_v0_0_2(self):
        """
        This migration updates the step costs and max step limits
        """
        if len(self._step_costs) == 0:
            # migrates from old DB of step_costs.
            for step_type in INITIAL_STEP_COST_KEYS:
                if step_type in self._step_costs:
                    self._step_costs._step_types.put(step_type)

        self._set_initial_step_costs()

    def _migrate_v0_0_3(self):
        # set initial import white list
        self._set_initial_import_white_list()
        self._set_initial_service_config()

        self._set_initial_max_step_limits()

    def _migrate_v0_0_4(self):
        pass

    def _migrate_v0_0_5(self):
        self._set_initial_revision()

    def _migrate_v0_0_6(self):
        pass

    @staticmethod
    def _versions(version: str):
        parts = []
        if version is not None:
            for part in version.split("."):
                try:
                    parts.append(int(part))
                except ValueError:
                    pass
        return tuple(parts)

    @external(readonly=True)
    def getScoreStatus(self, address: Address) -> dict:
        # Governance
        if self.is_builtin_score(address):
            deploy_info = self.get_deploy_info(address)
            result = {
                CURRENT: {
                    STATUS: STATUS_ACTIVE
                }
            }
            if deploy_info.current_tx_hash is not None:
                result[CURRENT][DEPLOY_TX_HASH] = deploy_info.current_tx_hash
            return result

        deploy_info = self.get_deploy_info(address)
        if deploy_info is None:
            self.revert('SCORE not found')

        current_tx_hash = deploy_info.current_tx_hash
        next_tx_hash = deploy_info.next_tx_hash
        active = self.is_score_active(address)

        # install audit
        if current_tx_hash is None and next_tx_hash and active is False:
            reject_tx_hash = self._reject_status[next_tx_hash]
            if reject_tx_hash:
                result = {
                    NEXT: {
                        STATUS: STATUS_REJECTED,
                        DEPLOY_TX_HASH: next_tx_hash,
                        AUDIT_TX_HASH: reject_tx_hash
                    }}
            else:
                result = {
                    NEXT: {
                        STATUS: STATUS_PENDING,
                        DEPLOY_TX_HASH: next_tx_hash
                    }}
        elif current_tx_hash and next_tx_hash is None and active is True:
            audit_tx_hash = self._audit_status[current_tx_hash]
            result = {
                CURRENT: {
                    STATUS: STATUS_ACTIVE,
                    DEPLOY_TX_HASH: current_tx_hash
                }}
            if audit_tx_hash:
                result[CURRENT][AUDIT_TX_HASH] = audit_tx_hash
        else:
            # update audit
            if current_tx_hash and next_tx_hash and active is True:
                current_audit_tx_hash = self._audit_status[current_tx_hash]
                next_reject_tx_hash = self._reject_status[next_tx_hash]
                if next_reject_tx_hash:
                    result = {
                        CURRENT: {
                            STATUS: STATUS_ACTIVE,
                            DEPLOY_TX_HASH: current_tx_hash,
                            AUDIT_TX_HASH: current_audit_tx_hash
                        },
                        NEXT: {
                            STATUS: STATUS_REJECTED,
                            DEPLOY_TX_HASH: next_tx_hash,
                            AUDIT_TX_HASH: next_reject_tx_hash
                        }}
                else:
                    result = {
                        CURRENT: {
                            STATUS: STATUS_ACTIVE,
                            DEPLOY_TX_HASH: current_tx_hash,
                            AUDIT_TX_HASH: current_audit_tx_hash
                        },
                        NEXT: {
                            STATUS: STATUS_PENDING,
                            DEPLOY_TX_HASH: next_tx_hash
                        }}
            else:
                result = {}
        return result

    @external(readonly=True)
    def getStepPrice(self) -> int:
        return self._step_price.get()

    @external
    def setStepPrice(self, stepPrice: int):
        # only owner can set new step price
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')
        if stepPrice > 0:
            self._step_price.set(stepPrice)
            self.StepPriceChanged(stepPrice)

    @external
    def acceptScore(self, txHash: bytes, warning: str = ""):
        # check message sender
        Logger.debug(f'acceptScore: msg.sender = "{self.msg.sender}"', TAG)
        if self.msg.sender not in self._auditor_list:
            self.revert('Invalid sender: no permission')

        # check txHash
        tx_params = self.get_deploy_tx_params(txHash)
        if tx_params is None:
            self.revert('Invalid txHash: None')

        deploy_score_addr = tx_params.score_address
        deploy_info = self.get_deploy_info(deploy_score_addr)
        if txHash != deploy_info.next_tx_hash:
            self.revert('Invalid txHash: mismatch')

        next_audit_tx_hash = self._audit_status[txHash]
        if next_audit_tx_hash:
            self.revert('Invalid txHash: already accepted')

        next_reject_tx_hash = self._reject_status[txHash]
        if next_reject_tx_hash:
            self.revert('Invalid txHash: already rejected')

        self._deploy(txHash, deploy_score_addr)

        Logger.debug(f'acceptScore: score_address = "{tx_params.score_address}"', TAG)

        self._audit_status[txHash] = self.tx.hash

        self.Accepted('0x' + txHash.hex(), warning)

    def _deploy(self, tx_hash: bytes, score_addr: Address):
        owner = self.get_owner(score_addr)
        tmp_sender = self.msg.sender
        self.msg.sender = owner
        try:
            self.deploy(tx_hash)
        finally:
            self.msg.sender = tmp_sender

    @external
    def rejectScore(self, txHash: bytes, reason: str):
        # check message sender
        Logger.debug(f'rejectScore: msg.sender = "{self.msg.sender}"', TAG)
        if self.msg.sender not in self._auditor_list:
            self.revert('Invalid sender: no permission')

        # check txHash
        tx_params = self.get_deploy_tx_params(txHash)
        if tx_params is None:
            self.revert('Invalid txHash')

        next_audit_tx_hash = self._audit_status[txHash]
        if next_audit_tx_hash:
            self.revert('Invalid txHash: already accepted')

        next_reject_tx_hash = self._reject_status[txHash]
        if next_reject_tx_hash:
            self.revert('Invalid txHash: already rejected')

        Logger.debug(f'rejectScore: score_address = "{tx_params.score_address}", reason = {reason}', TAG)

        self._reject_status[txHash] = self.tx.hash

        self.Rejected('0x' + txHash.hex(), reason)

    @external
    def addAuditor(self, address: Address):
        if address.is_contract:
            self.revert(f'Invalid EOA Address: {address}')
        # check message sender, only owner can add new auditor
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')
        if address not in self._auditor_list:
            self._auditor_list.put(address)
        else:
            self.revert(f'Invalid address: already auditor')
        if DEBUG is True:
            self._print_auditor_list('addAuditor')

    @external
    def removeAuditor(self, address: Address):
        if address.is_contract:
            self.revert(f'Invalid EOA Address: {address}')
        if address not in self._auditor_list:
            self.revert('Invalid address: not in list')
        # check message sender
        if self.msg.sender != self.owner:
            if self.msg.sender != address:
                self.revert('Invalid sender: not yourself')
        # get the topmost value
        top = self._auditor_list.pop()
        if top != address:
            for i in range(len(self._auditor_list)):
                if self._auditor_list[i] == address:
                    self._auditor_list[i] = top
        if DEBUG is True:
            self._print_auditor_list('removeAuditor')

    def _print_auditor_list(self, header: str):
        Logger.debug(f'{header}: list len = {len(self._auditor_list)}', TAG)
        for auditor in self._auditor_list:
            Logger.debug(f' --- {auditor}', TAG)

    @external
    def addDeployer(self, address: Address):
        if address.is_contract:
            self.revert(f'Invalid EOA Address: {address}')
        # check message sender, only owner can add new deployer
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')
        if address not in self._deployer_list:
            self._deployer_list.put(address)
        else:
            self.revert(f'Invalid address: already deployer')
        if DEBUG is True:
            self._print_deployer_list('addDeployer')

    @external
    def removeDeployer(self, address: Address):
        if address.is_contract:
            self.revert(f'Invalid EOA Address: {address}')
        if address not in self._deployer_list:
            self.revert('Invalid address: not in list')
        # check message sender
        if self.msg.sender != self.owner:
            if self.msg.sender != address:
                self.revert('Invalid sender: not yourself')
        # get the topmost value
        top = self._deployer_list.pop()
        if top != address:
            for i in range(len(self._deployer_list)):
                if self._deployer_list[i] == address:
                    self._deployer_list[i] = top
        if DEBUG is True:
            self._print_deployer_list('removeDeployer')

    @external(readonly=True)
    def isDeployer(self, address: Address) -> bool:
        Logger.debug(f'isDeployer address: {address}', TAG)
        return address in self._deployer_list

    def _print_deployer_list(self, header: str):
        Logger.debug(f'{header}: list len = {len(self._deployer_list)}', TAG)
        for deployer in self._deployer_list:
            Logger.debug(f' --- {deployer}', TAG)

    @external
    def addToScoreBlackList(self, address: Address):
        if not address.is_contract:
            self.revert(f'Invalid SCORE Address: {address}')
        # check message sender, only owner can add new blacklist
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')
        if self.address == address:
            self.revert("can't add myself")
        if address not in self._score_black_list:
            self._score_black_list.put(address)
        else:
            self.revert('Invalid address: already SCORE blacklist')
        if DEBUG is True:
            self._print_black_list('addScoreToBlackList')

    @external
    def removeFromScoreBlackList(self, address: Address):
        if not address.is_contract:
            self.revert(f'Invalid SCORE Address: {address}')
        # check message sender, only owner can remove from blacklist
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')
        if address not in self._score_black_list:
            self.revert('Invalid address: not in list')
        # get the topmost value
        top = self._score_black_list.pop()
        if top != address:
            for i in range(len(self._score_black_list)):
                if self._score_black_list[i] == address:
                    self._score_black_list[i] = top
        if DEBUG is True:
            self._print_black_list('removeScoreFromBlackList')

    @external(readonly=True)
    def isInScoreBlackList(self, address: Address) -> bool:
        Logger.debug(f'isInBlackList address: {address}', TAG)
        return address in self._score_black_list

    def _print_black_list(self, header: str):
        Logger.debug(f'{header}: list len = {len(self._score_black_list)}', TAG)
        for addr in self._score_black_list:
            Logger.debug(f' --- {addr}', TAG)

    def _set_initial_step_costs(self):
        initial_costs = {
            STEP_TYPE_DEFAULT: 100_000,
            STEP_TYPE_CONTRACT_CALL: 25_000,
            STEP_TYPE_CONTRACT_CREATE: 1_000_000_000,
            STEP_TYPE_CONTRACT_UPDATE: 1_600_000_000,
            STEP_TYPE_CONTRACT_DESTRUCT: -70_000,
            STEP_TYPE_CONTRACT_SET: 30_000,
            STEP_TYPE_GET: 0,
            STEP_TYPE_SET: 320,
            STEP_TYPE_REPLACE: 80,
            STEP_TYPE_DELETE: -240,
            STEP_TYPE_INPUT: 200,
            STEP_TYPE_EVENT_LOG: 100,
            STEP_TYPE_API_CALL: 0
        }
        for key, value in initial_costs.items():
            self._step_costs[key] = value

    def _set_initial_max_step_limits(self):
        self._max_step_limits[CONTEXT_TYPE_INVOKE] = 2_500_000_000
        self._max_step_limits[CONTEXT_TYPE_QUERY] = 50_000_000

    def _set_initial_revision(self):
        self._revision_code.set(2)
        self._revision_name.set("1.1.2")

    @external(readonly=True)
    def getStepCosts(self) -> dict:
        result = {}
        for key, value in self._step_costs.items():
            result[key] = value
        return result

    @external
    def setStepCost(self, stepType: str, cost: int):
        # only owner can set new step cost
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')
        if cost < 0:
            if stepType != STEP_TYPE_CONTRACT_DESTRUCT and \
                    stepType != STEP_TYPE_DELETE:
                self.revert(f'Invalid step cost: {stepType}, {cost}')
        self._step_costs[stepType] = cost
        self.StepCostChanged(stepType, cost)

    @external(readonly=True)
    def getMaxStepLimit(self, contextType: str) -> int:
        return self._max_step_limits[contextType]

    @external
    def setMaxStepLimit(self, contextType: str, value: int):
        # only owner can set new context type value
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')
        if value < 0:
            self.revert('Invalid value: negative number')
        if contextType == CONTEXT_TYPE_INVOKE or contextType == CONTEXT_TYPE_QUERY:
            self._max_step_limits[contextType] = value
            self.MaxStepLimitChanged(contextType, value)
        else:
            self.revert("Invalid context type")

    @external(readonly=True)
    def getVersion(self) -> str:
        return self._version.get()

    def _set_initial_import_white_list(self):
        key = "iconservice"
        # if iconservice has no value set ALL
        if self._import_white_list[key] == "":
            self._import_white_list[key] = "*"
            self._import_white_list_keys.put(key)

    @external
    def addImportWhiteList(self, importStmt: str):
        # only owner can add import white list
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')
        import_stmt_dict = {}
        try:
            import_stmt_dict: dict = self._check_import_stmt(importStmt)
        except Exception as e:
            self.revert(f'Invalid import statement: {e}')
        # add to import white list
        log_entry = []
        for key, value in import_stmt_dict.items():
            old_value: str = self._import_white_list[key]
            if old_value == "*":
                # no need to add
                continue

            if len(value) == 0:
                # set import white list as ALL
                self._import_white_list[key] = "*"

                # add to import white list keys
                if old_value == "":
                    self._import_white_list_keys.put(key)

                # make added item list for eventlog
                log_entry.append((key, value))
            elif old_value == "":
                # set import white list
                self._import_white_list[key] = ','.join(value)
                # add to import white list keys
                self._import_white_list_keys.put(key)
                # make added item list for eventlog
                log_entry.append((key, value))
            else:
                old_value_list = old_value.split(',')
                new_value = []
                for v in value:
                    if v not in old_value_list:
                        new_value.append(v)

                # set import white list
                self._import_white_list[key] = f'{old_value},{",".join(new_value)}'

                # make added item list for eventlog
                log_entry.append((key, new_value))

        # make eventlog
        if len(log_entry):
            self.AddImportWhiteListLog(str(log_entry), len(log_entry))

        if DEBUG is True:
            Logger.debug(f'checking added item ({importStmt}): {self.isInImportWhiteList(importStmt)}')

    @external
    def removeImportWhiteList(self, importStmt: str):
        # only owner can add import white list
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')

        import_stmt_dict = {}
        try:
            import_stmt_dict: dict = self._check_import_stmt(importStmt)
        except Exception as e:
            self.revert(f'Invalid import statement: {e}')

        # remove from import white list
        log_entry = []
        for key, value in import_stmt_dict.items():
            old_value: str = self._import_white_list[key]
            if old_value == "*":
                if len(value) == 0:
                    # remove import white list
                    self._remove_import_white_list(key)

                    # make added item list for eventlog
                    log_entry.append((key, value))
                continue

            if len(value) == 0:
                # remove import white list
                self._remove_import_white_list(key)

                # make added item list for eventlog
                log_entry.append((key, value))

                # add to import white list keys
                self._import_white_list_keys.put(key)
            else:
                old_value_list = old_value.split(',')
                remove_value = []
                new_value = []
                for v in old_value_list:
                    if v in value:
                        remove_value.append(v)
                    else:
                        new_value.append(v)

                # set import white list
                if len(new_value):
                    self._import_white_list[key] = f'{",".join(new_value)}'
                else:
                    self._remove_import_white_list(key)

                # make added item list for eventlog
                log_entry.append((key, remove_value))

        if len(log_entry):
            # make eventlog
            self.AddImportWhiteListLog(str(log_entry), len(log_entry))

        if DEBUG is True:
            Logger.debug(f'checking removed item ({importStmt}): {self.isInImportWhiteList(importStmt)}')

    @external(readonly=True)
    def isInImportWhiteList(self, importStmt: str) -> bool:
        try:
            import_stmt_dict: dict = self._check_import_stmt(importStmt)
        except Exception as e:
            raise ValueError(f'{e}')

        cache_import_white_list = self._get_import_white_list()
        for key, value in import_stmt_dict.items():
            old_value: list = cache_import_white_list.get(key, None)
            if old_value is None:
                return False

            if old_value[0] == "*":
                # import white list has ALL. See next key
                continue

            if len(value) == 0:
                # input is ALL
                return False

            for v in value:
                if v not in old_value:
                    return False

        if DEBUG is True:
            Logger.debug(f'({importStmt}) is in import white list')
        return True

    @staticmethod
    def _check_import_stmt(import_stmt: str) -> dict:
        Logger.debug(f'check_import_stmt: {import_stmt}')
        import_stmt_dict: dict = json_loads(import_stmt.replace("\'", "\""))
        for key, value in import_stmt_dict.items():
            if not isinstance(key, str):
                raise TypeError("Key must be of type `str`")

            if not isinstance(value, list):
                raise TypeError("Value must be of type `list`")
            else:
                for v in value:
                    if not isinstance(v, str):
                        raise TypeError("Element of value must be of type `str`")

        Logger.debug(f'check_import_stmt_dict: {import_stmt_dict}')
        return import_stmt_dict

    def _get_import_white_list(self) -> dict:
        whitelist = {}
        for v in self._import_white_list_keys:
            values: str = self._import_white_list[v]
            whitelist[v] = values.split(',')

        return whitelist

    def _remove_import_white_list(self, key: str):
        # remove from import white list
        self._import_white_list.remove(key)

        # remove from import white list keys
        top = self._import_white_list_keys.pop()
        if top != key:
            for i in range(len(self._import_white_list_keys)):
                if self._import_white_list_keys[i] == key:
                    self._import_white_list_keys[i] = top

    def _set_initial_service_config(self):
        self._service_config.set(self.get_icon_service_flag() | 8)

    @external
    def updateServiceConfig(self, serviceFlag: int):
        # only owner can add import white list
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')

        if serviceFlag < 0:
            self.revert(f'updateServiceConfig: serviceFlag({serviceFlag}) < 0')

        max_flag = 0
        for flag in IconServiceFlag:
            max_flag |= flag

        if serviceFlag > max_flag:
            self.revert(f'updateServiceConfig: serviceFlag({serviceFlag}) > max_flag({max_flag})')

        prev_service_config = self._service_config.get()
        if prev_service_config != serviceFlag:
            self._service_config.set(serviceFlag)
            self.UpdateServiceConfigLog(serviceFlag)
            if DEBUG is True:
                Logger.debug(f'updateServiceConfig (prev: {prev_service_config} flag: {serviceFlag})')
        else:
            if DEBUG is True:
                Logger.debug(f'updateServiceConfig not update ({serviceFlag})')

    @external(readonly=True)
    def getServiceConfig(self) -> dict:
        table = {}
        service_flag = self._service_config.get()

        for flag in IconServiceFlag:
            if service_flag & flag == flag:
                table[flag.name] = True
            else:
                table[flag.name] = False
        return table

    @external
    def setRevision(self, code: int, name: str):
        # only owner can add import white list
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')

        prev_code = self._revision_code.get()
        if code < prev_code:
            self.revert(f"can't decrease code")

        self._revision_code.set(code)
        self._revision_name.set(name)

    @external(readonly=True)
    def getRevision(self) -> dict:
        return {'code': self._revision_code.get(), 'name': self._revision_name.get()}
