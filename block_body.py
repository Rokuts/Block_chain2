import csv
import random
from pathlib import Path
from typing import List, Dict, Optional
import json
from tempfile import NamedTemporaryFile

# statiniai parametrai — pakeiskite čia
DEFAULT_N = 5
DEFAULT_SEED = 12345

def pick_random_transactions(csv_path: Optional[str] = None, n: int = 100, seed: Optional[int] = None, save_selected_path: Optional[str] = None) -> List[Dict[str, str]]:
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
        selected = rows
    else:
        selected = random.sample(rows, n)

    
    if save_selected_path:
        try:
            with open(save_selected_path, "w", encoding="utf-8") as sf:
                json.dump(selected, sf, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return selected

def remove_transactions_from_csv(csv_path: str, tx_ids: set) -> None:
    """
    Pašalina visas eilutes iš csv_path kurių pirmas stulpelis (transaction_id) yra tx_ids.
    Išsaugoma atgal į tą patį failą.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    # skaitymas ir rašymas naujam laikiniam failui, tada pakeitimas
    tmp_path = path.with_suffix(".tmp")
    with path.open(newline="", encoding="utf-8") as rf, tmp_path.open("w", newline="", encoding="utf-8") as wf:
        reader = csv.reader(rf)
        writer = csv.writer(wf)
        try:
            header = next(reader)
        except StopIteration:
            return
        writer.writerow(header)
        for row in reader:
            if not row:
                continue
            line_id = row[0].strip()
            if line_id not in tx_ids:
                writer.writerow(row)

    tmp_path.replace(path)
    print(f"Pašalinta {len(tx_ids)} transakcijų iš {csv_path}")

def apply_transactions_simple(txs: list, balances: Dict[str, float], allow_negative: bool = False):
    """
    Paprasta versija: tiesiog atnaujina balances in-place.
    Nebekaupia applied/skipped sąrašų (nereikalinga).
    """
    for tx in txs:
        tx_id = tx.get("id") or tx.get("transaction_id")
        sender = tx.get("sender") or tx.get("from") or tx.get("addr_from")
        receiver = tx.get("receiver") or tx.get("to") or tx.get("addr_to")
        if sender is None or receiver is None:
            continue

        # bandom paimti amount 
        raw_amount = tx.get("amount", 0)
        try:
            amount = float(raw_amount)
        except Exception:
            try:
                amount = float(str(raw_amount).replace(",", "."))
            except Exception:
                continue

        # užtikrinti, kad adresai egzistuoja balances
        balances.setdefault(sender, 0.0)
        balances.setdefault(receiver, 0.0)

        if not allow_negative and balances[sender] < amount:
            continue

        balances[sender] -= amount
        balances[receiver] += amount

    return

def load_balances_from_users_txt(path: str, key_by: str = "name") -> Dict[str, float]:
    
    balances: Dict[str, float] = {}
    meta: Dict[str, tuple] = {}  # key -> (name, public_key, original_balance_str)
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]
    # rasti header separator eilutę arba pradėti nuo 2
    start_idx = 0
    for i, ln in enumerate(lines[:5]):
        if ln.strip().startswith("-"):
            start_idx = i + 1
            break
    for ln in lines[start_idx:]:
        if not ln.strip():
            continue
        # split from right: name (may contain spaces), public_key, balance
        try:
            name_and_rest = ln.rstrip()
            name, public_key, bal_str = name_and_rest.rsplit(None, 2)
        except Exception:
            continue
        bal_clean = bal_str.replace(",", "").replace(" ", "")
        try:
            bal = float(bal_clean)
        except Exception:
            continue
        key = name if key_by == "name" else public_key
        balances[key] = bal
        meta[key] = (name, public_key, bal_str)
    return balances, meta

def save_balances_to_users_txt(path: str, balances: Dict[str, float], meta: Dict[str, tuple]) -> None:
    
    name_w = 30
    pk_w = 10
    bal_w = 12
    sep_width = name_w + 1 + pk_w + 1 + bal_w

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        header = f"{'Name':{name_w}} {'PublicKey':{pk_w}} {'Balance':>{bal_w}}\n"
        f.write(header)
        f.write("-" * sep_width + "\n")
        # rašome eilutes pagal meta (išlaikome tvarką meta.items())
        for key, (name, pub, _) in meta.items():
            bal = balances.get(key, 0.0)
            # formatavimas: sveikasis su tūkst. skyrikliais
            bal_str = f"{int(bal):,}"
            f.write(f"{name:{name_w}} {pub:{pk_w}} {bal_str:>{bal_w}}\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python block_body.py <tx_csv> <users_txt>")
        sys.exit(1)
    csv_path = sys.argv[1]
    users_path = sys.argv[2]

    # load balances keyed by public key (tx sender/receiver use public keys)
    balances, meta = load_balances_from_users_txt(users_path, key_by="public_key")

    transactions = pick_random_transactions(csv_path=csv_path, n=DEFAULT_N, seed=DEFAULT_SEED)

    # apply transactions 
    apply_transactions_simple(transactions, balances, allow_negative=False)

    # persist updated balances back to users.txt
    save_balances_to_users_txt(users_path, balances, meta)



