#!/bin/bash

if [[ -z $1 ]]; then
    echo "Usage: $0 <command>"
    exit 1
fi
action=$1

CURL_CMD='curl -H "Content-Type: application/json" -d '
SERVER_URL='http://localhost:9000/api/v3'

case "$action" in
  sendtx|sendTransaction )
      #PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 10889, "params": {"from": "hxebf3a409845cd09dcb5af31ed5be5e34e2af9433", "to": "hx670e692ffd3d5587c36c3a9d8442f6d2a8fcc795", "value": "0xde0b6b3a7640000", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "tx_hash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802", "signature": "T4gQzqD5m8ZMeAi3XS+5/9YtnTb46i8FgmJVuJrQvEFjT6NDCKiP0Hw5Ii2OajsQfau8A4odHE3BvEvo7uayygE="}}'
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 10889, "params": {"from": "hx0000000000000000000000000000000000000000", "to": "hx1000000000000000000000000000000000000000", "value": "0xde0b6b3a7640000", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "tx_hash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802"}}'
  ;;
  gettxres|getTransactionResult )
      PARAMS='{"jsonrpc": "2.0", "method": "icx_getTransactionResult", "id": 20889, "params": {"tx_hash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802"}}'
  ;;
  getbal|getBalance )
      PARAMS='{"jsonrpc": "2.0", "method": "icx_getBalance", "id": 30889, "params": {"address": "hx1000000000000000000000000000000000000000"}}'
  ;;
  getsup|getTotalSupply )
      PARAMS='{"jsonrpc": "2.0", "method": "icx_getTotalSupply", "id": 40889, "params": {}}'
  ;;
  tokenbal|tokenBalance )
      PARAMS='{"jsonrpc": "2.0", "method": "icx_call", "id": 50889, "params": { "from": "hx0000000000000000000000000000000000000000", "to": "cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf", "data_type": "call", "data": {"method": "balance_of", "params": {"addr_from": "hx1111111111111111111111111111111111111111"}}}}'
  ;;
  tokensup|tokenTotalSupply )
      PARAMS='{"jsonrpc": "2.0", "method": "icx_call", "id": 60889, "params": { "from": "hx0000000000000000000000000000000000000000", "to": "cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf", "data_type": "call", "data": {"method": "total_supply", "params": {}}}}'
  ;;
  tokentra|tokenTransfer )
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 70889, "params": { "from": "hx0000000000000000000000000000000000000000", "to": "cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf", "value": "0x0", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "tx_hash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802", "data_type": "call", "data": {"method": "transfer", "params": {"addr_to": "hx1111111111111111111111111111111111111111", "value": "0x1"}}}}'
  ;;
  seq1 )
  # genesis -> hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa(addr1) transfer 10 icx(0x8ac7230489e80000)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 80889, "params": {"from": "hx0000000000000000000000000000000000000000", "to": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "value": "0x8ac7230489e80000", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "txHash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802"}}'
  ;;
  seq2 )
  # check icx balance address: addr value : 0x8ac7230489e80000 (10 icx)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_getBalance", "id": 90889, "params": {"address": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}'
  ;;
  seq3 )
  # check token balance address : hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa(addr1) value : 0x3635c9adc5dea00000 (1000*10**18)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_call", "id": 100889, "params": { "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "to": "cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf", "dataType": "call", "data": {"method": "balance_of", "params": {"addr_from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}}}'
  ;;
  seq4 )
  # transfer token to cx8c814aa96fefbbb85131f87f6e0cb7878a95c1d3(CrowdSale) value: 0x3635c9adc5dea00000(1000*10**18)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 110889, "params": { "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "to": "cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf", "value": "0x0", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "txHash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802", "dataType": "call", "data": {"method": "transfer", "params": {"addr_to": "cx8c814aa96fefbbb85131f87f6e0cb7878a95c1d3", "value": "0x3635c9adc5dea00000"}}}}'
  ;;
  seq5 )
  # check token balance address : cx8c814aa96fefbbb85131f87f6e0cb7878a95c1d3(CrowdSale) value : 0x3635c9adc5dea00000 (1000*10**18)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_call", "id": 120889, "params": { "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "to": "cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf", "dataType": "call", "data": {"method": "balance_of", "params": {"addr_from": "cx8c814aa96fefbbb85131f87f6e0cb7878a95c1d3"}}}}'
  ;;
  seq6 )
  # check token balance address : hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa(addr1) value : 0x0 (0)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_call", "id": 130889, "params": { "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "to": "cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf", "dataType": "call", "data": {"method": "balance_of", "params": {"addr_from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}}}'
  ;;
  seq7 )
  # transfer icx to CrowdSale value : 0x1bc16d674ec80000(2 icx)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 140889, "params": {"from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "to": "cx8c814aa96fefbbb85131f87f6e0cb7878a95c1d3", "value": "0x1bc16d674ec80000", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "txHash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802"}}'
  ;;
  seq8 )
  # check icx balance address: addr1 value : 0x6f05b59d3b200000 (8 icx)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_getBalance", "id": 150889, "params": {"address": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}'
  ;;
  seq9 )
  # check token balance address : hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa(addr1) value : 0x2 (2)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_call", "id": 160889, "params": { "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "to": "cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf", "dataType": "call", "data": {"method": "balance_of", "params": {"addr_from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}}}'
  ;;
  seq10 )
  # transfer icx to CrowdSale value : 0x6f05b59d3b200000(8 icx)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 170889, "params": {"from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "to": "cx8c814aa96fefbbb85131f87f6e0cb7878a95c1d3", "value": "0x6f05b59d3b200000", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "txHash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802"}}'
  ;;
  seq11 )
  # genesis -> addr2 transfer 90icx(0x4e1003b28d9280000)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 180889, "params": {"from": "hx0000000000000000000000000000000000000000", "to": "hxbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "value": "0x4e1003b28d9280000", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "txHash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802"}}'
  ;;
  seq12 )
  # transfer icx to CrowdSale value : 0x4e1003b28d9280000(90 icx)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 190889, "params": {"from": "hxbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "to": "cx8c814aa96fefbbb85131f87f6e0cb7878a95c1d3", "value": "0x4e1003b28d9280000", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "txHash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802"}}'
  ;;
  seq13 )
  # check CrowdSaleEnd
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 200889, "params": { "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "to": "cx8c814aa96fefbbb85131f87f6e0cb7878a95c1d3", "value": "0x0", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "txHash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802", "dataType": "call", "data": {"method": "check_goal_reached", "params": {}}}}'
  ;;
  seq14 )
  # check CrowdSaleEnd
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 210889, "params": { "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "to": "cx8c814aa96fefbbb85131f87f6e0cb7878a95c1d3", "value": "0x0", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "txHash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802", "dataType": "call", "data": {"method": "safe_withdrawal", "params": {}}}}'
  ;;
  seq15 )
  # check icx balance address: addr1 value : 0x56bc75e2d63100000 (100 icx)
      PARAMS='{"jsonrpc": "2.0", "method": "icx_getBalance", "id": 220889, "params": {"address": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}'
  ;;
  * )
    echo "Error: Invalid action... $action"
    echo "   Valid actions are [sendtx|gettxres|getbal|getsup|tokenbal|tokensup|tokentra]."
    exit 1
  ;;
esac

echo "request = $PARAMS"
eval $CURL_CMD \'$PARAMS\' $SERVER_URL
echo
