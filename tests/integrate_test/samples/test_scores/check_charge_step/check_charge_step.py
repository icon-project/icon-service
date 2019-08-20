from iconservice import *


class CheckChargeStep(IconScoreBase):
    compressed_key_02_33 = b'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    compressed_key_03_33 = b'\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    uncompressed_key_04_65 = b'\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

# sha3_256
    def func2(self, bit: str) -> None:
        if bit[2] == '1':
            sha3_256(b'')

    def func3(self, bit: str) -> None:
        if bit[3] == '1':
            sha3_256(self.compressed_key_02_33)
    
    def func4(self, bit: str) -> None:
        if bit[4] == '1':
            sha3_256(self.uncompressed_key_04_65)

# create_address_with_key
    def func13(self, bit: str) -> None:
        if bit[13] == '1':
            create_address_with_key(b'')

    def func5(self, bit: str) -> None:
        if bit[5] == '1':
            create_address_with_key(self.compressed_key_02_33)

    def func6(self, bit: str) -> None:
        if bit[6] == '1':
            create_address_with_key(self.compressed_key_03_33)

    def func7(self, bit: str) -> None:
        if bit[7] == '1':
            create_address_with_key(self.uncompressed_key_04_65)
    
# json_dumps
    def func8(self, bit: str) -> None:
        if bit[8] == '1':
            json_dumps('')

    def func9(self, bit: str) -> None:
        if bit[9] == '1':
            json_dumps(None)

# json_loads
    def func10(self, bit: str) -> None:
        if bit[10] == '1':
            json_loads('')

# recover_key
    def func11(self, bit: str) -> None:
        if bit[11] == '1':
            recover_key(b'',b'',False)

    def func12(self, bit: str) -> None:
        if bit[12] == '1':
            recover_key(b'',b'',True)

    @external
    def test_str(self, bit:str) -> str:

        self.func2(bit)
        self.func3(bit)
        self.func4(bit)
        
        self.func13(bit)
        self.func5(bit)
        self.func6(bit)
        self.func7(bit)

        self.func8(bit)
        self.func9(bit)
        self.func10(bit)
        
        self.func11(bit)
        self.func12(bit)

        return bit
