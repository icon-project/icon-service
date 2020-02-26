import hashlib
from functools import wraps

import pytest

from iconservice import AddressPrefix, Address
from iconservice.database.db import KeyValueDatabase, ContextDatabase
from iconservice.icon_constant import IconScoreContextType, IconNetworkValueType
from iconservice.icon_network.container import Container as INVContainer
from iconservice.icon_network.data.value import (
    RevisionCode,
    ScoreBlackList,
    StepPrice,
    StepCosts,
    MaxStepLimits,
    ServiceConfig,
    ImportWhiteList
)
from iconservice.iconscore.icon_score_context import IconScoreContext
from tests import create_tx_hash
from tests.mock_db import MockKeyValueDatabase


def patch_several(*decorate_args):
    def start_patches(*args):
        for patcher in args:
            patcher.start()

    def stop_patches(*args):
        for patcher in args:
            patcher.stop()

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_patches(*decorate_args)
            ret = func(*args, **kwargs)
            stop_patches(*decorate_args)
            return ret

        return wrapper

    return decorate


def _generate_inv_container(revision: int = 0):
    is_migrated: bool = False
    service_config: int = 0
    step_costs = {
        'default': 1_000_000,
        'contractCall': 15_000,
        'contractCreate': 200_000,
        'contractUpdate': 80_000,
        'contractDestruct': -70_000,
        'contractSet': 30_000,
        'get': 0,
        'set': 200,
        'replace': 50,
        'delete': -150,
        'input': 200,
        'eventLog': 100,
        'apiCall': 0
    }
    max_step_limits: dict = {
        IconScoreContextType.INVOKE: 2_500_000_000,
        IconScoreContextType.QUERY: 50_000_000
    }
    step_price: int = 0
    score_black_list: list = []
    import_white_list = {"iconservice": ['*']}
    system_value = INVContainer(is_migrated=False)
    system_value._cache = {
        IconNetworkValueType.REVISION_CODE: RevisionCode(revision),
        IconNetworkValueType.SCORE_BLACK_LIST: ScoreBlackList(score_black_list),
        IconNetworkValueType.STEP_PRICE: StepPrice(step_price),
        IconNetworkValueType.STEP_COSTS: StepCosts(step_costs),
        IconNetworkValueType.MAX_STEP_LIMITS: MaxStepLimits(max_step_limits),
        IconNetworkValueType.SERVICE_CONFIG: ServiceConfig(service_config),
        IconNetworkValueType.IMPORT_WHITE_LIST: ImportWhiteList(import_white_list)
    }
    return system_value


@pytest.fixture(scope="function")
def address() -> 'Address':
    prefix: int = 0
    data: bytes = create_tx_hash()
    hash_value = hashlib.sha3_256(data).digest()
    return Address(AddressPrefix(prefix), hash_value[-20:])


@pytest.fixture(scope="function")
def context_db():
    mocked_kv_db: 'KeyValueDatabase' = MockKeyValueDatabase.create_db()
    return ContextDatabase(mocked_kv_db)


#
# @pytest.fixture(scope="module")
# def icon_context_factory():
#     origin_addr: 'Address' = create_address(AddressPrefix.EOA)
#     inv_container = _generate_inv_container()
#     context_type: 'IconScoreContextType' = IconScoreContextType.INVOKE
#
#     context = IconScoreContext(context_type)
#     context.msg = Message(origin_addr, 0)
#     context._inv_container = inv_container
#
#     context.tx = Transaction(create_tx_hash(), origin=origin_addr)
#     context.block = Block(1, create_block_hash(), 0, None, 0)
#     context.icon_score_mapper = IconScoreMapper()
#     context.new_icon_score_mapper = {}
#     step_counter: 'IconScoreStepCounterFactory' = IconScoreStepCounterFactory.create_step_counter(inv_container,
#                                                                                                   context_type)
#     context.step_counter = step_counter
#     context.icx = IcxEngine()
#     context.icx.open(self._icx_storage)
#     context.event_logs = Mock(spec=list)
#     context.traces = Mock(spec=list)
#     return context
