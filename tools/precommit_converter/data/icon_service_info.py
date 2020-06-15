from typing import Optional

from iconservice.base.block import Block


class IconServiceInfo:
    def __init__(self,
                 version: str,
                 revision: int,
                 block: 'Block',
                 is_state_root_hash: str,
                 rc_state_root_hash: str,
                 state_root_hash: str,
                 prev_block_generator: Optional[str]):
        self.version = version
        self.revision = revision
        self.block = block
        self.is_state_root_hash = is_state_root_hash
        self.rc_state_root_hash = rc_state_root_hash
        self.state_root_hash = state_root_hash
        self.prev_block_generator = prev_block_generator

    def __str__(self):
        return f"Version = {self.version} \n" \
               f"Revision = {self.revision} \n" \
               f"Block = {self.block} \n" \
               f"IS State Root Hash = {self.is_state_root_hash} \n" \
               f"RC State Root Hash = {self.rc_state_root_hash} \n" \
               f"State Root Hash = {self.state_root_hash} \n" \
               f"Prev Block Generator = {self.prev_block_generator} \n"
