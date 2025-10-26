import time

def hash_generator(tekstas):

    # Paverčiam tekstą į sąrašą skaičių (ASCII)
    skaiciai = [ord(c) for c in tekstas]   # skaiciu masyvas

    
    d1 = 828930167
    suma = d1  # pradinis sumos reikšmė

    for i, skaicius in enumerate(skaiciai):
        suma = suma ^ (skaicius * d1)  # XOR su kiekvienu skaičiumi * d1
        suma = (suma * d1) % 0x100000000  # daliname is Ox100000000, kad isvengtume per daug simboliu hash

    # Papildomas maišymas pabaigoje
    suma = (suma << 13 | suma >> (32 - 13)) & 0xFFFFFFFF

    hash = f"{suma:08x}" # skaiciaus formatavimas i hex su 8 simboliais
    return hash
