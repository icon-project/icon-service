import abc
from collections import UserDict
from typing import Optional, Any, List, Tuple

from iconservice.base.address import ICON_ADDRESS_BODY_SIZE, ICON_ADDRESS_BYTES_SIZE, Address, \
    ICON_CONTRACT_ADDRESS_BYTES_SIZE
from iconservice.deploy.storage import IconScoreDeployInfo, IconScoreDeployTXParams
from iconservice.icon_constant import DEFAULT_BYTE_SIZE
from iconservice.iconscore.icon_container_db import ARRAY_DB_ID, DICT_DB_ID, VAR_DB_ID
from iconservice.icx.coin_part import CoinPart
from iconservice.icx.delegation_part import DelegationPart
from iconservice.icx.stake_part import StakePart
from iconservice.prep import PRepStorage
from iconservice.icx import IcxStorage
from iconservice.icx.issue import IssueStorage
from iconservice.iiss.reward_calc import RewardCalcStorage
from iconservice.deploy import DeployStorage
from iconservice.iiss.storage import Storage as IISSStorage, IISSMetaData, RewardRate
from iconservice.prep.data import PRep
from iconservice.utils.msgpack_for_db import MsgPackForDB
from iconservice.meta import MetaDBStorage


class NotMatchException(Exception):
    pass


