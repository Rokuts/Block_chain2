from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from block_body import pick_random_transactions
from merkel_root2 import compute_merkle_root_from_tx_list
import sys
import json

DEFAULT_N = 5
DEFAULT_SEED = 12345

@dataclass
class BlockBody:
    transactions: List[Dict[str, Any]]
    merkle_root: Optional[str] = None

    def __post_init__(self) -> None:
        if self.transactions is None:
            raise ValueError("transactions negali būti None")
        if self.merkle_root is None:
            # apskaičiuojame Merkle root, jei nebuvo pateiktas
            self.merkle_root = compute_merkle_root_from_tx_list(self.transactions)

    @classmethod
    def from_csv(cls, csv_path: str, n: int = DEFAULT_N, seed: Optional[int] = DEFAULT_SEED) -> "BlockBody":
        txs = pick_random_transactions(csv_path=csv_path, n=n, seed=seed)
        return cls(txs)

    def to_dict(self) -> Dict[str, Any]:
        return {"transactions": self.transactions, "merkle_root": self.merkle_root}

    def __repr__(self) -> str:
        return f"BlockBody(transactions={len(self.transactions)}, merkle_root={self.merkle_root})"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Is kokio csv failo skaityti?")
        sys.exit(1)

    csv_path = sys.argv[1]
    n = DEFAULT_N
    seed = DEFAULT_SEED

    try:
        block = BlockBody.from_csv(csv_path, n=n, seed=seed)
    except Exception as e:
        print(f"Klaida: {e}")
        sys.exit(1)

    print(json.dumps(block.to_dict(), ensure_ascii=False, indent=2))