import sys
import json
import os
import re
import csv

from Body import BlockBody
from Header import BlockHeader
from merkel_root2 import build_block_body
from block_body import pick_random_transactions, remove_transactions_from_csv

# Statinis pasirinkimas: keiskite čia į True arba False
DEFAULT_USE_TREE: bool = False
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

def build_genesis_block_from_csv(csv_path: str, prev_hash: str = "00000000", use_tree: bool = DEFAULT_USE_TREE, mine: bool = DEFAULT_MINE, difficulty: int = 3, max_nonce: int = 10_000_000, users_path: str = None):
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

    # Mine pakeis header.nonce.
    try:
        if mine:
            found_hash = header.mine(max_nonce=max_nonce)
        else:
            found_hash = header.hash()
    except RuntimeError as e:
        print(f"Klaida kasant bloką: {e}")
        sys.exit(1)

    # Patikriname rastą hash 
    if mine and not BlockHeader.validate_hash(found_hash, header.difficulty):
        print("Kasyba nebuvo sėkminga: rastas hash neatitinka difficulty reikalavimo.")
        sys.exit(1)

    serialize = f"{header.prev_hash}|{header.timestamp}|{header.version}|{header.merkle_root}|{header.nonce}|{header.difficulty}"

    # Pagrindinis blokas
    block = {
        "Block_hash": found_hash,
        "header": {
            "prev_hash": header.prev_hash,
            "timestamp": header.timestamp,
            "version": header.version,
            "merkle_root": header.merkle_root,
            "nonce": header.nonce,
            "difficulty": header.difficulty,
            "serialize": f'{serialize} ---> {found_hash}'
        },
        "body": {
            "merkle_root": merkle_root
        }
    }

    # Jei pasirenkame tree, pridedame jį JSON formatu
    if use_tree and levels is not None:
        block["body"]["merkle_tree_levels"] = _format_levels_as_json(levels)

    # Pašaliname į bloką įtrauktas transakcijas iš CSV 
    if txs:
        tx_ids_in_block = set()
        for tx in txs:
            if not tx:
                continue
            if isinstance(tx, dict):
                tid = tx.get("transaction_id") or tx.get("id")
            elif isinstance(tx, str):
                tid = tx
            else:
                tid = getattr(tx, "transaction_id", None)
            if tid:
                tx_ids_in_block.add(tid)

        if tx_ids_in_block and os.path.isfile(csv_path):
            try:
                remove_transactions_from_csv(csv_path, tx_ids_in_block)
            except Exception as e:
                print(f"Įspėjimas: nepavyko pašalinti transakcijų iš CSV: {e}")

    # Naujas: atnaujinti users.txt jei pateiktas kelias
    if users_path and txs:
        try:
            from block_body import load_balances_from_users_txt, apply_transactions_simple, save_balances_to_users_txt
            balances, meta = load_balances_from_users_txt(users_path, key_by="public_key")
            # txs turi turėti laukus 'sender','receiver','amount' (atitinka transactions_min.csv)
            apply_transactions_simple(txs, balances, allow_negative=False)
            save_balances_to_users_txt(users_path, balances, meta)
        except Exception as e:
            print(f"Įspėjimas: nepavyko atnaujinti users.txt: {e}")

    return block

def _count_transactions_in_csv(csv_path: str) -> int:
    path = os.path.abspath(csv_path)
    if not os.path.isfile(path):
        return 0
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return 0
        # count non-empty rows
        return sum(1 for row in reader if row and any(cell.strip() for cell in row))

