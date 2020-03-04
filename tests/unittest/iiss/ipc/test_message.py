import unittest

from iconservice.iiss.reward_calc.ipc import message


class TestMessage(unittest.TestCase):
    def test_get_next_id(self):
        message.reset_next_msg_id(1)

        assert message._next_msg_id == 1

        msg_id: int = message._get_next_msg_id()
        assert msg_id == 1
        assert message._next_msg_id == 2

        msg_id: int = message._get_next_msg_id()
        assert msg_id == 2
        assert message._next_msg_id == 3

        message._next_msg_id = 0xffffffff
        msg_id: int = message._get_next_msg_id()
        assert msg_id == 0xffffffff
        assert message._next_msg_id == 1

        msg_id: int = message._get_next_msg_id()
        assert msg_id == 1
        assert message._next_msg_id == 2
