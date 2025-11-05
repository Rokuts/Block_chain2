import time
import sys
import os
import json
from typing import Optional, List
from multiprocessing import Process, Manager, Lock

from Header import BlockHeader
from block_body import pick_random_transactions, remove_transactions_from_csv
from merkel_root2 import compute_merkle_root_from_tx_list

def generate_candidates(csv_path: str, prev_hash: str = "00000000", n_candidates: int = 5, txs_per: int = 100, seed: Optional[int] = None, difficulty: int = 3) -> List[BlockHeader]:
    candidates = []
    for i in range(n_candidates):
        seed_i = (seed + i) if (seed is not None) else None
        txs = pick_random_transactions(csv_path=csv_path, n=txs_per, seed=seed_i)
        merkle_root = compute_merkle_root_from_tx_list(txs)
        header = BlockHeader.create_with_current_time(prev_hash=prev_hash, merkle_root=merkle_root, difficulty=difficulty)
        setattr(header, "_txs", txs)
        candidates.append(header)
    return candidates

def mine_candidate_mp(i, header, winner, stats, lock, deadline):
    start_time = time.time()
    while time.time() < deadline and winner["header"] is None:
        header.nonce += 1
        stats[i]["tries"] += 1
        h = header.hash()
        if BlockHeader.validate_hash(h, header.difficulty):
            with lock:
                if winner["header"] is None:
                    winner["header"] = header
                    winner["hash"] = h
                    winner["idx"] = i   # <-- pridėtas indeksas
                    stats[i]["found"] = True
                    stats[i]["time"] = time.time() - start_time

            break

def try_mine_parallel_multiprocessing(candidates: List[BlockHeader], time_limit_sec: float):
    manager = Manager()
    winner = manager.dict({"header": None, "hash": None, "idx": None})
    # kiekvienas įrašas dabar manager.dict, kad mutacijos iš subprocess'ų būtų matomos
    stats = manager.list([manager.dict({"tries": 0, "found": False, "time": None}) for _ in range(len(candidates))])
    lock = Lock()

    deadline = time.time() + time_limit_sec

    processes = []
    for i, header in enumerate(candidates):
        p = Process(target=mine_candidate_mp, args=(i, header, winner, stats, lock, deadline))
        processes.append(p)
        p.start()

    # Laukiame tik iki laiko limito arba kol randamas laimėtojas
    while time.time() < deadline:
        if winner["header"] is not None:
            break
        time.sleep(0.01)  # nedidelis delay, kad CPU nebūtų perkrautas

    # Nutraukiame likusius procesus
    for p in processes:
        if p.is_alive():
            p.terminate()

    # Konvertuoti į įprastus dict'ai, kad pagrindinis procesas gautų reikšmes
    stats_list = [dict(s) for s in stats]
    return winner["header"], winner["hash"], winner["idx"], stats_list



def append_block_to_chain(block: dict, chain_path: str = "chain.json"):
    chain = []
    if os.path.isfile(chain_path):
        try:
            with open(chain_path, "r", encoding="utf-8") as f:
                chain = json.load(f) or []
        except Exception:
            chain = []
    chain.append(block)
    with open(chain_path, "w", encoding="utf-8") as f:
        json.dump(chain, f, ensure_ascii=False, indent=2)

def build_block_dict(header: BlockHeader, block_hash: str) -> dict:
    txs = getattr(header, "_txs", [])
    serialize = f"{header.prev_hash}|{header.timestamp}|{header.version}|{header.merkle_root}|{header.nonce}|{header.difficulty}"
    block = {
        "Block_hash": block_hash,
        "header": {
            "prev_hash": header.prev_hash,
            "timestamp": header.timestamp,
            "version": header.version,
            "merkle_root": header.merkle_root,
            "nonce": header.nonce,
            "difficulty": header.difficulty,
            "serialize": f"{serialize} ---> {block_hash}"
        },
        "body": {
            "merkle_root": header.merkle_root,
            "transactions_count": len(txs),
            "transactions": txs
        }
    }
    return block

def main():
    if len(sys.argv) < 2:
        print("Usage: python procesas.py <tx_csv> [time_limit_seconds] [difficulty]")
        sys.exit(1)

    csv_path = sys.argv[1]
    initial_time_limit = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    difficulty = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    prev_hash = "00000000"
    print(f"\n Pradedamas kasimo procesas")
    print(f"CSV: {csv_path}")
    print(f"Kandidatai: 5 blokai po 100 transakcijų")
    print(f"Pradinė trukmė: {initial_time_limit}s, sunkumas: {difficulty}\n")

    candidates = generate_candidates(csv_path, prev_hash, 5, 100, 12345, difficulty)
    for i, c in enumerate(candidates, start=1):
        print(f" Kandidatas #{i}: merkle_root={c.merkle_root}")

    print("\n Pradedamas kasybos raundas...\n")

    time_limit = initial_time_limit
    max_attempts = 6
    winner_header = None
    winner_hash = None

    for attempt in range(max_attempts):
        print(f" Bandymas #{attempt+1}: laiko limitas = {time_limit:.1f}s")
        start = time.time()
        winner_header, winner_hash, winner_idx, stats = try_mine_parallel_multiprocessing(candidates, time_limit)
        duration = time.time() - start

        # parodyti kiek kiekvienas bandė
        for i, s in enumerate(stats):
            print(f"   • Kandidatas #{i+1}: bandymai = {s['tries']}")

        if winner_header:
            winner_idx += 1  # 1-based
            time_taken = stats[winner_idx-1]['time']
            tries_done = stats[winner_idx-1]['tries']
            if time_taken is None:
                time_taken = 0.0
            print(f"\nLaimėjo kandidatas #{winner_idx} su hash: {winner_hash}")
            print(f"    Rado per {time_taken:.3f}s, atlikęs {tries_done} bandymų")
            break
        else:
            print(f" Niekas neiškasė per {duration:.2f}s – didiname laiką iki {time_limit*2:.1f}s\n")
            time_limit *= 2

    if winner_header:
        block = build_block_dict(winner_header, winner_hash)
        append_block_to_chain(block, "chain.json")

        try:
            txs = getattr(winner_header, "_txs", [])
            tx_ids = {tx.get("transaction_id") or tx.get("id") for tx in txs if isinstance(tx, dict)}
            if tx_ids:
                remove_transactions_from_csv(csv_path, tx_ids)
        except Exception:
            pass

        print("\n Blokas įtrauktas į grandinę (chain.json)")
    else:
        print("\n Nei vienas blokas neiškastas – padidinkite ribas rankiniu būdu.")


if __name__ == "__main__":
    main()
