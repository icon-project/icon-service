from unittest.mock import Mock

import pytest

from iconservice import ZERO_SCORE_ADDRESS, Address
from iconservice.base.exception import InvalidParamsException
from iconservice.icon_constant import Revision
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_event_log import EventLogEmitter
from iconservice.icx.issue.engine import Engine as IssueEngine
from tests import create_address


@pytest.fixture(scope="function", params=[revision.value for revision in Revision])
def context(request):
    context = Mock(spec=IconScoreContext)
    context.revision = request.param
    return context


@pytest.fixture(scope="function")
def issue_engine(monkeypatch):
    issue_engine: 'IssueEngine' = IssueEngine()
    monkeypatch.setattr(IssueEngine, "_burn", Mock())
    yield issue_engine
    monkeypatch.undo()


@pytest.fixture(scope="function", autouse=True)
def event_log_emitter(monkeypatch):
    monkeypatch.setattr(EventLogEmitter, "emit_event_log", Mock())
    yield
    monkeypatch.undo()


class TestIssueEngine:

    def test_burn_event_log(self, context, issue_engine):
        address: 'Address' = create_address()
        amount: int = 10
        expected_score_address: 'Address' = ZERO_SCORE_ADDRESS

        if context.revision < Revision.FIX_BURN_EVENT_SIGNATURE.value:
            expected_signature = "ICXBurned"
        elif context.revision < Revision.BURN_V2_ENABLED.value:
            expected_signature: str = "ICXBurned(int)"
        else:
            expected_signature: str = "ICXBurnedV2(Address,int)"

        if context.revision < Revision.BURN_V2_ENABLED.value:
            expected_arguments: list = [amount]
            expected_indexed_args_count: int = 0
        else:
            expected_arguments: list = [address, amount]
            expected_indexed_args_count: int = 1

        issue_engine.burn(context, address, amount)

        issue_engine._burn.assert_called_with(context, address, amount)
        EventLogEmitter.emit_event_log.assert_called_with(context,
                                                          score_address=expected_score_address,
                                                          event_signature=expected_signature,
                                                          arguments=expected_arguments,
                                                          indexed_args_count=expected_indexed_args_count)

    def test_burn_0_amount(self, context, issue_engine):
        address: Address = create_address()

        if context.revision >= Revision.BURN_V2_ENABLED.value:
            with pytest.raises(InvalidParamsException):
                issue_engine.burn(context, address, amount=0)
        else:
            issue_engine.burn(context, address, amount=0)
