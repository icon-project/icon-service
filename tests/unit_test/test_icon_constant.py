# -*- coding: utf-8 -*-

import pytest

from iconservice.icon_constant import DataType


class TestDataType:

    @pytest.mark.parametrize(
        "data_type,expected",
        [
            ("call", True),
            ("deploy", True),
            ("deposit", True),
            ("message", True),
            ("calls", False),
            ("deploys", False),
            ("deposits", False),
            ("messages", False),
            ("abc", False),
            ("", False),
            (None, True),
            ("None", False),
            (1, False),
            (b"\x00\x01", False),
            (1.1, False)
        ]
    )
    def test_contains(self, data_type, expected):
        assert DataType.contains(data_type) == expected
