import csv
import random
from pathlib import Path
from typing import List, Dict, Optional

# statiniai parametrai — pakeiskite čia
DEFAULT_N = 5
DEFAULT_SEED = 12345

def pick_random_transactions(csv_path: Optional[str] = None, n: int = 100, seed: Optional[int] = None) -> List[Dict[str, str]]:
    if csv_path is None:
        raise ValueError("Įveskite iš kurio csv failo skaityti - nurodykite parametrą csv_path.")

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if seed is not None:
        random.seed(seed)

    if not rows:
        return []

    if len(rows) <= n:
        random.shuffle(rows)
        return rows

    return random.sample(rows, n)

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 1:
        print("Is kokio csv failo skaityti?")
        sys.exit(1)

    csv_path = sys.argv[1]
    n = DEFAULT_N
    seed = DEFAULT_SEED

    try:
        transactions = pick_random_transactions(csv_path=csv_path, n=n, seed=seed)
    except Exception as e:
        print(f"Klaida: {e}")
        sys.exit(1)

    for tx in transactions:
        print(tx)
