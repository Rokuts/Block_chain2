import random
import time
from typing import List
from dataclasses import dataclass, asdict
from my_hash_function import hash_generator  # <- naudok savo hash
from user import User  # Ensure to import the User class

@dataclass
class UTXO:
    transaction_id: str
    tr_index: int
    owner: str
    amount: int

@dataclass
class Transaction:
    transaction_id: str
    inputs: List[UTXO]
    outputs: List[UTXO]

class UTXOGenerator:
    def __init__(self, users: List[User]):
        self.users = users
        self.utxos: List[UTXO] = []  # dabartiniai „unspent“ išėjimai
        self.transactions: List[Transaction] = []

    def create_genesis_utxos(self, n_per_user: int = 3):
        """Sukuria pradinius UTXO kiekvienam user pagal jų balance."""
        self.utxos.clear()
        for user in self.users:
            # Paskirstome user'io balance į kelis UTXO
            remaining_balance = user.balance
            
            for i in range(n_per_user):
                # Paskutinis UTXO gauna likusį balansą
                if i == n_per_user - 1:
                    amount = remaining_balance
                else:
                    # Atsitiktinai paskirstome 10-30% balanso
                    amount = int(remaining_balance * random.uniform(0.1, 0.3))
                    remaining_balance -= amount
                
                if amount <= 0:
                    break
                    
                # Genesis be laiko - deterministinis
                transaction_id = hash_generator(f"genesis-{user.public_key}-{i}")
                self.utxos.append(UTXO(transaction_id=transaction_id, tr_index=i, owner=user.public_key, amount=amount))
        

    def generate_transactions(self, n_txs: int = 1000, max_inputs: int = 3):
        """Generuoja transakcijas, optimizuoja input skaičių."""
        for _ in range(n_txs):
            if len(self.utxos) < 1:
                break

            # Pasirenkam siuntėją
            seed_utxo = random.choice(self.utxos)
            sender_pk = seed_utxo.owner
            owner_utxos = [u for u in self.utxos if u.owner == sender_pk]
            if not owner_utxos:
                continue

            # Pasirenkam gavėją
            receiver = random.choice(self.users)
            while receiver.public_key == sender_pk:
                receiver = random.choice(self.users)

            # Pasirenkam sumą
            total_available = sum(u.amount for u in owner_utxos)

            if random.random() < 0.3:  # 30% atvejų - didelė suma (reikės kelių input'ų)
                target_amount = int(total_available * random.uniform(0.6, 0.9))
            else:  # 70% atvejų - maža suma (pakanka vieno input'o)
                target_amount = int(owner_utxos[0].amount * random.uniform(0.3, 0.9))
            
            # OPTIMIZACIJA: Renkam TIK kiek reikia input'ų
            input_utxos = []
            total_input = 0
            
            # Surūšiuojam UTXO nuo mažiausio (pirmiau suvalgys mažesnius)
            sorted_utxos = sorted(owner_utxos, key=lambda u: u.amount)
            
            for utxo in sorted_utxos:
                if total_input >= target_amount or len(input_utxos) >= max_inputs:
                    break
                input_utxos.append(utxo)
                total_input += utxo.amount
            
            # PATAISYMAS: Jei nepakanka pinigų, koreguojame sumą vietoj praleisti TX
            if total_input < target_amount:
                target_amount = int(total_input * random.uniform(0.5, 0.9))  # Siunčiame tik dalį turimų
            
            # Jei per maža suma liko, praleisti
            if target_amount < 1 or not input_utxos:
                continue
            
            # Pašalinam panaudotus UTXO
            for u in input_utxos:
                self.utxos.remove(u)

            # Generuojam transaction_id (deterministiškai)
            tx_str = "|".join(
                [sender_pk, receiver.public_key, str(target_amount)]
                + [f"{u.transaction_id}:{u.tr_index}" for u in input_utxos]
            )
            transaction_id = hash_generator(tx_str)

            # Outputs
            change = total_input - target_amount
            outputs = [UTXO(transaction_id=transaction_id, tr_index=0, owner=receiver.public_key, amount=target_amount)]
            
            if change > 0:
                outputs.append(UTXO(transaction_id=transaction_id, tr_index=1, owner=sender_pk, amount=change))

            tx = Transaction(transaction_id=transaction_id, inputs=input_utxos, outputs=outputs)
            self.transactions.append(tx)
            self.utxos.extend(outputs)

    def save_transactions(self, path: str):
        """Saves transactions in a detailed, readable format."""
        # Sukuriame žodyną transaction_id -> numeris
        tx_id_to_num = {tx.transaction_id: idx for idx, tx in enumerate(self.transactions, 1)}
        
        with open(path, 'w', encoding='utf-8') as f:
            for idx, tx in enumerate(self.transactions, 1):
                f.write(f"[Transaction #{idx:05d}]\n")
                f.write(f"Transaction ID: {tx.transaction_id}\n\n")
                
                f.write("Inputs:\n")
                for i, inp in enumerate(tx.inputs):
                    sender_name = next((user.name for user in self.users if user.public_key == inp.owner), "Unknown")
                    
                    # Patikriname ar input'as yra iš genesis ar iš ankstesnės TX
                    if inp.transaction_id in tx_id_to_num:
                        tx_ref = f"TX #{tx_id_to_num[inp.transaction_id]:05d}"
                    else:
                        tx_ref = "Genesis"
                    
                    f.write(f"   ({i}) {tx_ref} → {sender_name} : {inp.amount}\n")
                
                f.write("\nOutputs:\n")
                for i, out in enumerate(tx.outputs):
                    receiver_name = next((user.name for user in self.users if user.public_key == out.owner), "Unknown")
                    change_text = " (change)" if i > 0 else ""
                    f.write(f"   ({i}) {receiver_name} : {out.amount}{change_text}\n")
                
                f.write("\n---------------------------------------------------\n\n")

    def save_minimal_csv(self, path: str):
        """Išsaugo minimalų CSV: transaction_id,sender,receiver,amount."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write("transaction_id,sender,receiver,amount\n")
            for tx in self.transactions:
                sender = tx.inputs[0].owner if tx.inputs else ""
                # Parenkam gavėjo output (jei yra change atgal siuntėjui – praleidžiam)
                if tx.outputs:
                    recv_out = next((o for o in tx.outputs if o.owner != sender), tx.outputs[0])
                    receiver = recv_out.owner
                    amount = recv_out.amount
                else:
                    receiver, amount = "", 0
                f.write(f"{tx.transaction_id},{sender},{receiver},{amount}\n")

    @staticmethod
    def load_users_from_file(path: str) -> List[User]:
        """Loads users from a text file."""
        users = []
        with open(path, 'r', encoding='utf-8') as f:
            next(f)  # skip header
            next(f)  # skip dashed line
            for line in f:
                parts = line.strip().split()
                
                # Find the public key by looking for an 8-character hex string
                for i, part in enumerate(parts):
                    if len(part) == 8 and all(c in '0123456789abcdef' for c in part.lower()):
                        # Everything before this is the name
                        name = ' '.join(parts[:i])  # ✅
                        public_key = part
                        # Remove commas from balance and convert to int
                        balance = int(parts[i + 1].replace(',', ''))
                        users.append(User(name=name, public_key=public_key, balance=balance))
                        break
        return users

