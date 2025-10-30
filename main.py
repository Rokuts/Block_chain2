import random
from user_generator import UserGenerator
from transaction_generator import UTXOGenerator

random.seed()

# Parametrai demonstracijai
N_USERS, N_UTXOS, N_TXS = 5, 4, 25

# Generuojame users
user_gen = UserGenerator(n_users=N_USERS)
users = user_gen.generate()
user_gen.to_text_file('users.txt')

# Generuojame transactions
tx_gen = UTXOGenerator(users)
tx_gen.create_genesis_utxos(n_per_user=N_UTXOS)
tx_gen.generate_transactions(n_txs=N_TXS)
tx_gen.save_transactions('transactions.txt')
tx_gen.save_minimal_csv('transactions_min.csv')



print(f"\nCreated {N_USERS} users and {len(tx_gen.transactions)} transactions")