# Pridėta: įrašyti vienos eilutės hash grandinę į failą
def _write_hashes_line_from_chainfile(chain_path="chain.json", line_path="hashes_line.txt"):
    try:
        chain = []
        if os.path.isfile(chain_path):
            with open(chain_path, "r", encoding="utf-8") as f:
                chain = json.load(f) or []
        parts = ["00000000"]
        for b in chain:
            h = b.get("Block_hash") or b.get("block_hash") or ""
            if h:
                parts.append(h)
        line = " <--- ".join(parts)
        with open(line_path, "w", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print(f"Įspėjimas: nepavyko įrašyti vienos eilutės hash failo: {e}")

def mine_chain_from_csv(csv_path: str, users_path: str = "users.txt", use_tree: bool = True, difficulty: int = 3, max_nonce: int = 10_000_000, block_limit: int = None, output_path: str = "chain.json", print_to_console: bool = False, print_each_block: bool = False):
    """
    Kasa blokus iteratyviai tol kol CSV tuščias.
    Grąžina list'ą blokų ir išsaugo į output_path.
    Jei print_to_console True, taip pat išveda rezultatus į konsolę.
    """
    chain = []
    prev_hash = "00000000"
    idx = 0

    while True:
        remaining = _count_transactions_in_csv(csv_path)
        if remaining == 0:
            print("Nėra daugiau transakcijų CSV faile. Baigiama kasyba.")
            break
        if block_limit is not None and idx >= block_limit:
            print(f"Pasiektas block limit: {block_limit}. Sustojama.")
            break

        print(f"Kasant bloką #{idx} (liko transakcijų: {remaining})...")
        try:
            block = build_genesis_block_from_csv(csv_path, prev_hash=prev_hash, use_tree=use_tree, mine=True, difficulty=difficulty, max_nonce=max_nonce, users_path=users_path)
        except Exception as e:
            print(f"Klaida kasant bloką #{idx}: {e}")
            break

        chain.append(block)
        # jeigu reikalaujama, išvedame kiekvieną bloką į konsolę (valdo print_each_block)
        if print_each_block:
            try:
                print(json.dumps(block, ensure_ascii=False, indent=2))
            except Exception:
                # jei spausdinimas nepavyksta dėl didelio turinio, tiesiog praleidžiame
                pass

        prev_hash = block.get("Block_hash", prev_hash)
        idx += 1

    # Išsaugome grandinę JSON formatu
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chain, f, ensure_ascii=False, indent=2)
        print(f"Grandinė išsaugota į {output_path} ({len(chain)} blokai).")
    except Exception as e:
        print(f"Įspėjimas: nepavyko įrašyti grandinės: {e}")

    # Nauja: sukurti vienos eilutės hash failą (pvz. hashes_line.txt)
    try:
        _write_hashes_line_from_chainfile(chain_path=output_path, line_path="hashes_line.txt")
        print("Hash grandinė įrašyta į hashes_line.txt")
    except Exception:
        pass

    # jei pageidaujama, atspausdiname pilną grandinę (vieną kartą)
    if print_to_console:
        try:
            print(json.dumps(chain, ensure_ascii=False, indent=2))
        except Exception:
            pass

    return chain

if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Nenurodytas CSV failas!")
        sys.exit(1)

    csv_path = sys.argv[1]
    # pagal nutylėjimą atnaujiname balances į users.txt, nebent nurodysite kitą failą
    users_path = sys.argv[2] if len(sys.argv) > 2 else "users.txt"

    # galiU perduoti trečią argumentą "single" jei noriU vieno bloko generavimo 
    # arba "chain" (numatytoji) - kasa tol kol csv tuščias.
    mode = sys.argv[3] if len(sys.argv) > 3 else "chain"

    # nauja: jei nurodote 'console' arba '--console' bet kuriame argv, išvesime į konsolę taip pat
    print_to_console = ("console" in sys.argv) or ("--console" in sys.argv)

    try:
        if mode == "single":
            # Paruošiame grandinės failą (jei egzistuoja, nuskaitome paskutinį hash)
            chain_path = "chain.json"
            prev_hash = "00000000"
            chain = []
            if os.path.isfile(chain_path):
                try:
                    with open(chain_path, "r", encoding="utf-8") as cf:
                        chain = json.load(cf) or []
                    if chain:
                        prev_hash = chain[-1].get("Block_hash", prev_hash)
                except Exception:
                    print("Įspėjimas: nepavyko perskaityti esamos grandinės, bus sukurtas naujas.")
                    chain = []

            # Iškasame vieną bloką, naudojant prev_hash iš grandinės (jei yra)
            block = build_genesis_block_from_csv(csv_path, prev_hash=prev_hash, users_path=users_path, use_tree=True, mine=True, difficulty=3, max_nonce=10_000_000)

            # Rašome vieną block.txt
            with open("block.txt", "w", encoding="utf-8") as f:
                f.write(json.dumps(block, ensure_ascii=False, indent=2))

            # Pridedame bloką prie chain.json
            chain.append(block)
            try:
                with open(chain_path, "w", encoding="utf-8") as cf:
                    json.dump(chain, cf, ensure_ascii=False, indent=2)
                print(f"Blokas pridėtas prie {chain_path}.")
            except Exception as e:
                print(f"Įspėjimas: nepavyko įrašyti grandinės: {e}")

            # Nauja: atnaujinti vienos eilutės hash failą
            try:
                _write_hashes_line_from_chainfile(chain_path=chain_path, line_path="hashes_line.txt")
                print("Hash grandinė įrašyta į hashes_line.txt")
            except Exception:
                pass

            # jei prašyta, taip pat atspausdiname
            if print_to_console:
                try:
                    print(json.dumps(block, ensure_ascii=False, indent=2))
                except Exception:
                    pass

            print("Viena bloko operacija užbaigta.")
        else:
            # kasa grandinę tol kol CSV tuščias
            mine_chain_from_csv(csv_path, users_path=users_path, use_tree=True, difficulty=3, max_nonce=10_000_000, block_limit=None, output_path="chain.json", print_to_console=print_to_console)

    except Exception as e:
        print(f"Klaida: {e}")
        sys.exit(1)