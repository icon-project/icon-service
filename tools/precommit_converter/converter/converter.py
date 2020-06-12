from typing import List, Tuple, Optional

from iconservice import ArrayDB
from iconservice.base.address import ICON_ADDRESS_BODY_SIZE, ICON_ADDRESS_BYTES_SIZE, Address, \
    ICON_CONTRACT_ADDRESS_BYTES_SIZE
from iconservice.base.block import Block
from iconservice.deploy import DeployStorage
from iconservice.deploy.storage import IconScoreDeployInfo, IconScoreDeployTXParams
from iconservice.icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER
from iconservice.iconscore.icon_container_db import ARRAY_DB_ID, DICT_DB_ID, VAR_DB_ID
from iconservice.icx import IcxStorage
from iconservice.icx.coin_part import CoinPart
from iconservice.icx.delegation_part import DelegationPart
from iconservice.icx.issue import IssueStorage
from iconservice.icx.issue.storage import RegulatorVariable
from iconservice.icx.stake_part import StakePart
from iconservice.iiss.storage import Storage as IISSStorage, IISSMetaData, RewardRate
from iconservice.meta import MetaDBStorage
from iconservice.prep import PRepStorage
from iconservice.prep.data import PRep
from iconservice.prep.prep_address_converter import PRepAddressConverter
from iconservice.utils import bytes_to_int
from iconservice.utils.msgpack_for_db import MsgPackForDB


class NotMatchException(Exception):
    pass


class Converter:
    def __init__(self):
        self._static_key_convert_methods: dict = {}
        self._flexible_key_convert_methods: List[callable, callable] = []

    def _convert_flexible_key(self, key: bytes, value: bytes):
        for key_detector, convert_method in self._flexible_key_convert_methods:
            if key_detector(key) is True:
                converted_key, converted_value = convert_method(key, value)
                return converted_key, converted_value

        raise NotMatchException()

    def convert(self, key: bytes, value: Optional[bytes]) -> Tuple[str, str]:
        """
        Convert key, value from bytes to string
        If no match, raise NotMatchException
        :param key:
        :param value: value could be None (e.g. delete score data)
        :return:
        """
        try:
            method = self._static_key_convert_methods[key]
            key, value = method(key, value)
        except KeyError:
            key, value = self._convert_flexible_key(key, value)
        return key, value


class DeployConverter(Converter):
    def __init__(self):
        super().__init__()
        self._flexible_key_convert_methods.extend([
            (self._is_deploy_tx_params, self._convert_deploy_tx_params),
            (self._is_deploy_info, self._convert_deploy_info)
        ])

    @classmethod
    def _is_deploy_tx_params(cls, key: bytes):
        if key.startswith(DeployStorage._DEPLOY_STORAGE_DEPLOY_TX_PARAMS_PREFIX) and len(key) == \
                len(DeployStorage._DEPLOY_STORAGE_DEPLOY_TX_PARAMS_PREFIX) + DEFAULT_BYTE_SIZE:
            return True
        return False

    @classmethod
    def _convert_deploy_tx_params(cls, key: bytes, value: bytes):
        bytes_tx_hash: bytes = key[len(DeployStorage._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX):]
        converted_key: str = f"Deploy TX Params TX hash: {bytes_tx_hash.hex()}"
        converted_value: 'IconScoreDeployTXParams' = IconScoreDeployTXParams.from_bytes(value)
        return converted_key, f"{converted_value.__dict__}"

    @classmethod
    def _is_deploy_info(cls, key: bytes):
        if key.startswith(DeployStorage._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX) and len(key) == \
                len(DeployStorage._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX) + ICON_CONTRACT_ADDRESS_BYTES_SIZE:
            return True
        return False

    @classmethod
    def _convert_deploy_info(cls, key: bytes, value: bytes) -> Tuple[str, str]:
        bytes_address: bytes = key[len(DeployStorage._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX):]
        converted_key: str = f"Deploy SCORE: {Address.from_bytes(bytes_address)}"
        converted_value: str = str(IconScoreDeployInfo.from_bytes(value))
        return converted_key, converted_value


