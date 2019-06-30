import os

from iconsdk.builder.transaction_builder import CallTransactionBuilder
from iconsdk.builder.call_builder import CallBuilder
from iconsdk.icon_service import IconService
from iconsdk.providers.http_provider import HTTPProvider
from iconsdk.signed_transaction import SignedTransaction

from tbears.libs.icon_integrate_test import IconIntegrateTestBase

DIR_PATH = os.path.abspath(os.path.dirname(__file__))


class TestScoreTest(IconIntegrateTestBase):
    TEST_HTTP_ENDPOINT_URI_V3 = "http://127.0.0.1:9000/api/v3"
    SCORE_PROJECT = os.path.abspath(os.path.join(DIR_PATH, '..'))
    SYSTEM_ADDRESS = "cx0000000000000000000000000000000000000000"

    def setUp(self):
        super().setUp(block_confirm_interval=1, network_only=True)

        # if you want to send request to network, uncomment next line and set self.TEST_HTTP_ENDPOINT_URI_V3
        self.icon_service = IconService(HTTPProvider(self.TEST_HTTP_ENDPOINT_URI_V3))

    def test_stake(self):
        stake_value: int = 0x64
        account = self._wallet_array[0]

        # Generates a 'setStake' instance of transaction for calling method in SCORE.
        transaction = CallTransactionBuilder() \
            .from_(account.get_address()) \
            .to(self.SYSTEM_ADDRESS) \
            .step_limit(10_000_000) \
            .nid(3) \
            .nonce(100) \
            .method("setStake") \
            .params({"value": stake_value}) \
            .build()

        # Returns the signed transaction object having a signature
        signed_transaction = SignedTransaction(transaction, account)

        # process the transaction in local
        tx_result = self.process_transaction(signed_transaction, self.icon_service)

        self.assertTrue('status' in tx_result)
        self.assertEqual(1, tx_result['status'])

        # Generates a 'getStake' call instance using the CallBuilder
        call = CallBuilder().from_(account.get_address()) \
            .to(self.SYSTEM_ADDRESS) \
            .method("getStake") \
            .params({"address": account.get_address()}) \
            .build()

        # Sends the call request
        response = self.process_call(call, self.icon_service)

        expect_result = {
            "stake": hex(stake_value),
            "unstake": "0x0",
            "unstakedBlockHeight": "0x0"
        }

        self.assertEqual(expect_result, response)

    def test_message_tx(self):
        tx_result = self.process_message_tx(self.icon_service, "test message")

        self.assertTrue('status' in tx_result)
        self.assertEqual(1, tx_result['status'])
