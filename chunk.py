import csv
from typing import List, Dict, Optional
import sys
import random

DEFAULT_N_MTXS = 5
DEFAULT_OUT = "chunks.txt"
DEFAULT_SEED: Optional[int] = 12345  # pakeitus į None gaunasi skirtingi chunk'ai kiekvieną kartą

def chunk_transactions(csv_path: str, n_mtxs: int = DEFAULT_N_MTXS, seed: Optional[int] = DEFAULT_SEED) -> List[List[Dict[str, str]]]:
    with open(csv_path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    if seed is not None:
        rnd = random.Random(seed)
        rnd.shuffle(rows)

    chunks: List[List[Dict[str, str]]] = [rows[i:i + n_mtxs] for i in range(0, len(rows), n_mtxs)]
    return chunks

def write_chunks_to_file(chunks: List[List[Dict[str, str]]], out_path: str = DEFAULT_OUT, n_mtxs: int = DEFAULT_N_MTXS) -> None:
    with open(out_path, "w", encoding="utf-8", newline='') as f:
        f.write(f"Blocks: {len(chunks)}\n")
        f.write(f"Each: {n_mtxs} txs\n\n")

        if not chunks:
            return

        fieldnames = list(chunks[0][0].keys())
        writer = csv.writer(f)
        writer.writerow(fieldnames)

        for i, chunk in enumerate(chunks, start=1):
            f.write(f"=== block {i} ===\n")
            for row in chunk:
                writer.writerow([row.get(k, "") for k in fieldnames])
            f.write("\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Pateik CSV faila is kurio nori skaityti tranzakcijas.")
        sys.exit(1)

    csv_path = sys.argv[1]

    chunks = chunk_transactions(csv_path)
    write_chunks_to_file(chunks)
    print(f"Išrašyta {len(chunks)} chunk'ų į '{DEFAULT_OUT}' (n_mtxs={DEFAULT_N_MTXS}, seed={DEFAULT_SEED}).")