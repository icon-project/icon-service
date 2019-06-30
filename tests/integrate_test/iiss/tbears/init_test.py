import os

from iconsdk.builder.transaction_builder import CallTransactionBuilder, DeployTransactionBuilder, TransactionBuilder
from iconsdk.icon_service import IconService
from iconsdk.libs.in_memory_zip import gen_deploy_data_content
from iconsdk.providers.http_provider import HTTPProvider
from iconsdk.signed_transaction import SignedTransaction

from tbears.libs.icon_integrate_test import IconIntegrateTestBase, SCORE_INSTALL_ADDRESS

DIR_PATH = os.path.abspath(os.path.dirname(__file__))

GOVERNANCE_SCORES = [
    '769282ab3dee78378d7443fe6c1344c76e718734e7f581961717f12a121a2be8',
    '83537e56c647fbf0b726286ee08d31f12dba1bf7e50e8119eaffbf48004f237f'
]


class TestInit(IconIntegrateTestBase):
    TEST_HTTP_ENDPOINT_URI_V3 = "http://127.0.0.1:9000/api/v3"
    SYSTEM_ADDRESS = "cx0000000000000000000000000000000000000000"
    GOVERNANCE_ADDRESS = "cx0000000000000000000000000000000000000001"

    def setUp(self):
        super().setUp(block_confirm_interval=1, network_only=True)

        # if you want to send request to network, uncomment next line and set self.TEST_HTTP_ENDPOINT_URI_V3
        self.icon_service = IconService(HTTPProvider(self.TEST_HTTP_ENDPOINT_URI_V3))

    def _deploy_score(self, score_path: str, to: str = SCORE_INSTALL_ADDRESS) -> dict:
        # Generates an instance of transaction for deploying SCORE.
        transaction = DeployTransactionBuilder() \
            .from_(self._test1.get_address()) \
            .to(to) \
            .step_limit(100_000_000_000) \
            .nid(3) \
            .nonce(100) \
            .content_type("application/zip") \
            .content(gen_deploy_data_content(score_path)) \
            .build()

        # Returns the signed transaction object having a signature
        signed_transaction = SignedTransaction(transaction, self._test1)

        # process the transaction
        tx_result = self.process_transaction(signed_transaction, self.icon_service)

        self.assertTrue('status' in tx_result)
        self.assertEqual(1, tx_result['status'])
        self.assertTrue('scoreAddress' in tx_result)

        return tx_result

    def _transfer_icx(self, from_: str, to: str, value: int):
        # Generates an instance of transaction for sending icx.
        transaction = TransactionBuilder() \
        .from_(from_) \
        .to(to) \
        .value(value) \
        .step_limit(1000000) \
        .nid(3) \
        .nonce(100) \
        .build()

        # Returns the signed transaction object having a signature
        signed_transaction = SignedTransaction(transaction, self._test1)

        # process the transaction
        tx_result = self.process_transaction(signed_transaction, self.icon_service)

        self.assertTrue('status' in tx_result)
        self.assertEqual(1, tx_result['status'])

        return tx_result

    def test_init(self):
        # deploy governance SCORE
        for score in GOVERNANCE_SCORES:
            score_path = os.path.abspath(os.path.join(DIR_PATH, f'./data/{score}.zip'))
            self._deploy_score(score_path=score_path, to=self.GOVERNANCE_ADDRESS)

        # set revision
        # Generates a 'setStake' instance of transaction for calling method in SCORE.
        transaction = CallTransactionBuilder() \
            .from_(self._test1.get_address()) \
            .to(self.GOVERNANCE_ADDRESS) \
            .step_limit(10_000_000) \
            .nid(3) \
            .nonce(100) \
            .method("setRevision") \
            .params({"code": 6, "name": "1.4.0"}) \
            .build()

        # Returns the signed transaction object having a signature
        signed_transaction = SignedTransaction(transaction, self._test1)

        # process the transaction
        tx_result = self.process_transaction(signed_transaction, self.icon_service)

        self.assertTrue('status' in tx_result)
        self.assertEqual(1, tx_result['status'])