class ScoreConverter(Converter):
    """
    Score Converter guarantees a probabilistic conversion.
    It means that it is impossible to decode the bytes data perfectly, as the data type is not recorded
    """
    DECODER_STRING_MAPPER = {
        ARRAY_DB_ID: "List ",
        DICT_DB_ID: "Dict ",
        VAR_DB_ID: "Var  "
    }
    ADDR_B_SIZE = ICON_CONTRACT_ADDRESS_BYTES_SIZE

    def __init__(self):
        super().__init__()
        self._flexible_key_convert_methods.append((self._is_score_data, self._convert_score_data))
        self.mapper = {
            ARRAY_DB_ID: self._array_db_decoder,
            DICT_DB_ID: self._dict_db_decoder,
            VAR_DB_ID: self._var_db_decoder
        }

    @classmethod
    def _decode_name(cls, name: bytes):
        #
        try:
            decoded_name = Address.from_bytes(name)
            if decoded_name is None:
                raise KeyError
        except:
            try:
                decoded_name = name.decode()
            except UnicodeDecodeError:
                decoded_name = name

        return decoded_name

    @classmethod
    def _is_score_data(cls, key):
        # It does not ensure this key is score data
        # Score address | type | name ...

        if len(key) > 24 and key[cls.ADDR_B_SIZE:cls.ADDR_B_SIZE + 1] == b'|' and \
                key[cls.ADDR_B_SIZE + 1:cls.ADDR_B_SIZE + 2] in cls.DECODER_STRING_MAPPER.keys() and \
                key[cls.ADDR_B_SIZE + 2:cls.ADDR_B_SIZE + 3] == b'|':
            return True
        return False

    def _convert_score_data(self, key: bytes, value: Optional[bytes]):
        # Score address | type | name ...
        score_addr = Address.from_bytes(key[:21])
        type_ = key[22:23]
        converted_key = self.mapper[type_](key[24:])
        converted_key: str = f"SCORE: {score_addr} || Type: {self.DECODER_STRING_MAPPER[type_]} || Key: {converted_key}"
        return converted_key, str(value)

    @classmethod
    def _dict_db_decoder(cls, key: bytes):
        ret: list = key.split(b'|')
        name = cls._decode_name(ret.pop(0))
        string_dict: str = f"{name}"
        for key in ret:
            if key == DICT_DB_ID:
                continue
            try:
                decoded_key = Address.from_bytes(key)
                if decoded_key is None:
                    decoded_key = key
            except:
                decoded_key = key
            string_dict += f"[{decoded_key}]"
        return string_dict

    @classmethod
    def _array_db_decoder(cls, key: bytes):
        ret: list = key.split(b'|')
        name = cls._decode_name(ret.pop(0))
        string_array: str = f"{name}"
        for d in ret:
            if d == ArrayDB._ArrayDB__SIZE_BYTE_KEY:
                string_array += f" byte {d.decode()}"
            else:
                string_array += f"[{bytes_to_int(d)}]"
        return string_array

    @classmethod
    def _var_db_decoder(cls, key: bytes):
        name = cls._decode_name(key)
        string_var: str = f"{name}"
        return string_var


class AccountMethod(Converter):

    def __init__(self):
        super().__init__()
        self._static_key_convert_methods.update({
            IcxStorage.LAST_BLOCK_KEY: self._convert_last_block,
            IcxStorage._TOTAL_SUPPLY_KEY: self._convert_total_supply
        })
        self._flexible_key_convert_methods.extend([(self._is_stake_parts, self._convert_stake_parts),
                                                   (self._is_delegation_parts, self._convert_delegation_parts),
                                                   (self._is_coin_parts, self._convert_coin_parts)])

    @classmethod
    def _convert_last_block(cls, key: bytes, value: bytes):
        last_block: 'Block' = Block.from_bytes(value)
        return key.decode(), str(last_block)

    @classmethod
    def _convert_total_supply(cls, key: bytes, value: bytes):
        converted_total_supply: int = int.from_bytes(value, DATA_BYTE_ORDER)
        return key.decode(), str(converted_total_supply)

    @classmethod
    def _is_coin_parts(cls, key: bytes):
        if len(key) == ICON_ADDRESS_BYTES_SIZE or len(key) == ICON_ADDRESS_BODY_SIZE:
            return True

    @classmethod
    def _convert_coin_parts(cls, key: bytes, value: bytes):

        return str(Address.from_bytes(key)), str(CoinPart.from_bytes(value))

    @classmethod
    def _is_stake_parts(cls, key: bytes):
        if key.startswith(StakePart.PREFIX) and len(key) == len(StakePart.PREFIX) + ICON_ADDRESS_BYTES_SIZE:
            return True
        return False

    @classmethod
    def _convert_stake_parts(cls, key: bytes, value: bytes):
        ret = StakePart.from_bytes(value)
        return str(Address.from_bytes(key[len(StakePart.PREFIX):])), str(ret)

    @classmethod
    def _is_delegation_parts(cls, key: bytes):
        if key.startswith(DelegationPart.PREFIX) and len(key) == len(DelegationPart.PREFIX) + ICON_ADDRESS_BYTES_SIZE:
            return True
        return False

    @classmethod
    def _convert_delegation_parts(cls, key: bytes, value: bytes):
        ret = DelegationPart.from_bytes(value)
        return str(Address.from_bytes(key[len(StakePart.PREFIX):])), str(ret)


