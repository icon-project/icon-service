import pytest

from iconservice.base.address import Address
from iconservice.utils.locked import is_address_locked


@pytest.mark.parametrize(
    "address,locked", [
        ("hx76dcc464a27d74ca7798dd789d2e1da8193219b4", True),
        ("hxac5c6e6f7a6e8ae1baba5f0cb512f7596b95f1fe", True),
        ("hx966f5f9e2ab5b80a0f2125378e85d17a661352f4", True),
        ("hxad2bc6446ee3ae23228889d21f1871ed182ca2ca", True),
        ("hxc39a4c8438abbcb6b49de4691f07ee9b24968a1b", True),
        ("hx96505aac67c4f9033e4bac47397d760f121bcc44", True),
        ("hxf5bbebeb7a7d37d2aee5d93a8459e182cbeb725d", True),
        ("hx3f472b9f22a165b02da1544004e177d168d19eaf", True),
        ("hx3333333333333333333333333333333333333333", False),
    ]
)
def test_is_address_locked(address, locked):
    addr = Address.from_string(address)
    assert is_address_locked(addr) == locked
