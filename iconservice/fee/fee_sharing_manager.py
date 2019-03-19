from ..icx.icx_storage import IcxStorage
from ..icx.icx_engine import IcxEngine


class FeeSharingManager:
    """
    Fee Sharing Manager

    [Role]
    - State DB CRUD
    - Calculation
    """

    def __init__(self, icx_storage: 'IcxStorage', icx_engine: 'IcxEngine') -> None:
        pass

    def set_fee_sharing_info(self, score: 'Address', ratio: int, max_step_limit: int = 0):

        """Sets fee sharing ratio and max step limit of the SCORE"""
        pass

    def get_fee_sharing_info(self, score: 'Address') -> dict:
        """Gets fee sharing ratio and max step limit"""
        return {
            "ratio": 100,
            "max_step_limit": 100
        }

    # TODO : naming (_term or _period)
    def deposit_fee(self, score: 'Address', term: int) -> None:
        """
        Deposits ICX for charging fee by adding contract

        [Sub Task]
        - Deposits ICX
        - Calculates Virtual Step
        - Updates Deposit Data
        """
        pass

    def withdraw_fee(self, id: bytes) -> None:
        """
        Withdraws deposited ICX

        [Sub Task]
        - Checks if the contract period is finished
        - if the period is not finished, calculates and apply a penalty
        - Update ICX
        """
        pass

    def get_deposit_info_by_id(self, id: bytes) -> dict:
        """Gets deposit information in dict by contract ID"""
        return {
            "_id": "_id",
            "_score": "_score",
            "_from": "_from",
            "_amount": "_amount",
            "_createAt": "_createAt",
            "_expiresIn": "_expiresIn",
            "_virtualStepIssued": "_virtualStepIssued",
            "_virtualStepUsed": "_virtualStepUsed"
        }

    def get_score_info(self, score: 'Address') -> dict:
        """
        Gets SCORE information in dict

        :param score: SCORE address
        :return: score information in dict
                - CORE Address
                - Amount of issued total virtual step
                - Amount of Used total virtual step
                - contracts in list
        """
        return {
            "_score": "_score",
            "_totalVirtualStepIssued": "_totalVirtualStepIssued",
            "_totalVirtualStepUsed": "_totalVirtualStepUsed",
            "_deposits": [{}, {}, ...]
        }

    # TODO : get_score_info_by_EOA

    def get_available_step(self, score: 'Address', msg_sender_step_limit: int) -> int:
        """
        Checks if msg sender's step limit is available with both of msg sender and SCORE account
        - ICX or virtual step.
        """
        # Get the SCORE's ratio
        # Calculate ratio * SCORE and (1-ratio) * msg sender
        # Checks msg sender account
        # Checks SCORE owner account
        return 'MaxAvailableStep'

    def charge_fee(self, step_price, used_step):
        pass


