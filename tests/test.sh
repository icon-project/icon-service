#!/bin/bash
export PYTHONPATH=$PYTHONPATH:..

LIST=`ls -1 test*.py`

if [ $# -eq 1 ]; then
    LIST="test_icx_$1.py"
fi

python3 -m unittest -v $LIST

