#!/bin/bash

if [[ -z $1 ]]; then
    echo "Usage: $0 <command>"
    exit 1
fi
action=$1

CURL_CMD='curl -H "Content-Type: application/json" -d '
SERVER_URL='http://localhost:9000/api/v2'

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
      PARAMS='{"jsonrpc": "2.0", "method": "icx_call", "id": 50889, "params": { "from": "hx0000000000000000000000000000000000000000", "to": "cxb133709a91eb8bbc762808a87072287432523be5", "data_type": "call", "data": {"method": "balance_of", "params": {"addr_from": "cxb133709a91eb8bbc762808a87072287432523be5"}}}}'
  ;;
  tokensup|tokenTotalSupply )
      PARAMS='{"jsonrpc": "2.0", "method": "icx_call", "id": 60889, "params": { "from": "hx0000000000000000000000000000000000000000", "to": "cxb133709a91eb8bbc762808a87072287432523be5", "data_type": "call", "data": {"method": "total_supply", "params": {}}}}'
  ;;
  tokentra|tokenTransfer )
      PARAMS='{"jsonrpc": "2.0", "method": "icx_sendTransaction", "id": 70889, "params": { "from": "hx0000000000000000000000000000000000000000", "to": "cxb133709a91eb8bbc762808a87072287432523be5", "value": "0x0", "fee": "0x2386f26fc10000", "timestamp": "1523327456264040", "tx_hash": "1b06cfef02fd6c69e38f2d3079720f2c44be94455a7e664803a4fcbc3a695802", "data_type": "call", "data": {"method": "transfer", "params": {"addr_to": "hx0000000000000000000000000000000000000000", "value": "0x1"}}}}'
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
