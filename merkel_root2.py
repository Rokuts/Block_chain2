from typing import Iterable, List, Any, Dict, Tuple
from my_hash_function import hash_generator
import os
from block_body import pick_random_transactions
import sys
import json

# DEFAULT_TREE nustato numatytąjį elgesį — True rašyti tree.txt, False vykdyti tik minimalų Merkle root skaičiavimą.
DEFAULT_TREE: bool = False
DEFAULT_N = 5   # numatytasis atsitiktinių transakcijų skaičius
DEFAULT_SEED = 12345

def compute_merkle_root_from_tx_list(tx_list: Iterable[Any], show_tree: bool = DEFAULT_TREE):
    """
    Apskaičiuoja Merkle root.
    Jei show_tree=True, papildomai surenka lygius ir grąžina (root, levels).
    Jei show_tree=False, grąžina tik root (string).
    """
    if tx_list is None:
        raise ValueError("tx_list negali būti None")

    def _leaf_hash(item: Any) -> str:
        if not isinstance(item, dict):
            raise TypeError("Kiekvienas elementas turi būti dict (CSV eilutė).")
        sender = item.get("sender", "")
        receiver = item.get("receiver", "")
        amount = item.get("amount", "")
        inputs_field = item.get("inputs", "")
        inputs_list = inputs_field.split(";") if inputs_field else []
        parts = [sender, receiver, str(amount)] + [p for p in inputs_list if p]
        tx_str = "|".join(parts)
        return hash_generator(tx_str)

    leaves: List[str] = [_leaf_hash(it) for it in tx_list]

    if not leaves:
        raise ValueError("Nėra lapų Merkle root skaičiavimui")

    # Minimalus skaičiavimas be medžio išsaugojimo
    def _compute_root_min(current_level: List[str]) -> str:
        while len(current_level) > 1:
            next_level: List[str] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                parent = hash_generator(left + right)
                next_level.append(parent)
            current_level = next_level
        return current_level[0]

    # jei nereikia medžio, grąžiname tik root
    if not show_tree:
        return _compute_root_min(leaves[:])

    # Surenkame visus lygius
    levels: List[List[str]] = [leaves[:]]
    current = leaves[:]
    while len(current) > 1:
        next_level: List[str] = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else left
            parent = hash_generator(left + right)
            next_level.append(parent)
        levels.append(next_level[:])
        current = next_level

    root = current[0]
    return root, levels

def build_block_body(csv_path: str, n: int = DEFAULT_N, seed: int = DEFAULT_SEED, show_tree: bool = DEFAULT_TREE) -> Dict[str, Any]:
    """
    Pasirenka atsitiktines transakcijas, apskaičiuoja Merkle root.
    Jei show_tree=True, grąžina ir levels.
    """
    txs = pick_random_transactions(csv_path=csv_path, n=n, seed=seed)
    result = compute_merkle_root_from_tx_list(txs, show_tree=show_tree)
    if show_tree:
        merkle_root, levels = result
        return {"transactions": txs, "merkle_root": merkle_root, "levels": levels}
    else:
        merkle_root = result
        return {"transactions": txs, "merkle_root": merkle_root}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Is kokio csv failo skaityti?")
        sys.exit(1)

    csv_path = sys.argv[1]
    block = build_block_body(csv_path, n=DEFAULT_N, seed=DEFAULT_SEED)
    print(json.dumps(block, ensure_ascii=False, indent=2))
    sys.exit(0)