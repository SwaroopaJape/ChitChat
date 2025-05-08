import random

# Computes (a^s) mod n efficiently using modular exponentiation
def a_s_mod_n(a, s, n):

    result = 1

    while(s > 0):
        if(s & 1 == 1):
            result = (result * a) % n
        a = (a * a) % n
        s = s >> 1
    return result

# Miller-Rabin primality test for checking if n is probably prime
def miller_rabin(n, k):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    # n - 1 = 2^s * p
    p = n - 1
    s = 0
    while(p & 1 == 0):
        p >>= 1
        s += 1

    # Perform the test k times
    for i in range(k):
        a = random.randint(2, n - 1)
        x = a_s_mod_n(a, p, n)
        if x == 1 or x == n - 1:
            continue
        for r in range(s - 1):
            x = a_s_mod_n(x, 2, n)
            if x == n - 1:
                break
        else:
            return False

    return True

# Generates a large probable prime number of given bit length
def generate_large_prime(length):
    a = 1 << (length - 2)  
    b = (1 << length) - 1  
    while True:
        p = random.randint(a, b)
        p = p | 1          
        if miller_rabin(p, 40):
            return p

# Computes the greatest common divisor of a and b
def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

# Finds a suitable encryption exponent e such that gcd(e, phi) = 1
def find_e(phi):
    e = 3
    while gcd(e, phi) != 1:
        e += 2
    if(e < phi):
        return e
    else:
        return None

# Computes the modular inverse of a modulo n using Extended Euclidean Algorithm
def a_mod_inv_n(a, n):
    r1, r2 = n, a
    t1, t2 = 0, 1
    while r2 > 0:
        q = r1 // r2
        r1, r2 = r2, r1 - q * r2
        t1, t2 = t2, t1 - q * t2
    if r1 != 1:
        return None
    if t1 < 0:
        t1 += n
    return t1

# Generates RSA keypair (n, e, d) of the specified bit length
def generate_keypair(length):
    
    while True:
        p = generate_large_prime(length)
        q = generate_large_prime(length)
        if p != q:
            break

    n = p * q
    phi = (p - 1) * (q - 1)

    e = find_e(phi)
    if e is None:
        return None

    d = a_mod_inv_n(e, phi)
    if d is None:
        return None

    return (n, e, d)

# Decrypts ciphertext using private key (d, n)
def decrypt(ciphertext, n, d):
    if ciphertext < 0 or ciphertext >= n:
        return None
    if d < 0 or d >= n:
        return None
    if n <= 1:
        return None
    plaintext = a_s_mod_n(ciphertext, d, n)
    return plaintext

# Encrypts plaintext using public key (e, n)
def encrypt(plaintext, n, e):

    if plaintext < 0 or plaintext >= n:
        return None
    if e < 0 or e >= n:
        return None
    if n <= 1:
        return None

    ciphertext = a_s_mod_n(plaintext, e, n)
    return ciphertext
