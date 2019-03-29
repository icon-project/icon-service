from unittest import TestCase

from iconservice.fee.fee import Fee
from tests import create_tx_hash


class TestFee(TestCase):

    def test_fee_from_bytes_to_bytes(self):
        fee = Fee()
        fee.ratio = 80
        fee.head_id = create_tx_hash()
        fee.tail_id = create_tx_hash()
        fee.available_head_id_of_deposit = create_tx_hash()
        fee.available_head_id_of_virtual_step = create_tx_hash()

        fee_in_bytes = fee.to_bytes()
        self.assertIsInstance(fee_in_bytes, bytes)

        fee2 = Fee.from_bytes(fee_in_bytes)
        self.assertIsInstance(fee2, Fee)
        self.assertEqual(fee, fee2)

    def test_to_bytes_from_bytes_with_none_type(self):
        fee = Fee()
        fee.ratio = 80

        fee_in_bytes = fee.to_bytes()
        self.assertIsInstance(fee_in_bytes, bytes)

        fee2 = Fee.from_bytes(fee_in_bytes)
        self.assertIsInstance(fee2, Fee)
        self.assertEqual(fee, fee2)

