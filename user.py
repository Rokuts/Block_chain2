from dataclasses import dataclass, asdict
from typing import Dict

@dataclass
class User:
    name: str
    public_key: str
    balance: int

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def adjust_balance(self, amount: int) -> None:
        if self.balance + amount < 0:
            raise ValueError(f"Vartotojas neturi pakankamai lėšų! Balansas: {self.balance}, bandai pakeisti {amount}")
        self.balance += amount

    def __repr__(self) -> str:
        return f"User(name={self.name!r}, pk={self.public_key}, balance={self.balance})"

