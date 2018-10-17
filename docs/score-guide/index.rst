ICON Smart Contract - SCORE
===========================

SCORE (Smart Contract on Reliable Environment) is a smart contract
running on ICON network. A contract is a software that resides at a
specific address on the blockchain and executed on ICON nodes. They are
building blocks for DApp (Decentralized App). SCORE defines and exports
interfaces, so that other SCORE can invoke its functions. The code is
written in python, and is uploaded as compressed binary data on the
blockchain.

-  Deployed SCORE can be updated. SCORE address remains the same after
   update.
-  SCORE code size is limited to about 64 KB (actually bounded by the
   maximum stepLimit value during its deploy transaction) after
   compression.
-  SCORE must follow sandbox policy - file system access or network API
   calls are prohibited.

.. toctree::
    :caption: Contents

    deep-into-the-score
    syntax
    limitation
    api-references
