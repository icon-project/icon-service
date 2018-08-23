# SCORE Audit

For every SCOREs requested to deploy to the ICON mainnet, we perform a security audit in an effort to verify they do not break the mainnet. Audit process may take several days. Before you plan to build your DApp, please take a time to look at these guidelines.

## Guidelines

Code should be deterministic as it will run on multiple nodes. You should avoid any business logic that depends on non-deterministic input such as clock time, random number, or external data source.

- Do not use clock time. Use block height instead. If you really want to use time information, use block timestamp or transaction timestamp.
- Do not use python random module. Consider using block hash or transaction hash to generate random number.
- Do not make an outgoing network call to fetch external data source whose outcome cannot be verified and also can change over time.

To pass an ICON audit, we recommend you do the following.

- DO NOT import any system packages. DO import only “iconservice” and the files of your own implementation placed in the same folder.
- DO NOT make any long-running operation inside the SCORE. Average block generation time would be 2 seconds in ICON, your transaction should not interrupt the block generation. No zero transaction blocks for now.

## Audit Process

- You request to “deploy” your SCORE to the ICON mainnet from the tbrears CLI.
- Your SCORE becomes in “pending” state, if the deploy transaction succeeded.
- You can query your SCORE’s state by sending an API call to a special address using SDKs (Java, Python) or on the ICONex.
  - Address : cx0000000000000000000000000000000000000001
  - API : getScoreStatus
  - Parameter : SCORE address. You can get this address by querying the result of deploy transaction using "tbears txresult" command.
- Once auditor approves your SCORE, it becomes in “active” state.
- If rejected, it becomes in “rejected” state. Response message of "getScoreStatus" will return the audit transaction hash, and if you query the audit transaction, you will know why it has been rejected. You need to deploy again after fixing the issues.

## Notes

This audit process would be temporary as current ICON network is in the beginning of its journey as a public network. We confirm that we do not have any intention of controlling DApps. Our first priority is maintaining ICON network as stable as possible, and minimizing any negative impacts, if any, on our partners business running on ICON.