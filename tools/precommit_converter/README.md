# Precommit Data Converter

* Convert pre-commit data from hexadecimal string to human-readable

# Commands

* [convert](#convert)

## Convert

### Explain

* Convert pre-commit data from hexadecimal string to human-readable

```bash
(venv) :~/icon-service$ python3 -m tools.precommit_converter convert -h
usage: converter convert [-h] [-v] path

positional arguments:
  path           Precommit data file path

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Print key value with primitive
```

| key           |  type  | required | desc                                  |
| :------------ | :----: | :------: | ------------------------------------- |
| path          | string |   True   | The path of pre-commit data file<br/> |
| -v, --verbose |  bool  |  False   | Print key value with primitive <br/>  |

### Example

```
(venv) soobok@soobok-virtual-machine:~/icon-service$ python3 -m tools.precommit_converter convert -v 1-precommit-data-v0.json

Version = 1.6.1 
Revision = 5 
Block = Block(height=None, hash=None, prev_hash=0x0000000000000000000000000000000000000000000000000000000000000000, timestamp=1591318988717094, cumulative_fee=0) 
IS State Root Hash = 0x44ee9cd260abf6ff2be79ef10d8bfc8ae7a4da32e5fe4bb850873f7060dc2453 
RC State Root Hash = 0x44ee9cd260abf6ff2be79ef10d8bfc8ae7a4da32e5fe4bb850873f7060dc2453 
State Root Hash = 0x44ee9cd260abf6ff2be79ef10d8bfc8ae7a4da32e5fe4bb850873f7060dc2453 
Prev Block Generator = None 

* 'Hex:' means fail to convert. If new key, value is defined on iconservice, you should supplement converter
------------0------------
TX Index    ==> [0]
Key         ==> SCORE: cx0000000000000000000000000000000000000001 || Type: Var   || Key: revision_code
Value       ==> b'\x05'
Bytes Key   ==> b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01|\x02|revision_code'
Bytes Value ==> b'\x05'
------------1------------
TX Index    ==> [0]
Key         ==> Reward rate (key: b'iissrr')
Value       ==> reward_prep=1200
Bytes Key   ==> b'iissrr'
Bytes Value ==> b'\x92\x00\xcd\x04\xb0'
```