class Method(metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def get_static_key_convert_methods(cls) -> List[Tuple[bytes, callable]]:
        pass

    @classmethod
    @abc.abstractmethod
    def get_flexible_key_convert_methods(cls) -> List[Tuple[callable, callable]]:
        pass


class DeployMethod(Method):
    @classmethod
    def get_static_key_convert_methods(cls) -> list:
        return [

        ]

    @classmethod
    def get_flexible_key_convert_methods(cls) -> list:
        return [
            (cls._is_deploy_info, cls._get_deploy_info)
        ]

    @classmethod
    def _is_deploy_tx_params(cls, key: bytes):
        if key.startswith(DeployStorage._DEPLOY_STORAGE_DEPLOY_TX_PARAMS_PREFIX) and len(key) == \
                len(DeployStorage._DEPLOY_STORAGE_DEPLOY_TX_PARAMS_PREFIX) + DEFAULT_BYTE_SIZE:
            return True
        return False

    @classmethod
    def _get_deploy_tx_params(cls, key: bytes, value: bytes):
        bytes_tx_hash: bytes = key[len(DeployStorage._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX):]
        converted_key: str = f"Deploy TX Params TX hash: {bytes_tx_hash.hex()}"
        converted_value: 'IconScoreDeployTXParams' = IconScoreDeployTXParams.from_bytes(value)
        return converted_key, converted_value.__dict__

    @classmethod
    def _is_deploy_info(cls, key: bytes):
        if key.startswith(DeployStorage._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX) and len(key) == \
                len(DeployStorage._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX) + ICON_CONTRACT_ADDRESS_BYTES_SIZE:
            return True
        return False

    @classmethod
    def _get_deploy_info(cls, key: bytes, value: bytes):
        bytes_address: bytes = key[len(DeployStorage._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX):]
        converted_key: str = f"Deploy {Address.from_bytes(bytes_address)}"
        converted_value: 'IconScoreDeployInfo' = IconScoreDeployInfo.from_bytes(value)
        converted_value: str = f"Score Address: {converted_value.score_address} Owner: {converted_value.owner} " \
                               f"State: {converted_value.deploy_state} Cur TX Hash: {converted_value.current_tx_hash} " \
                               f"Next TX Hash: {converted_value.next_tx_hash}"
        return converted_key, converted_value


class ScoreMethod(Method):
    DECODER_STRING_MAPPER = {
        ARRAY_DB_ID: "List ",
        DICT_DB_ID: "Dict ",
        VAR_DB_ID: "Var  "
    }

    @classmethod
    def get_static_key_convert_methods(cls) -> list:
        return [

        ]

    @classmethod
    def get_flexible_key_convert_methods(cls) -> list:
        return [
            (cls._is_score_data, cls._get_score_data)
        ]

    @classmethod
    def _is_score_data(cls, key):
        # It does not ensure this key is score data
        # Score address | type | name ...
        if len(key) > 24 and key[21:22] == b'|' and \
                key[22:23] in cls.DECODER_STRING_MAPPER.keys() and \
                key[23:24] == b'|':
            return True
        return False

    @classmethod
    def _get_score_data(cls, key, value):
        mapper = {
            ARRAY_DB_ID: cls._array_db_decoder,
            DICT_DB_ID: cls._dict_db_decoder,
            VAR_DB_ID: cls._var_db_decoder
        }

        ret: list = key.split(b'|')
        # Score address | type | name ...
        score_addr = Address.from_bytes(ret.pop(0))
        type_ = ret.pop(0)
        converted_key = mapper[type_](ret)
        return f"SCORE: {score_addr} || Type: {cls.DECODER_STRING_MAPPER[type_]} || Key: {converted_key}", value

    @classmethod
    def _dict_db_decoder(cls, split_key: list):
        name = split_key.pop(0).decode()
        string_dict: str = f"{name}"
        for key in split_key:
            if key == DICT_DB_ID:
                continue
            decoded_key = Address.from_bytes(key)
            if decoded_key is None:
                decoded_key = key
            string_dict += f"[{decoded_key}]"
        return string_dict

    @classmethod
    def _array_db_decoder(cls, split_key: list):
        name = split_key.pop(0).decode()
        string_array: str = f"{name}"
        for key in split_key:
            string_array += f"[{int(key)}]"
        return string_array

    @classmethod
    def _var_db_decoder(cls, split_key: list):
        name = split_key.pop(0).decode()
        string_var: str = f"{name}"
        return string_var


class AccountMethod(Method):
    @classmethod
    def get_static_key_convert_methods(cls) -> list:
        return [

        ]

    @classmethod
    def get_flexible_key_convert_methods(cls) -> list:
        return [
            (cls._is_stake_parts, cls._get_stake_parts),
            (cls._is_delegation_parts, cls._get_delegation_parts),
            (cls._is_coin_parts, cls._get_coin_parts)
        ]

    @classmethod
    def _is_coin_parts(cls, key: bytes):
        if len(key) == ICON_ADDRESS_BYTES_SIZE or len(key) == ICON_ADDRESS_BODY_SIZE:
            return True

    @classmethod
    def _get_coin_parts(cls, key: bytes, value: bytes):

        return Address.from_bytes(key), CoinPart.from_bytes(value)

    @classmethod
    def _is_stake_parts(cls, key: bytes):
        if key.startswith(StakePart.PREFIX) and len(key) == len(StakePart.PREFIX) + ICON_ADDRESS_BYTES_SIZE:
            return True
        return False

    @classmethod
    def _get_stake_parts(cls, key: bytes, value: bytes):
        ret = StakePart.from_bytes(value)
        return Address.from_bytes(key[len(StakePart.PREFIX):]), ret

    @classmethod
    def _is_delegation_parts(cls, key: bytes):
        if key.startswith(DelegationPart.PREFIX) and len(key) == len(DelegationPart.PREFIX) + ICON_ADDRESS_BYTES_SIZE:
            return True
        return False

    @classmethod
    def _get_delegation_parts(cls, key: bytes, value: bytes):
        ret = DelegationPart.from_bytes(value)
        return key, ret


class MetaMethod(Method):
    @classmethod
    def get_static_key_convert_methods(cls) -> list:
        return [
            (MetaDBStorage._KEY_LAST_CALC_INFO, cls._get_last_calc_info),
            (MetaDBStorage._KEY_LAST_MAIN_PREPS, cls._get_last_main_preps)
        ]

    @classmethod
    def get_flexible_key_convert_methods(cls) -> list:
        return [

        ]

    """ Static """

    @classmethod
    def _get_last_calc_info(cls, key, value):
        data: list = MsgPackForDB.loads(value)
        _version = data[0]
        return key, data

    @classmethod
    def _get_last_main_preps(cls, key, value):
        data: list = MsgPackForDB.loads(value)
        _version = data[0]
        return key, data


class PrepMethod(Method):
    @classmethod
    def get_static_key_convert_methods(cls) -> list:
        return [
            (PRepStorage.PREP_REGISTRATION_FEE_KEY, cls._get_prep_registration_fee),
            (PRepStorage.TERM_KEY, cls._get_term)
        ]

    @classmethod
    def get_flexible_key_convert_methods(cls) -> list:
        return [
            (cls._is_prep_data, cls._get_prep)
        ]

    """ Static """

    @classmethod
    def _get_term(cls, key, value):
        data = MsgPackForDB.loads(value)
        return f"Term (bytes: {key})", data

    @classmethod
    def _get_prep_registration_fee(cls, key, value):
        data = MsgPackForDB.loads(value)
        version: int = data[0]
        assert version == 0
        prep_reg_fee: int = data[1]
        return f"PREP_REGISTRATION_FEE_KEY (bytes: {key})", prep_reg_fee

    """ Flexible """

    @classmethod
    def _is_prep_data(cls, key: bytes):
        if key.startswith(PRep.PREFIX) and len(key) == len(PRep.PREFIX) + ICON_ADDRESS_BYTES_SIZE:
            return True
        return False

    @classmethod
    def _get_prep(cls, key, value):
        prep_address = Address.from_bytes(key[len(PRep.PREFIX):])
        return f"Prep: {prep_address}", PRep.from_bytes(value)


class IISSMethod(Method):
    @classmethod
    def get_static_key_convert_methods(cls) -> list:
        return [
            (IISSStorage.IISS_META_DATA_KEY, cls.get_meta_data),
            (IISSStorage.REWARD_RATE_KEY, cls.get_reward_rate),
            # IISSStorage.TOTAL_STAKE_KEY,
            # IISSStorage.CALC_END_BLOCK_HEIGHT_KEY,
            # IISSStorage.CALC_PERIOD_KEY
        ]

    @classmethod
    def get_flexible_key_convert_methods(cls) -> list:
        return []

    @classmethod
    def get_meta_data(cls, key, value):
        return key, IISSMetaData.from_bytes(value)

    @classmethod
    def get_reward_rate(cls, key, value):
        return key, RewardRate.from_bytes(value)


class StaticKeyConverter:
    def __init__(self):
        self._mapper = {}

    def register(self, key: bytes, value_converter: callable):
        self._mapper[key] = value_converter

    def convert(self, key: bytes, value: bytes):
        try:
            return self._mapper[key](key, value)
        except KeyError:
            raise NotMatchException()


class FlexibleKeyConverter:
    def __init__(self):
        self._detector_converter_pairs = []

    def register(self, key_detector: callable, value_converter: callable):
        self._detector_converter_pairs.append((key_detector, value_converter))

    def convert(self, key: bytes, value: bytes) -> Any:
        for detector, converter in self._detector_converter_pairs:
            if detector(key) is True:
                return converter(key, value)
        else:
            raise NotMatchException()


class Converter:
    def __init__(self):
        self._static_key_converter = StaticKeyConverter()
        self._flexible_key_converter = FlexibleKeyConverter()
        for method_ in Method.__subclasses__():
            for key, converter in method_.get_static_key_convert_methods():
                self._static_key_converter.register(key, converter)

            for key_detector, converter in method_.get_flexible_key_convert_methods():
                self._flexible_key_converter.register(key_detector, converter)

    def convert(self, key: bytes, value: bytes):
        # Todo: check the minimum requirements
        try:
            converted_key, converted_value = self._static_key_converter.convert(key, value)
        except NotMatchException:
            try:
                converted_key, converted_value = self._flexible_key_converter.convert(key, value)
            except NotMatchException:
                # print("Converter not found")
                converted_key, converted_value = key, value
        return converted_key, converted_value
