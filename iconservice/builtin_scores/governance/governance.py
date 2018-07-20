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
STEP_TYPE_SET = 'set'
STEP_TYPE_REPLACE = 'replace'
STEP_TYPE_DELETE = 'delete'
STEP_TYPE_INPUT = 'input'
STEP_TYPE_EVENT_LOG = 'eventLog'
VALID_STEP_COST_KEYS = [STEP_TYPE_DEFAULT,
                        STEP_TYPE_CONTRACT_CALL, STEP_TYPE_CONTRACT_CREATE, STEP_TYPE_CONTRACT_UPDATE,
                        STEP_TYPE_CONTRACT_DESTRUCT, STEP_TYPE_CONTRACT_SET,
                        STEP_TYPE_SET, STEP_TYPE_REPLACE, STEP_TYPE_DELETE, STEP_TYPE_INPUT,
                        STEP_TYPE_EVENT_LOG]


class Governance(IconScoreBase):

    _SCORE_STATUS = 'score_status'
    _AUDITOR_LIST = 'auditor_list'
    _STEP_PRICE = 'step_price'
    _STEP_COSTS = 'step_costs'

    @eventlog(indexed=1)
    def Accepted(self, tx_hash: str):
        pass

    @eventlog(indexed=1)
    def Rejected(self, tx_hash: str):
        pass

    @eventlog(indexed=1)
    def StepPriceChanged(self, step_price: int):
        pass

    @eventlog(indexed=1)
    def StepCostChanged(self, step_type: str, cost: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._score_status = DictDB(self._SCORE_STATUS, db, value_type=bytes, depth=3)
        self._auditor_list = ArrayDB(self._AUDITOR_LIST, db, value_type=Address)
        self._step_price = VarDB(self._STEP_PRICE, db, value_type=int)
        self._step_costs = DictDB(self._STEP_COSTS, db, value_type=int)

    def on_install(self, stepPrice: int = 10 ** 12) -> None:
        super().on_install()
        # add owner into initial auditor list
        Logger.debug(f'on_install: owner = "{self.owner}"', TAG)
        self._auditor_list.put(self.owner)
        # set initial step price
        self._step_price.set(stepPrice)
        # set initial step costs
        self._set_initial_step_costs()

    def on_update(self) -> None:
        super().on_update()

    def _get_current_status(self, score_address: Address):
        return self._score_status[score_address][CURRENT]

    def _get_next_status(self, score_address: Address):
        return self._score_status[score_address][NEXT]

    @staticmethod
    def _fill_status_with_str(db: DictDB):
        count = 0
        status = {}
        for key in VALID_STATUS_KEYS:
            value: bytes = db[key]
            if value:
                if key == STATUS:
                    status[key] = value.decode()
                else:
                    status[key] = value
                count += 1
        return count, status

    @staticmethod
    def _save_status(db: DictDB, status: dict) -> None:
        for key in VALID_STATUS_KEYS:
            value: bytes = status[key]
            if value:
                db[key] = value

    @staticmethod
    def _remove_status(db: DictDB) -> None:
        for key in VALID_STATUS_KEYS:
            value = db[key]
            if value:
                del db[key]

    @external(readonly=True)
    def getScoreStatus(self, address: Address) -> dict:
        # check score address
        current_tx_hash, next_tx_hash = self.get_tx_hashes_by_score_address(address)
        if current_tx_hash is None and next_tx_hash is None:
            self.revert('SCORE not found')
        result = {}
        build_initial_status = False
        # get current status
        _current = self._get_current_status(address)
        count1, status = self._fill_status_with_str(_current)
        if count1 > 0:
            if current_tx_hash is None:
                self.revert('current_tx_hash is None')
            if current_tx_hash != status[DEPLOY_TX_HASH]:
                self.revert('Current deploy tx mismatch')
            # audit has been performed (accepted)
            result[CURRENT] = status
        # get next status
        _next = self._get_next_status(address)
        count2, status = self._fill_status_with_str(_next)
        if count2 > 0:
            # check if another pending tx has been arrived
            if next_tx_hash is not None and \
                    next_tx_hash != status[DEPLOY_TX_HASH]:
                build_initial_status = True
            else:
                # audit has been performed (rejected)
                result[NEXT] = status
        else:
            if next_tx_hash is not None:
                build_initial_status = True
        # there is no information, build initial status
        if build_initial_status:
            status = {
                STATUS: STATUS_PENDING,
                DEPLOY_TX_HASH: next_tx_hash
            }
            result[NEXT] = status
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
    def acceptScore(self, txHash: bytes):
        # check message sender
        Logger.debug(f'acceptScore: msg.sender = "{self.msg.sender}"', TAG)
        if self.msg.sender not in self._auditor_list:
            self.revert('Invalid sender: no permission')
        # check txHash
        score_address = self.get_score_address_by_tx_hash(txHash)
        if score_address is None:
            self.revert('Invalid txHash')
        Logger.debug(f'acceptScore: score_address = "{score_address}"', TAG)
        # check next: it should be 'pending'
        result = self.getScoreStatus(score_address)
        try:
            next_status = result[NEXT][STATUS]
            if next_status != STATUS_PENDING:
                self.revert(f'Invalid status: next is {next_status}')
        except KeyError:
            self.revert('Invalid status: no next status')
        # next: pending -> null
        _next = self._get_next_status(score_address)
        self._remove_status(_next)
        # current: null -> active
        _current = self._get_current_status(score_address)
        status = {
            STATUS: STATUS_ACTIVE,
            DEPLOY_TX_HASH: txHash,
            AUDIT_TX_HASH: self.tx.hash
        }
        self._save_status(_current, status)
        self.deploy(txHash)
        self.Accepted('0x' + txHash.hex())

    @external
    def rejectScore(self, txHash: bytes, reason: str):
        # check message sender
        Logger.debug(f'rejectScore: msg.sender = "{self.msg.sender}"', TAG)
        if self.msg.sender not in self._auditor_list:
            self.revert('Invalid sender: no permission')
        # check txHash
        score_address = self.get_score_address_by_tx_hash(txHash)
        if score_address is None:
            self.revert('Invalid txHash')
        Logger.debug(f'rejectScore: score_address = "{score_address}", reason = {reason}', TAG)
        # check next: it should be 'pending'
        result = self.getScoreStatus(score_address)
        try:
            next_status = result[NEXT][STATUS]
            if next_status != STATUS_PENDING:
                self.revert(f'Invalid status: next is {next_status}')
        except KeyError:
            self.revert('Invalid status: no next status')
        # next: pending -> rejected
        _next = self._get_next_status(score_address)
        status = {
            STATUS: STATUS_REJECTED,
            DEPLOY_TX_HASH: txHash,
            AUDIT_TX_HASH: self.tx.hash
        }
        self._save_status(_next, status)
        self.Rejected('0x' + txHash.hex())

    @external
    def addAuditor(self, address: Address):
        # check message sender, only owner can add new auditor
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')
        if address not in self._auditor_list:
            self._auditor_list.put(address)
        if DEBUG is True:
            self._print_auditor_list('addAuditor')

    @external
    def removeAuditor(self, address: Address):
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

    def _set_initial_step_costs(self):
        initial_costs = {
            STEP_TYPE_DEFAULT: 4000,
            STEP_TYPE_CONTRACT_CALL: 1500,
            STEP_TYPE_CONTRACT_CREATE: 20000,
            STEP_TYPE_CONTRACT_UPDATE: 8000,
            STEP_TYPE_CONTRACT_DESTRUCT: -7000,
            STEP_TYPE_CONTRACT_SET: 1000,
            STEP_TYPE_SET: 20,
            STEP_TYPE_REPLACE: 5,
            STEP_TYPE_DELETE: -15,
            STEP_TYPE_INPUT: 20,
            STEP_TYPE_EVENT_LOG: 10
        }
        for key in VALID_STEP_COST_KEYS:
            value: int = initial_costs[key]
            self._step_costs[key] = value

    @external(readonly=True)
    def getStepCosts(self) -> dict:
        result = {}
        for key in VALID_STEP_COST_KEYS:
            result[key] = self._step_costs[key]
        return result

    @external
    def setStepCost(self, stepType: str, cost: int):
        # only owner can set new step cost
        if self.msg.sender != self.owner:
            self.revert('Invalid sender: not owner')
        if stepType not in VALID_STEP_COST_KEYS:
            self.revert(f'Invalid step type: {stepType}')
        if cost < 0:
            if stepType != STEP_TYPE_CONTRACT_DESTRUCT and \
                    stepType != STEP_TYPE_DELETE:
                self.revert(f'Invalid step cost: {stepType}, {cost}')
        self._step_costs[stepType] = cost
        self.StepCostChanged(stepType, cost)
