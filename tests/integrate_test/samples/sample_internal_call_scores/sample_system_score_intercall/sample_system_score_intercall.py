from iconservice import *


class SampleSystemScoreInterCall(IconScoreBase):
    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self.use_interface = VarDB("use_interface", db, value_type=bool)

    def on_install(self, use_interface: bool) -> None:
        super().on_install()
        self.use_interface.set(use_interface)

    def on_update(self) -> None:
        super().on_update()

    def _get_kw_dict(self, ret_locals: dict):
        del ret_locals["self"]
        del ret_locals["use_interface"]
        return ret_locals

    @payable
    @external
    def call_setStake(self, value: int) -> None:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            test_interface.setStake(value)
        else:
            self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                      func_name="setStake",
                      kw_dict=self._get_kw_dict(locals()))

    @external
    def call_getStake(self, address: Address) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.getStake(address)
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="getStake",
                             kw_dict=self._get_kw_dict(locals()))

    @external
    def call_estimateUnstakeLockPeriod(self) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.estimateUnstakeLockPeriod()
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="estimateUnstakeLockPeriod",
                             kw_dict=self._get_kw_dict(locals()))
    @external
    def call_setDelegation(self, delegations: list):
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            test_interface.setDelegation(delegations)
        else:
            self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                      func_name="setDelegation",
                      kw_dict=self._get_kw_dict(locals()))

    @external
    def call_getDelegation(self, address: Address) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.getDelegation(address)
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="getDelegation",
                             kw_dict=self._get_kw_dict(locals()))

    @payable
    @external
    def call_claimIScore(self):
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            test_interface.claimIScore()
        else:
            self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                      func_name="claimIScore",
                      kw_dict=self._get_kw_dict(locals()))

    @external
    def call_queryIScore(self, address: Address) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.queryIScore(address)
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="queryIScore",
                             kw_dict=self._get_kw_dict(locals()))

    @external
    def call_getIISSInfo(self) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.getIISSInfo()
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="getIISSInfo",
                             kw_dict=self._get_kw_dict(locals()))

    @external
    def call_getPRep(self, address: Address) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.getPRep(address)
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="getPRep",
                             kw_dict=self._get_kw_dict(locals()))

    @external
    def call_getPReps(self, startRanking: int, endRanking: int) -> list:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.getPReps(startRanking, endRanking)
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="getPReps",
                             kw_dict=self._get_kw_dict(locals()))

    @external
    def call_getMainPReps(self) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.getMainPReps()
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="getMainPReps",
                             kw_dict=self._get_kw_dict(locals()))

    @external
    def call_getSubPReps(self) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.getSubPReps()
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="getSubPReps",
                             kw_dict=self._get_kw_dict(locals()))

    @external
    def call_getPRepTerm(self) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.getPRepTerm()
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="getPRepTerm",
                             kw_dict=self._get_kw_dict(locals()))

    @external
    def call_getInactivePReps(self) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.getInactivePReps()
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="getInactivePReps",
                             kw_dict=self._get_kw_dict(locals()))

    @external
    def call_getScoreDepositInfo(self, address: Address) -> dict:
        use_interface = self.use_interface.get()
        if use_interface:
            test_interface = self.create_interface_score(SYSTEM_SCORE_ADDRESS, InterfaceSystemScore)
            return test_interface.getScoreDepositInfo(address)
        else:
            return self.call(addr_to=SYSTEM_SCORE_ADDRESS,
                             func_name="getScoreDepositInfo",
                             kw_dict=self._get_kw_dict(locals()))

