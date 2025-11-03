import csv
import random
from pathlib import Path
from typing import List, Dict, Optional

def pick_random_transactions(csv_path: Optional[str] = None, n: int = 100, seed: Optional[int] = None) -> List[Dict[str, str]]:
    if csv_path is None:
        raise ValueError("Įveskite iš kurio csv failo skaityti – nurodykite parametrą csv_path.")

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
