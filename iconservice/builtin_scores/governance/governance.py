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


class Governance(IconScoreBase):

    _SCORE_STATUS = 'score_status'
    _AUDITOR_LIST = 'auditor_list'
    _STEP_PRICE = 'step_price'

    # TODO: replace with real func
    _MAP_ADDRESS = {
        'e0f6dc6607aa9b5550cd1e6d57549f67fe9718654cde15258922d0f88ff58b27': 'cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32',
        'e22222222222222250cd1e6d57549f67fe9718654cde15258922d0f88ff58b27': 'cx222222222f5b45bfaea8cff1d8232fbb6122ec32',
    }
    _MAP_TXHASH = {
        'cxb0776ee37f5b45bfaea8cff1d8232fbb6122ec32': '0xe0f6dc6607aa9b5550cd1e6d57549f67fe9718654cde15258922d0f88ff58b27',
        'cx222222222f5b45bfaea8cff1d8232fbb6122ec32': '0xe22222222222222250cd1e6d57549f67fe9718654cde15258922d0f88ff58b27',
    }

    @eventlog(indexed=1)
    def Accepted(self, tx_hash: str):
        pass

    @eventlog(indexed=1)
    def Rejected(self, tx_hash: str):
        pass

    @eventlog(indexed=1)
    def StepPriceChanged(self, step_price: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._score_status = DictDB(self._SCORE_STATUS, db, value_type=bytes, depth=3)
        self._auditor_list = ArrayDB(self._AUDITOR_LIST, db, value_type=Address)
        self._step_price = VarDB(self._STEP_PRICE, db, value_type=int)

    def on_install(self, stepPrice: int = 10 ** 12) -> None:
        super().on_install()
        # add owner into initial auditor list
        self._auditor_list.put(self.owner)
        # set initial step price
        self._step_price.set(stepPrice)

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
                    status[key] = '0x' + value.hex()
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
        # TODO: replace with real func
        tx_hash: str = None
        if str(address) in self._MAP_TXHASH:
            tx_hash = self._MAP_TXHASH[str(address)]
        else:
            self.revert('SCORE not found')
        result = {}
        _current = self._get_current_status(address)
        count1, status = self._fill_status_with_str(_current)
        if count1 > 0:
            result[CURRENT] = status
        _next = self._get_next_status(address)
        count2, status = self._fill_status_with_str(_next)
        if count2 > 0:
            result[NEXT] = status
        if count1 + count2 == 0:
            # there is no status information, build initial status
            status = {
                STATUS: STATUS_PENDING,
                DEPLOY_TX_HASH: tx_hash
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
        # TODO: replace with real func
        score_address: Address = None
        hex_string = txHash.hex()
        if hex_string in self._MAP_ADDRESS:
            score_address = Address.from_string(self._MAP_ADDRESS[hex_string])
        else:
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
        self.Accepted('0x' + hex_string)

    @external
    def rejectScore(self, txHash: bytes, reason: str):
        # check message sender
        Logger.debug(f'rejectScore: msg.sender = "{self.msg.sender}"', TAG)
        if self.msg.sender not in self._auditor_list:
            self.revert('Invalid sender: no permission')
        # check txHash
        # TODO: replace with real func
        score_address: Address = None
        hex_string = txHash.hex()
        if hex_string in self._MAP_ADDRESS:
            score_address = Address.from_string(self._MAP_ADDRESS[hex_string])
        else:
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
        self.Rejected('0x' + hex_string)

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
