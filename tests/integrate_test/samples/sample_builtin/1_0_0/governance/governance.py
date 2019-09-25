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

from .network_proposal import NetworkProposal, NetworkProposalType, MaliciousScoreType

TAG = 'Governance'
DEBUG = False

CURRENT = 'current'
NEXT = 'next'
STATUS = 'status'
DEPLOY_TX_HASH = 'deployTxHash'
AUDIT_TX_HASH = 'auditTxHash'
DEPOSIT_INFO = 'depositInfo'
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

ZERO_TX_HASH = bytes(32)


def _is_tx_hash_valid(tx_hash: bytes) -> bool:
    return tx_hash is not None and tx_hash != ZERO_TX_HASH


class SystemInterface(InterfaceScore):
    @interface
    def getScoreDepositInfo(self, address: Address) -> dict: pass


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
    def Accepted(self, txHash: str):
        pass

    @eventlog(indexed=1)
    def Rejected(self, txHash: str, reason: str):
        pass

    @eventlog(indexed=1)
    def StepPriceChanged(self, stepPrice: int):
        pass

    @eventlog(indexed=0)
    def RevisionChanged(self, revisionCode: int, revisionName: str):
        pass

    @eventlog(indexed=0)
    def AddMaliciousScore(self, address: Address):
        pass

    @eventlog(indexed=0)
    def RemoveMaliciousScore(self, address: Address):
        pass

    @eventlog(indexed=0)
    def DisqualifyPRep(self, address: Address):
        pass

    @eventlog(indexed=0)
    def RegisterNetworkProposal(self, title: str, description: str, type: int, value: bytes, proposer: Address):
        pass

    @eventlog(indexed=0)
    def CancelNetworkProposal(self, id: bytes):
        pass

    @eventlog(indexed=0)
    def VoteNetworkProposal(self, id: bytes, vote: int, voter: Address):
        pass

    @eventlog(indexed=0)
    def NetworkProposalApproved(self, id: bytes):
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
        self._network_proposal = NetworkProposal(db)

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

        self._version.set('0.0.7')

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
        self._set_initial_max_step_limits()
        self._set_initial_import_white_list()
        self._set_initial_service_config()

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
            revert('SCORE not found')

        current_tx_hash = deploy_info.current_tx_hash
        next_tx_hash = deploy_info.next_tx_hash
        active = self.is_score_active(address)

        # install audit
        if not _is_tx_hash_valid(current_tx_hash) \
                and _is_tx_hash_valid(next_tx_hash) \
                and active is False:
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
        elif _is_tx_hash_valid(current_tx_hash) \
                and not _is_tx_hash_valid(next_tx_hash) \
                and active is True:
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
            if _is_tx_hash_valid(current_tx_hash) \
                    and _is_tx_hash_valid(next_tx_hash) \
                    and active is True:
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

        system = self.create_interface_score(ZERO_SCORE_ADDRESS, SystemInterface)
        deposit_info = system.getScoreDepositInfo(address)
        if deposit_info is not None:
            result[DEPOSIT_INFO] = deposit_info

        return result

    @external(readonly=True)
    def getStepPrice(self) -> int:
        return self._step_price.get()

    @external
    def acceptScore(self, txHash: bytes):
        # check message sender
        Logger.debug(f'acceptScore: msg.sender = "{self.msg.sender}"', TAG)
        if self.msg.sender not in self._auditor_list:
            revert('Invalid sender: no permission')

        # check txHash
        tx_params = self.get_deploy_tx_params(txHash)
        if tx_params is None:
            revert('Invalid txHash: None')

        deploy_score_addr = tx_params.score_address
        deploy_info = self.get_deploy_info(deploy_score_addr)
        if txHash != deploy_info.next_tx_hash:
            revert('Invalid txHash: mismatch')

        next_audit_tx_hash = self._audit_status[txHash]
        if next_audit_tx_hash:
            revert('Invalid txHash: already accepted')

        next_reject_tx_hash = self._reject_status[txHash]
        if next_reject_tx_hash:
            revert('Invalid txHash: already rejected')

        self._deploy(txHash, deploy_score_addr)

        Logger.debug(f'acceptScore: score_address = "{tx_params.score_address}"', TAG)

        self._audit_status[txHash] = self.tx.hash

        self.Accepted('0x' + txHash.hex())

    def _deploy(self, tx_hash: bytes, score_addr: Address):
        owner = self.get_owner(score_addr)
        tmp_sender = self.msg.sender
        self.msg.sender = owner
        try:
            self._context.deploy(tx_hash)
        finally:
            self.msg.sender = tmp_sender

    @external
    def rejectScore(self, txHash: bytes, reason: str):
        # check message sender
        Logger.debug(f'rejectScore: msg.sender = "{self.msg.sender}"', TAG)
        if self.msg.sender not in self._auditor_list:
            revert('Invalid sender: no permission')

        # check txHash
        tx_params = self.get_deploy_tx_params(txHash)
        if tx_params is None:
            revert('Invalid txHash')

        next_audit_tx_hash = self._audit_status[txHash]
        if next_audit_tx_hash:
            revert('Invalid txHash: already accepted')

        next_reject_tx_hash = self._reject_status[txHash]
        if next_reject_tx_hash:
            revert('Invalid txHash: already rejected')

        Logger.debug(f'rejectScore: score_address = "{tx_params.score_address}", reason = {reason}', TAG)

        self._reject_status[txHash] = self.tx.hash

        self.Rejected('0x' + txHash.hex(), reason)

    @external
    def addAuditor(self, address: Address):
        if address.is_contract:
            revert(f'Invalid EOA Address: {address}')
        # check message sender, only owner can add new auditor
        if self.msg.sender != self.owner:
            revert('Invalid sender: not owner')
        if address not in self._auditor_list:
            self._auditor_list.put(address)
        else:
            revert(f'Invalid address: already auditor')
        if DEBUG is True:
            self._print_auditor_list('addAuditor')

    @external
    def removeAuditor(self, address: Address):
        if address.is_contract:
            revert(f'Invalid EOA Address: {address}')
        if address not in self._auditor_list:
            revert('Invalid address: not in list')
        # check message sender
        if self.msg.sender != self.owner:
            if self.msg.sender != address:
                revert('Invalid sender: not yourself')
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

    @external(readonly=True)
    def isDeployer(self, address: Address) -> bool:
        Logger.debug(f'isDeployer address: {address}', TAG)
        return address in self._deployer_list

    def _addToScoreBlackList(self, address: Address):
        if not address.is_contract:
            revert(f'Invalid SCORE Address: {address}')

        if self.address == address:
            revert("can't add myself")

        if address not in self._score_black_list:
            self._score_black_list.put(address)
            self.AddMaliciousScore(address)
        else:
            revert('Invalid address: already SCORE blacklist')

        if DEBUG is True:
            self._print_black_list('addScoreToBlackList')

    def _removeFromScoreBlackList(self, address: Address):
        if not address.is_contract:
            revert(f'Invalid SCORE Address: {address}')

        if address not in self._score_black_list:
            revert('Invalid address: not in list')

        # get the topmost value
        top = self._score_black_list.pop()
        if top != address:
            for i in range(len(self._score_black_list)):
                if self._score_black_list[i] == address:
                    self._score_black_list[i] = top

        self.RemoveMaliciousScore(address)

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

    @external(readonly=True)
    def getMaxStepLimit(self, contextType: str) -> int:
        return self._max_step_limits[contextType]

    @external(readonly=True)
    def getVersion(self) -> str:
        return self._version.get()

    def _set_initial_import_white_list(self):
        key = "iconservice"
        # if iconservice has no value set ALL
        if self._import_white_list[key] == "":
            self._import_white_list[key] = "*"
            self._import_white_list_keys.put(key)

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

    def _set_revision(self, code: str, name: str):
        # check message sender, only main P-Rep can add new blacklist
        main_preps, _ = get_main_prep_info()
        if not self._check_main_prep(self.msg.sender, main_preps):
            revert("No permission - only for main prep")

        code = int(code, 16)
        prev_code = self._revision_code.get()
        if code < prev_code:
            revert(f"can't decrease code")

        self._revision_code.set(code)
        self._revision_name.set(name)
        self.RevisionChanged(code, name)

    @external(readonly=True)
    def getRevision(self) -> dict:
        return {'code': self._revision_code.get(), 'name': self._revision_name.get()}

    @external
    def registerProposal(self, title: str, description: str, type: int, value: bytes):
        """ Register a Proposal with information like description, type and value by main prep

        :param title: title of the proposal
        :param description: description of the proposal
        :param type: proposal type
        :param value: encoded value
        :return: None
        """
        main_preps, expire_block_height = get_main_prep_info()

        if not self._check_main_prep(self.msg.sender, main_preps):
            revert("No permission - only for main prep")

        if expire_block_height < self.block_height:
            revert("Invalid main P-Rep term information")

        value_in_dict = json_loads(value.decode())
        self._network_proposal.register_proposal(self.tx.hash, self.msg.sender, self.block_height, expire_block_height,
                                                 title, description, type, value_in_dict, main_preps)

        self.RegisterNetworkProposal(title, description, type, value, self.msg.sender)

    @external
    def cancelProposal(self, id: bytes):
        """ Cancel Proposal if it have not been approved

        :param id: transaction hash to generate when registering proposal
        :return: None
        """
        main_preps, _ = get_main_prep_info()

        if not self._check_main_prep(self.msg.sender, main_preps):
            revert("No permission - only for main prep")

        self._network_proposal.cancel_proposal(id, self.msg.sender, self.block_height)

        self.CancelNetworkProposal(id)

    @external
    def voteProposal(self, id: bytes, vote: int):
        """ Vote for Proposal - agree or disagree

        :param id: transaction hash to generate when registering proposal
        :param vote: agree(1) or disagree(0)
        :return: None
        """
        main_preps, _ = get_main_prep_info()

        if not self._check_main_prep(self.msg.sender, main_preps):
            revert("No permission - only for main prep")

        approved, proposal_type, value = self._network_proposal.vote_proposal(id, self.msg.sender,
                                                                              vote,
                                                                              self.block_height,
                                                                              self.tx.hash,
                                                                              self.tx.timestamp,
                                                                              main_preps)

        self.VoteNetworkProposal(id, vote, self.msg.sender)

        if approved:
            self.NetworkProposalApproved(id)

            # value dict has str key, value. convert str value to appropriate type to use
            if proposal_type == NetworkProposalType.TEXT:
                return
            elif proposal_type == NetworkProposalType.REVISION:
                self._set_revision(**value)
            elif proposal_type == NetworkProposalType.MALICIOUS_SCORE:
                self._malicious_score(**value)
            elif proposal_type == NetworkProposalType.PREP_DISQUALIFICATION:
                self._disqualify_prep(**value)
            elif proposal_type == NetworkProposalType.STEP_PRICE:
                self._set_step_price(**value)

    @external(readonly=True)
    def getProposal(self, id: bytes) -> dict:
        """ Get Proposal info as dict

        :param id: transaction hash to generate when registering proposal
        :return: proposal information in dict
        """
        proposal_info = self._network_proposal.get_proposal(id, self.block_height)
        return proposal_info

    @external(readonly=True)
    def getProposals(self, type: int = None, status: int = None) -> dict:
        """ Get all of proposals in list

        :param type: type of network proposal to filter (optional)
        :param status: status of network proposal to filter (optional)
        :return: proposal list in dict
        """
        return self._network_proposal.get_proposals(self.block_height, type, status)

    def _check_main_prep(self, address: 'Address', main_preps: list) -> bool:
        """ Check if the address is main prep

        :param address: address to be checked
        :param main_preps: list of main preps
        :return: bool value to be checked if it is one of main preps or not
        """
        for prep in main_preps:
            if prep.address == address:
                return True
        return False

    def _malicious_score(self, address: str, type: str):
        # check message sender, only main P-Rep can modify SCORE blacklist
        main_preps, _ = get_main_prep_info()
        if not self._check_main_prep(self.msg.sender, main_preps):
            revert("No permission - only for main prep")

        converted_address = Address.from_string(address)
        converted_type = int(type, 16)
        if converted_type == MaliciousScoreType.FREEZE:
            self._addToScoreBlackList(converted_address)
        elif converted_type == MaliciousScoreType.UNFREEZE:
            self._removeFromScoreBlackList(converted_address)

    def _disqualify_prep(self, address: str):
        # check message sender, only main P-Rep can disqualify P-Rep
        main_preps, _ = get_main_prep_info()
        if not self._check_main_prep(self.msg.sender, main_preps):
            revert("No permission - only for main prep")

        address = Address.from_string(address)

        self.disqualify_prep(address)
        self.DisqualifyPRep(address)

    def _set_step_price(self, value: str):
        # check message sender, only main P-Rep can set step price
        main_preps, _ = get_main_prep_info()
        if not self._check_main_prep(self.msg.sender, main_preps):
            revert("No permission - only for main prep")

        step_price = int(value, 16)
        if step_price > 0:
            self._step_price.set(step_price)
            self.StepPriceChanged(step_price)
