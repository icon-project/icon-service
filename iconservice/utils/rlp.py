def rlp_encode_bytes(b: bytes) -> bytes:
    blen = len(b)
    if blen == 1 and b[0] < 0x80:
        return b
    elif blen <= 55:
        return bytes([blen + 0x80]) + b
    len_bytes = rlp_get_bytes(blen)
    return bytes([len(len_bytes) + 0x80 + 55]) + len_bytes + b


def rlp_get_bytes(x: int) -> bytes:
    if x == 0:
        return b''
    else:
        return rlp_get_bytes(int(x / 256)) + bytes([x % 256])
