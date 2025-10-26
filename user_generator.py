import random, secrets
from typing import List
from user import User         
from my_hash_function import hash_generator 

class UserGenerator:
    def __init__(self, n_users: int = 1000, min_bal: int = 100, max_bal: int = 1_000_000):
        self.n = n_users
        self.min_bal = min_bal
        self.max_bal = max_bal
        self.users: List[User] = []

        self.first_names = ["Aistis","Benas","Domas","Jokubas","Fabrielius","Algirdas","Jonas","Kęstutis","Linas","Mindaugas"]
        self.last_names = ["Kazlauskas","Petraitis","Jankauskas","Stankevičius","Paulauskas","Vilkas","Bublys","Baronas"]

    def _make_name(self, idx:int) -> str:
        return f"#{idx} {random.choice(self.first_names)} {random.choice(self.last_names)}"


    def _make_public_key_8(self, name:str) -> str:
        return hash_generator(name)

    def _make_balance(self) -> int:
        return random.randint(self.min_bal, self.max_bal)

    def generate(self) -> List[User]:
        self.users.clear()
        for i in range(1, self.n + 1):
            name = self._make_name(i)
            pk = self._make_public_key_8(name)
            bal = self._make_balance()
            self.users.append(User(name=name, public_key=pk, balance=bal))
        return self.users

    def to_text_file(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            header = f"{'Name':30} {'PublicKey':10} {'Balance':>12}\n"
            f.write(header)
            f.write("-" * len(header) + "\n")
            for u in self.users:
                f.write(f"{u.name:30} {u.public_key:10} {u.balance:12,}\n")
