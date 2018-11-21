# source code from
#   https://github.com/ethereum/eth-bloom
#
# run tests with following commands:
#   py.test tests/                  # run all tests under tests directory
#   py.test tests/test_bloom.py     # run all tests in tests/test_bloom.py
#   py.test tests/test_bloom.py::test_icon_bloom    # run test_icon_bloom test
#
# changes
#   test_casting_to_integer() : modify bloom filter result value
#   test_casting_to_binary() : modify bloom filter result value
#   test_icon_bloom() : add example for ICON

from __future__ import unicode_literals
import itertools

from hypothesis import (
    strategies as st,
    given,
    settings,
)

from iconservice.utils.bloom import (
    BloomFilter,
)


address = st.binary(min_size=20, max_size=20)
topic = st.binary(min_size=32, max_size=32)
topics = st.lists(topic, min_size=0, max_size=4)


log_entry = st.tuples(address, topics)
log_entries = st.lists(log_entry, min_size=0, max_size=30)


def check_bloom(bloom, log_entries):
    for address, topics in log_entries:
        assert address in bloom
        for topic in topics:
            assert topic in bloom


@given(log_entries)
@settings(max_examples=2000)
def test_bloom_filter_add_method(log_entries):
    bloom = BloomFilter()

    for address, topics in log_entries:
        bloom.add(address)
        for topic in topics:
            bloom.add(topic)

    check_bloom(bloom, log_entries)


@given(log_entries)
@settings(max_examples=2000)
def test_bloom_filter_extend_method(log_entries):
    bloom = BloomFilter()

    for address, topics in log_entries:
        bloom.extend([address])
        bloom.extend(topics)

    check_bloom(bloom, log_entries)


@given(log_entries)
@settings(max_examples=2000)
def test_bloom_filter_from_iterable_method(log_entries):
    bloomables = itertools.chain.from_iterable(
        itertools.chain([address], topics)
        for address, topics
        in log_entries
    )
    bloom = BloomFilter.from_iterable(bloomables)
    check_bloom(bloom, log_entries)


def test_casting_to_integer():
    bloom = BloomFilter()

    assert int(bloom) == 0

    bloom.add(b'value 1')
    bloom.add(b'value 2')

    assert int(bloom) == 800963689112930163398906062858920420155058144640141718492915966880983085334997948747242097956779081307875580665488979984230722615353716650488633297670536626677047622120622773348612865536585061953503673059142357958805410916593380605246972855179710304426298481701840818530123424537115396880974513788241473095180795899781565848464976696751898893539061424015338830573761126298009298281137312049835631880331605867224168108141830919723401071352531589012084131482373133878697278440283647605128052407795712


def test_casting_to_binary():
    bloom = BloomFilter()

    assert bin(bloom) == '0b0'

    bloom.add(b'value 1')
    bloom.add(b'value 2')

    assert bin(bloom) == (
        '0b1000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000001000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '010000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000010000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000100000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000010000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '000000000000000000000000000000000000000000000000000000000000000'
        '0000000000000000000'
    )


def test_combining_filters():
    b1 = BloomFilter()
    b2 = BloomFilter()

    b1.add(b'a')
    b1.add(b'b')
    b1.add(b'c')

    b2.add(b'd')
    b2.add(b'e')
    b2.add(b'f')

    b1.add(b'common')
    b2.add(b'common')

    assert b'a' in b1
    assert b'b' in b1
    assert b'c' in b1

    assert b'a' not in b2
    assert b'b' not in b2
    assert b'c' not in b2

    assert b'd' in b2
    assert b'e' in b2
    assert b'f' in b2

    assert b'd' not in b1
    assert b'e' not in b1
    assert b'f' not in b1

    assert b'common' in b1
    assert b'common' in b2

    b3 = b1 | b2

    assert b'a' in b3
    assert b'b' in b3
    assert b'c' in b3
    assert b'd' in b3
    assert b'e' in b3
    assert b'f' in b3
    assert b'common' in b3

    b4 = b1 + b2

    assert b'a' in b4
    assert b'b' in b4
    assert b'c' in b4
    assert b'd' in b4
    assert b'e' in b4
    assert b'f' in b4
    assert b'common' in b4

    b5 = BloomFilter(int(b1))
    b5 |= b2

    assert b'a' in b5
    assert b'b' in b5
    assert b'c' in b5
    assert b'd' in b5
    assert b'e' in b5
    assert b'f' in b5
    assert b'common' in b5

    b6 = BloomFilter(int(b1))
    b6 += b2

    assert b'a' in b6
    assert b'b' in b6
    assert b'c' in b6
    assert b'd' in b6
    assert b'e' in b6
    assert b'f' in b6
    assert b'common' in b6


def test_icon_bloom():
    b1 = BloomFilter()

    keys = ["func_name", "index1", "index2", "index3"]

    # make key from string
    i: int = 0
    for key in keys:
        # add to bloom filter as bytes type
        item = key + str(i)
        b1.add(item.encode())

    # backup bloom filter with int casting
    b1_int = int(b1)

    # load bloom filter from backup
    b2 = BloomFilter(b1_int)

    # check bloom filter has key value
    item = keys[0] + str(0)
    assert item.encode() in b2