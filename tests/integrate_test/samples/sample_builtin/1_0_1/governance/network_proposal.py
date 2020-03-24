from iconservice import *


class NetworkProposalType:
    TEXT = 0
    REVISION = 1
    MALICIOUS_SCORE = 2
    PREP_DISQUALIFICATION = 3
    STEP_PRICE = 4
    MIN = TEXT
    MAX = STEP_PRICE


class NetworkProposalStatus:
    VOTING = 0
    APPROVED = 1
    DISAPPROVED = 2
    CANCELED = 3
    MIN = VOTING
    MAX = CANCELED


class NetworkProposalVote:
    DISAGREE = 0
    AGREE = 1
    MIN = DISAGREE
    MAX = AGREE


class ApproveCondition:
    APPROVE_RATE = 0.66
    DISAPPROVE_RATE = 0.33


class MaliciousScoreType:
    FREEZE = 0
    UNFREEZE = 1
    MIN = FREEZE
    MAX = UNFREEZE


class NetworkProposal:
    """ Network Proposal which implements related method, controls DB and make result formatted """
    _PROPOSAL_LIST = 'proposal_list'
    _PROPOSAL_LIST_KEYS = 'proposal_list_keys'

    def __init__(self, db: IconScoreDatabase) -> None:
        self._proposal_list = DictDB(self._PROPOSAL_LIST, db, value_type=bytes)
        self._proposal_list_keys = ArrayDB(self._PROPOSAL_LIST_KEYS, db, value_type=bytes)
        self._validate_func: list = [
            self._validate_text_proposal,
            self._validate_revision_proposal,
            self._validate_malicious_score_proposal,
            self._validate_prep_disqualification_proposal,
            self._validate_step_price_proposal
        ]

    def register_proposal(self, id: bytes, proposer: 'Address', start: int, expired: int,
                          title: str, description: str, type: int, value: dict, main_preps: list) -> None:
        """ Put transaction hash and info of the proposal to db

        :param id: transaction hash to register the proposal
        :param proposer: address of EOA who want to register the proposal
        :param start: start block height of the proposal
        :param expired: expire block height of the proposal
        :param description: description of the proposal
        :param title: title of the proposal
        :param type: type of the proposal
        :param value: specific value of the proposal
        :param main_preps: main preps in list, List['PRepInfo']
        """
        if not self._validate_proposal(type, value):
            revert(f"Invalid parameter - type: {type}, value: {value}")

        self._proposal_list_keys.put(id)
        _STATUS = NetworkProposalStatus.VOTING

        main_prep_addresses = []
        main_prep_total_delegated = 0
        proposer_name = ''
        for main_prep in main_preps:
            main_prep_addresses.append(str(main_prep.address))
            main_prep_total_delegated += main_prep.delegated
            if main_prep.address == proposer:
                proposer_name = main_prep.name

        _VOTER = {
            "agree": {
                "list": [],
                "amount": 0
            },
            "disagree": {
                "list": [],
                "amount": 0
            },
            "noVote": {
                "list": main_prep_addresses,
                "amount": main_prep_total_delegated
            }
        }

        proposal_info = ProposalInfo(id, proposer, proposer_name, title, description, type, value, start, expired,
                                     _STATUS, _VOTER, len(main_prep_addresses), main_prep_total_delegated)
        self._proposal_list[id] = proposal_info.to_bytes()

    def cancel_proposal(self, id: bytes, proposer: 'Address', current_block_height: int) -> None:
        """ Set status out of the proposal's info to NetworkProposalStatus.CANCELED

        :param id: transaction hash to cancel the proposal
        :param proposer: address of EOA who want to cancel this proposal
        :param current_block_height: current block height
        """
        if not self._check_registered_proposal(id):
            revert("No registered proposal")

        proposal_info = ProposalInfo.from_bytes(self._proposal_list[id])

        if proposal_info.end_block_height < current_block_height:
            revert("This proposal has already expired")

        if proposer != proposal_info.proposer:
            revert("No permission - only for proposer")

        if proposal_info.status != NetworkProposalStatus.VOTING:
            revert("Can not be canceled - only voting proposal")

        proposal_info.status = NetworkProposalStatus.CANCELED
        self._proposal_list[id] = proposal_info.to_bytes()

    def vote_proposal(self, id: bytes, voter_address: 'Address', vote_type: int, current_block_height: int,
                      tx_hash: bytes, timestamp: int, main_preps: list) -> (bool, int, dict):
        """ Vote for the proposal - agree or disagree
        
        :param id: transaction hash to vote to the proposal
        :param voter_address: voter address
        :param vote_type: votes type - agree(NetworkProposalVote.AGREE, 1) or disagree(NetworkProposalVote.DISAGREE, 0)
        :param current_block_height: current block height
        :param tx_hash: generated transaction hash of this transaction to vote the proposal
        :param timestamp: timestamp of this transaction to vote the proposal
        :param main_preps: main preps list
        :return: bool - True means success for voting and False means failure for voting
        """
        if not self._validate_vote_type(vote_type):
            revert(f"Invalid vote parameter: {vote_type}")

        if not self._check_registered_proposal(id):
            revert("No registered proposal")

        proposal_info = ProposalInfo.from_bytes(self._proposal_list[id])

        if proposal_info.end_block_height < current_block_height:
            revert("This proposal has already expired")

        if proposal_info.status == NetworkProposalStatus.CANCELED:
            revert("This proposal has already canceled")

        _VOTE_TYPE_IN_STR = "agree" if vote_type == NetworkProposalVote.AGREE else "disagree"
        _NO_VOTE_IN_STR = "noVote"

        addresses_of_voters_agreeing_or_disagreeing = \
            [voter["address"] for voter in proposal_info.vote["agree"]["list"]] \
            + [voter["address"] for voter in proposal_info.vote["disagree"]["list"]]

        if str(voter_address) in addresses_of_voters_agreeing_or_disagreeing:
            revert("Already voted")

        if str(voter_address) not in proposal_info.vote["noVote"]["list"]:
            revert("No permission - only for main prep when network proposal registered")

        for main_prep in main_preps:
            if main_prep.address == voter_address:
                voter_in_dict = self._generate_voter_in_dict(tx_hash, timestamp, main_prep)

        proposal_info.vote[_VOTE_TYPE_IN_STR]["list"].append(voter_in_dict)
        proposal_info.vote[_VOTE_TYPE_IN_STR]["amount"] += voter_in_dict["amount"]

        proposal_info.vote[_NO_VOTE_IN_STR]["list"].remove(voter_in_dict["address"])
        proposal_info.vote[_NO_VOTE_IN_STR]["amount"] -= voter_in_dict["amount"]

        # set status
        approved = False
        if proposal_info.status == NetworkProposalStatus.VOTING:
            if self._check_vote_result(vote_type, proposal_info):
                if vote_type == NetworkProposalVote.AGREE:
                    proposal_info.status = NetworkProposalStatus.APPROVED
                    approved = True
                else:
                    proposal_info.status = NetworkProposalStatus.DISAPPROVED
            elif len(proposal_info.vote["noVote"]["list"]) == 0:
                # All voters voted but the status is still VOTING. Set status to DISAPPROVED
                proposal_info.status = NetworkProposalStatus.DISAPPROVED

        self._proposal_list[id] = proposal_info.to_bytes()

        return approved, proposal_info.type, proposal_info.value

    def get_proposal(self, id: bytes, current_block_height: int) -> dict:
        """ Get proposal information by ID

        :param id: transaction hash to register the proposal
        :param current_block_height: current block height
        :return: the proposal info in result format in dict
        """
        if not self._check_registered_proposal(id):
            revert("No registered proposal")

        proposal_info = ProposalInfo.from_bytes(self._proposal_list[id])

        if proposal_info.end_block_height < current_block_height:
            if proposal_info.status == NetworkProposalStatus.VOTING:
                proposal_info.status = NetworkProposalStatus.DISAPPROVED

        result = self._generate_proposal_info_in_dict_for_get_proposal(proposal_info)
        return result

    def get_proposals(self, current_block_height: int, type: int = None, status: int = None) -> dict:
        """ Get proposal list to be filtered by type and status

        :param current_block_height: current block height
        :param type: type of network proposal to filter (optional)
        :param status: status of network proposal to filter (optional)
        :return: the proposal info list in result format in dict
        """
        if type is not None and not self._validate_proposal_type(type):
            revert(f"Invalid type parameter: {type}")

        if status is not None and not self._validate_proposal_status(status):
            revert(f"Invalid status parameter: {status}")

        proposals = []
        for id in self._proposal_list_keys:
            proposal_info = ProposalInfo.from_bytes(self._proposal_list[id])

            if proposal_info.end_block_height < current_block_height:
                if proposal_info.status == NetworkProposalStatus.VOTING:
                    proposal_info.status = NetworkProposalStatus.DISAPPROVED

            if type is not None and proposal_info.type != type:
                continue

            if status is not None and proposal_info.status != status:
                continue

            proposal_info_in_dict = self._generate_proposal_info_in_dict_for_get_proposals(proposal_info)
            proposals.append(proposal_info_in_dict)

        result = {
            "proposals": proposals
        }
        return result

    @staticmethod
    def _validate_proposal_type(type_: int):
        return True if NetworkProposalType.MIN <= type_ <= NetworkProposalType.MAX else False

    @staticmethod
    def _validate_proposal_status(status: int):
        return True if NetworkProposalStatus.MIN <= status <= NetworkProposalStatus.MAX else False

    @staticmethod
    def _validate_vote_type(type_: int):
        return True if NetworkProposalVote.MIN <= type_ <= NetworkProposalVote.MAX else False

    def _validate_proposal(self, proposal_type: int, value: dict):
        result = False
        if not self._validate_proposal_type(proposal_type):
            return result
        try:
            validator = self._validate_func[proposal_type]
            result = validator(value)
        except Exception as e:
            Logger.error(f"Network proposal parameter validation error :{e}")
        finally:
            return result

    @staticmethod
    def _validate_text_proposal(value: dict) -> bool:
        text = value['value']
        return isinstance(text, str)

    @staticmethod
    def _validate_revision_proposal(value: dict) -> bool:
        code = int(value['code'], 16)
        name = value['name']

        return isinstance(code, int) and isinstance(name, str)

    @staticmethod
    def _validate_malicious_score_proposal(value: dict) -> bool:
        address = Address.from_string(value['address'])
        type_ = int(value['type'], 16)

        return isinstance(address, Address) \
               and address.is_contract \
               and MaliciousScoreType.MIN <= type_ <= MaliciousScoreType.MAX

    @staticmethod
    def _validate_prep_disqualification_proposal(value: dict) -> bool:
        address = Address.from_string(value['address'])

        main_preps, _ = get_main_prep_info()
        sub_preps, _ = get_sub_prep_info()

        for prep in main_preps + sub_preps:
            if prep.address == address:
                return True

        return False

    @staticmethod
    def _validate_step_price_proposal(value: dict) -> bool:
        value = int(value['value'], 16)
        return isinstance(value, int)

    def _check_registered_proposal(self, id: bytes) -> bool:
        """ Check if the proposal with ID have already registered

        :param id: transaction hash to register the proposal
        :return: bool
        """
        proposal_in_bytes = self._proposal_list[id]
        return True if proposal_in_bytes else False

    @staticmethod
    def _check_vote_result(vote_type: int, proposal_info: 'ProposalInfo') -> bool:
        """ Check that the results of the vote meet the approve or disapprove conditions

        :return: bool
        """
        total_delegated = 0
        for vote_type_in_str in ("agree", "disagree", "noVote"):
            total_delegated += proposal_info.vote[vote_type_in_str]["amount"]

        preps_to_vote = proposal_info.vote["agree" if vote_type == NetworkProposalVote.AGREE else "disagree"]
        voters_of_preps_to_vote: list = preps_to_vote["list"]
        delegated_of_preps_to_vote: int = preps_to_vote["amount"]
        try:
            if vote_type == NetworkProposalVote.AGREE:
                return len(voters_of_preps_to_vote) / proposal_info.total_voter >= ApproveCondition.APPROVE_RATE \
                       and delegated_of_preps_to_vote / proposal_info.total_delegated_amount \
                       >= ApproveCondition.APPROVE_RATE
            else:
                return len(voters_of_preps_to_vote) / proposal_info.total_voter >= ApproveCondition.DISAPPROVE_RATE \
                       and delegated_of_preps_to_vote / proposal_info.total_delegated_amount \
                       >= ApproveCondition.DISAPPROVE_RATE
        except ZeroDivisionError:
            return False

    @staticmethod
    def _generate_common_proposal_info_in_dict(proposal_info: 'ProposalInfo') -> dict:
        """ Generate common proposal info in dict for both `getProposal` and `getProposals`

        :param proposal_info: ProposalInfo instance
        :return: proposal info in dict where format is used to both `getProposal` and `getProposals` except for 'vote' item
        """
        proposal_info_in_dict = {
            "id": '0x' + bytes.hex(proposal_info.id),
            "proposer": str(proposal_info.proposer),
            "proposerName": proposal_info.proposer_name,
            "status": hex(proposal_info.status),
            "startBlockHeight": hex(proposal_info.start_block_height),
            "endBlockHeight": hex(proposal_info.end_block_height),
            "contents": {
                "title": proposal_info.title,
                "description": proposal_info.description,
                "type": hex(proposal_info.type),
                "value": proposal_info.value
            }
        }
        return proposal_info_in_dict

    def _generate_proposal_info_in_dict_for_get_proposals(self, proposal_info: 'ProposalInfo') -> dict:
        """ Generate proposal info in dict for `getProposals` method

        :param proposal_info: ProposalInfo instance
        :return: proposal info in dict where format is set to the `getProposals` method
        """
        vote_value = {}
        for vote_type in ("agree", "disagree", "noVote"):
            vote_value[vote_type] = {
                "count": hex(len(proposal_info.vote[vote_type]["list"])),
                "amount": hex(proposal_info.vote[vote_type]["amount"])
            }

        proposal_info_in_dict = self._generate_common_proposal_info_in_dict(proposal_info)
        proposal_info_in_dict["vote"] = vote_value
        return proposal_info_in_dict

    def _generate_proposal_info_in_dict_for_get_proposal(self, proposal_info: 'ProposalInfo') -> dict:
        """ Generate proposal info in dict for `getProposal` method

        :param proposal_info: ProposalInfo instance
        :return: proposal info in dict where format is set to the `getProposal` method
        """
        for vote_type in ("agree", "disagree", "noVote"):
            proposal_info.vote[vote_type]["amount"] = hex(proposal_info.vote[vote_type]["amount"])

            if vote_type in ("agree", "disagree") and len(proposal_info.vote[vote_type]) > 0:
                for voter_in_dict in proposal_info.vote[vote_type]["list"]:
                    voter_in_dict["timestamp"] = hex(voter_in_dict["timestamp"])
                    voter_in_dict["amount"] = hex(voter_in_dict["amount"])

        proposal_info_in_dict = self._generate_common_proposal_info_in_dict(proposal_info)
        proposal_info_in_dict["vote"] = proposal_info.vote
        return proposal_info_in_dict

    @staticmethod
    def _generate_voter_in_dict(id: bytes, timestamp: int, prep: 'Prep') -> dict:
        """ Generate one of items in dict of voter list

        :param id: transaction hash generated for the voter to vote for the proposal
        :param timestamp: timestamp
        :param prep: 'Prep' having attributes of prep information like address, name, delegated and etc.
        :return: voter information in dict; one of the items in dict for voter list.
                 A data type is either integer or string in order not to be converted but to JSON dumps directly
        """
        voter_in_dict = {
            "id": '0x' + bytes.hex(id),
            "timestamp": timestamp,
            "address": str(prep.address),
            "name": prep.name,
            "amount": prep.delegated
        }
        return voter_in_dict


