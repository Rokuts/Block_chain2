import sys
import json
import os
import re

from Body import BlockBody
from Header import BlockHeader
from merkel_root2 import build_block_body

# Statinis pasirinkimas: keiskite čia į True arba False
DEFAULT_USE_TREE: bool = True
DEFAULT_MINE: bool = True

def _format_levels_as_json(levels):
    """
    Paverčia lygius į JSON-ready struktūrą:
    [{"level": 0, "count": 5, "hashes": [...]}, ...]
    """
    return [
        {"level": idx, "count": len(lvl), "hashes": lvl[:] }
        for idx, lvl in enumerate(levels)
    ]

def build_genesis_block_from_csv(csv_path: str, prev_hash: str = "00000000", use_tree: bool = DEFAULT_USE_TREE, mine: bool = DEFAULT_MINE, difficulty: int = 3, max_nonce: int = 10_000_000):
    txs = None
    levels = None

    if use_tree:
        block_body = build_block_body(csv_path, show_tree=True)
        merkle_root = block_body.get("merkle_root")
        txs = block_body.get("transactions", [])
        levels = block_body.get("levels", None)
    else:
        body = BlockBody.from_csv(csv_path)
        merkle_root = body.merkle_root

    # Sukuriame header
    # sukonstruojame header su pageidaujamu difficulty (naudojama kasybai, jei mine=True)
    header = BlockHeader.create_with_current_time(prev_hash=prev_hash, merkle_root=merkle_root, difficulty=difficulty)


    # Pagrindinis blokas
    block = {
        
        "header": {
            "prev_hash": header.prev_hash,
            "timestamp": header.timestamp,
            "version": header.version,
            "merkle_root": header.merkle_root,
            "nonce": header.nonce,
            "difficulty": header.difficulty,
            
        },
        "body": {
            "merkle_root": merkle_root
        }
    }

    # Jei pasirenkame tree, pridedame jį JSON formatu
    if use_tree and levels is not None:
        block["body"]["merkle_tree_levels"] = _format_levels_as_json(levels)

    return block

if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Nenurodytas CSV failas!")
        sys.exit(1)

    csv_path = sys.argv[1]

    try:
        block = build_genesis_block_from_csv(csv_path)
    except Exception as e:
        print(f"Klaida: {e}")
        sys.exit(1)

    output_path = "block.txt"
    try:
        # sugeneruojame gražų JSON tekstą
        json_text = json.dumps(block, ensure_ascii=False, indent=2)

        # regex ras "hashes": [ ... ] blokus (su tarpais / newline) ir pakeis į vienos eilutės variantą
        pattern = re.compile(r'("hashes"\s*:\s*)\[\s*([^\]]*?)\s*\]', re.S)

        def _collapse_hashes(m):
            prefix = m.group(1)
            content = m.group(2)
            items = re.findall(r'"([^"]+)"', content)
            # formatuojame elementus tinkamai 
            single_line = "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in items) + "]"
            return prefix + single_line

        json_text = pattern.sub(_collapse_hashes, json_text)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_text)

    except Exception as e:
        print(f"Klaida įrašant failą: {e}")
        sys.exit(1)

    print(f"Rezultatai įrašyti į {output_path}")