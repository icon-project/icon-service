# -*- coding: utf-8 -*-

from ..base.address import Address


LOCKED_ADDRESSES = (
    "hx76dcc464a27d74ca7798dd789d2e1da8193219b4",
    "hxac5c6e6f7a6e8ae1baba5f0cb512f7596b95f1fe",
    "hx966f5f9e2ab5b80a0f2125378e85d17a661352f4",
    "hxad2bc6446ee3ae23228889d21f1871ed182ca2ca",
    "hxc39a4c8438abbcb6b49de4691f07ee9b24968a1b",
    "hx96505aac67c4f9033e4bac47397d760f121bcc44",
    "hxf5bbebeb7a7d37d2aee5d93a8459e182cbeb725d",
    "hx4602589eb91cf99b27296e5bd712387a23dd8ce5",
    "hxa67e30ec59e73b9e15c7f2c4ddc42a13b44b2097",
    "hx52c32d0b82f46596f697d8ba2afb39105f3a6360",
    "hx985cf67b563fb908543385da806f297482f517b4",
    "hxc0567bbcba511b84012103a2360825fddcd058ab",
    "hx52c32d0b82f46596f697d8ba2afb39105f3a6360",
    "hx20be21b8afbbc0ba46f0671508cfe797c7bb91be",
    "hx19e551eae80f9b9dcfed1554192c91c96a9c71d1",

    "hx0607341382dee5e039a87562dcb966e71881f336",
    "hxdea6fe8d6811ec28db095b97762fdd78b48c291f",

    "hxaf3a561e3888a2b497941e464f82fd4456db3ebf",
    "hx061b01c59bd9fc1282e7494ff03d75d0e7187f47",
    "hx10d12d5726f50e4cf92c5fad090637b403516a41",
    "hx10e8a7289c3989eac07828a840905344d8ed559b",
)


_locked_addresses = set(Address.from_string(address) for address in LOCKED_ADDRESSES)


def is_address_locked(address: 'Address') -> bool:
    return address in _locked_addresses