class ProposalInfo:
    """ ProposalInfo Class including proposal information"""

    def __init__(self, id: bytes, proposer: 'Address', proposer_name: str, title: str, description: str, type: int,
                 value: dict, start_block_height: int, end_block_height: int, status: int, vote: dict,
                 total_voter: int = 0, total_delegated_amount: int = 0):
        self.id = id
        self.proposer = proposer
        self.proposer_name = proposer_name
        self.title = title
        self.description = description
        self.type = type
        self.value = value  # value dict has str value
        self.start_block_height = start_block_height
        self.end_block_height = end_block_height
        self.status = status
        self.vote = vote
        if total_voter == 0 and total_delegated_amount == 0:
            for vote_type_in_str in ("agree", "disagree", "noVote"):
                total_voter += len(vote[vote_type_in_str]["list"])
                total_delegated_amount += vote[vote_type_in_str]["amount"]
        self.total_voter = total_voter
        self.total_delegated_amount = total_delegated_amount

    def to_bytes(self) -> bytes:
        """ Convert ProposalInfo to bytes

        :return: ProposalInfo in bytes
        """
        proposal_info_in_dict = vars(self)
        proposal_info_in_dict["id"] = bytes.hex(proposal_info_in_dict["id"])
        proposal_info_in_dict["proposer"] = str(proposal_info_in_dict["proposer"])
        return json_dumps(proposal_info_in_dict).encode()

    @staticmethod
    def from_bytes(buf: bytes) -> 'ProposalInfo':
        """ Create ProposalInfo object from bytes

        :param buf: ProposalInfo in bytes
        :return: ProposalInfo object
        """
        proposal_info_in_dict: dict = json_loads(buf.decode())
        proposal_info_in_dict["id"] = bytes.fromhex(proposal_info_in_dict["id"])
        proposal_info_in_dict["proposer"] = Address.from_string(proposal_info_in_dict["proposer"])
        return ProposalInfo(**proposal_info_in_dict)
