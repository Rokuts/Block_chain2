from dataclasses import dataclass
from typing import Optional
import time

from my_hash_function import hash_generator

@dataclass
class BlockHeader:
    prev_hash: str
    timestamp: int
    version: int
    merkle_root: str
    nonce: int = 0
    difficulty: int = 3  # kiek nulių heksadešimtainėje hasho pradžioje reikalaujama
    is_genesis: bool = False  # jei True — hash grąžinamas kaip "00000000"

    def serialize(self) -> str:
        return f"{self.prev_hash}|{self.timestamp}|{self.version}|{self.merkle_root}|{self.nonce}|{self.difficulty}"

    def hash(self) -> str:
        if self.is_genesis:
            return "00000000"
        return hash_generator(self.serialize())

    def mine(self, max_nonce: int = 10_000_000, start_nonce: int = 0) -> str:
        if self.is_genesis:
            return self.hash()
        target_prefix = "0" * self.difficulty
        nonce = start_nonce
        while nonce < max_nonce:
            self.nonce = nonce
            h = self.hash()
            if h.startswith(target_prefix):
                return h
            nonce += 1
        raise RuntimeError("Nonce nerastas per leistiną bandymų skaičių")

    def validate_proof_of_work(self) -> bool:
        if self.is_genesis:
            return self.hash() == "00000000"
        return self.hash().startswith("0" * self.difficulty)

    @staticmethod
    def validate_hash(hash_str: str, difficulty: int) -> bool:
        """Patikrina ar duotas hash atitinka difficulty (prefix nulių)."""
        return isinstance(hash_str, str) and hash_str.startswith("0" * difficulty)

    @classmethod
    def create_with_current_time(cls, prev_hash: str, merkle_root: str, version: int = 1, difficulty: int = 3) -> "BlockHeader":
        """Patogus konstruktorius nustatantis timestamp į dabartinį UTC laiką (s Unix)."""
        return cls(prev_hash=prev_hash, timestamp=int(time.time()), version=version, merkle_root=merkle_root, nonce=0, difficulty=difficulty)

    @classmethod
    def create_genesis(cls, merkle_root: str = "", version: int = 1, difficulty: int = 3, timestamp: Optional[int] = 0) -> "BlockHeader":
        """Sukuria genesis bloką; jo hash bus '00000000'."""
        ts = int(timestamp) if timestamp is not None else int(time.time())
        return cls(prev_hash="00000000", timestamp=ts, version=version, merkle_root=merkle_root, nonce=0, difficulty=difficulty, is_genesis=True)

    @classmethod
    def create_from_body(cls, prev_hash: str, body, version: int = 1, difficulty: int = 3) -> "BlockHeader":
        """
        Sukuria BlockHeader iš BlockBody objekto.
        Importuojame BlockBody lokaliai, kad būtų išvengta circular import problemų.
        """
        # lokalus import -- saugiau prieš circular import
        from Body import BlockBody  
        if not isinstance(body, BlockBody):
            raise TypeError("body turi būti BlockBody instancija")
        return cls.create_with_current_time(prev_hash=prev_hash, merkle_root=body.merkle_root, version=version, difficulty=difficulty)