class MetaConverter(Converter):
    def __init__(self):
        super().__init__()
        self._static_key_convert_methods.update({
            MetaDBStorage._KEY_LAST_CALC_INFO: self._convert_last_calc_info,
            MetaDBStorage._KEY_LAST_MAIN_PREPS: self._convert_last_main_preps,
            MetaDBStorage._KEY_LAST_TERM_INFO: self._convert_last_term_info,
            MetaDBStorage._KEY_PREV_NODE_ADDRESS_MAPPER: self._convert_prep_address_converter
        })

    """ Static """

    @classmethod
    def _convert_prep_address_converter(cls, key: bytes, value: bytes):
        converted_value: 'PRepAddressConverter' = PRepAddressConverter.from_bytes(value)
        return key.decode(), str(converted_value)

    @classmethod
    def _convert_last_calc_info(cls, key: bytes, value: bytes):
        data: list = MsgPackForDB.loads(value)
        _version = data[0]
        return key.decode(), str(data)

    @classmethod
    def _convert_last_main_preps(cls, key: bytes, value: bytes):
        data: list = MsgPackForDB.loads(value)
        _version = data[0]
        return key.decode(), str(data)

    @classmethod
    def _convert_last_term_info(cls, key: bytes, value: bytes):
        converted_value: list = MsgPackForDB.loads(value)
        return key.decode(), str(converted_value)


class PrepConverter(Converter):
    def __init__(self):
        super().__init__()
        self._static_key_convert_methods.update({
            PRepStorage.PREP_REGISTRATION_FEE_KEY: self._convert_prep_registration_fee,
            PRepStorage.TERM_KEY: self._convert_term
        })
        self._flexible_key_convert_methods.extend([
            (self._is_prep_data, self._convert_prep)
        ])

    """ Static """

    @classmethod
    def _convert_term(cls, key, value):
        data = MsgPackForDB.loads(value)
        return f"Term (bytes: {key})", str(data)

    @classmethod
    def _convert_prep_registration_fee(cls, key, value):
        data = MsgPackForDB.loads(value)
        return f"Prep registration fee (bytes: {key})", str(data)

    """ Flexible """

    @classmethod
    def _is_prep_data(cls, key: bytes):
        if key.startswith(PRep.PREFIX) and len(key) == len(PRep.PREFIX) + ICON_ADDRESS_BYTES_SIZE:
            return True
        return False

    @classmethod
    def _convert_prep(cls, key: bytes, value: bytes):
        prep_address = Address.from_bytes(key[len(PRep.PREFIX):])
        return f"Prep: {prep_address}", str(PRep.from_bytes(value))


class IISSConverter(Converter):
    def __init__(self):
        super().__init__()
        self._static_key_convert_methods.update({
            IISSStorage.IISS_META_DATA_KEY: self._convert_meta_data,
            IISSStorage.REWARD_RATE_KEY: self._convert_reward_rate,
            IISSStorage.TOTAL_STAKE_KEY: self._convert_total_stake,
            IISSStorage.CALC_END_BLOCK_HEIGHT_KEY: self._convert_calc_end_block_height,
            IISSStorage.CALC_PERIOD_KEY: self._convert_calc_period
        })

    @classmethod
    def _convert_total_stake(cls, key: bytes, value: bytes):
        converted_key: str = f"Total Stake (key: {key})"
        converted_value: str = str(MsgPackForDB.loads(value))
        return converted_key, converted_value

    @classmethod
    def _convert_calc_end_block_height(cls, key: bytes, value: bytes):
        converted_key: str = f"Calc End BH (key: {key})"
        converted_value: str = str(MsgPackForDB.loads(value))
        return converted_key, converted_value

    @classmethod
    def _convert_calc_period(cls, key: bytes, value: bytes):
        converted_key: str = f"Calc Period (key: {key})"
        converted_value: str = str(MsgPackForDB.loads(value))
        return converted_key, converted_value

    @classmethod
    def _convert_meta_data(cls, key: bytes, value: bytes):
        converted_key: str = f"Meta data (key: {key})"
        return converted_key, str(IISSMetaData.from_bytes(value))

    @classmethod
    def _convert_reward_rate(cls, key: bytes, value: bytes):
        converted_key: str = f"Reward rate (key: {key})"
        return converted_key, str(RewardRate.from_bytes(value))


class IssueConverter(Converter):
    def __init__(self):
        super().__init__()
        self._static_key_convert_methods.update({
            IssueStorage._REGULATOR_VARIABLE_KEY: self._convert_regulator_variable
        })

    @classmethod
    def _convert_regulator_variable(cls, key: bytes, value: bytes):
        converted_key: str = key.decode()
        converted_value: str = str(RegulatorVariable.from_bytes(value))
        return converted_key, converted_value
