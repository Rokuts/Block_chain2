import random
from user_generator import UserGenerator

random.seed() 

gen = UserGenerator(n_users=10)
users = gen.generate()

gen.to_text_file('users.txt')
print("Saved users.txt")
