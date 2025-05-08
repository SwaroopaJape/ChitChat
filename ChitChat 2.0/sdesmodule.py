# function for P10 permutation
def P10(bin_str):
    p10 = [2, 5, 1, 7, 3, 9, 0, 8, 6, 4]
    ans = ""
    for i in p10:
        ans += bin_str[i]
    return ans

# function for P8 permutation
def P8(bin_str):
    p8 = [5, 2, 6, 3, 7, 4, 9, 8]
    ans = ""
    for i in p8:
        ans += bin_str[i]
    return ans

# function for left shift 1
def LS1(bin_str):
    return bin_str[1:] + bin_str[0]

# function for left shift 2
def LS2(bin_str):
    return bin_str[2:] + bin_str[:2]

# function to generate keys
def key_generation(key):
    binary = bin(key)[2:]
    binary = binary.zfill(10)  

    # P10 permutation
    v1 = P10(binary)

    # left shift 1
    v2 = LS1(v1[:5]) + LS1(v1[5:])

    # P8 permutation
    k1 = P8(v2)

    # left shift 2
    v3 = LS2(v2[:5]) + LS2(v2[5:])

    # P8 permutation
    k2 = P8(v3)

    return k1, k2

# function for initial permutation
def IP(plaintext):
    ip = [1, 5, 2, 0, 3, 7, 4, 6]
    ans = ""
    for  i in ip:
        ans += plaintext[i]
    return ans

# function for inverse initial permutation
def IP_inv(plaintext):
    ip_inv = [3, 0, 2, 4, 6, 1, 7, 5]
    ans = ""
    for i in ip_inv:
        ans += plaintext[i]
    return ans

# function for expansion/permutation
def EP(bin_str):
    ep = [3, 0, 1, 2, 1, 2, 3, 0]
    ans = ""
    for i in ep:
        ans += bin_str[i]
    return ans

# function for S-box 0
def S0(bin_str):
    s0 = [
        [1, 0, 3, 2],
        [3, 2, 0, 1],
        [0, 2, 1, 3],
        [3, 1, 3, 2]
    ]
    row = int(bin_str[0] + bin_str[3], 2)
    col = int(bin_str[1] + bin_str[2], 2)
    return bin(s0[row][col])[2:].zfill(2)

# function for S-box 1
def S1(bin_str):
    s1 = [
        [0, 1, 2, 3],
        [2, 0, 1, 3],
        [1, 2, 3, 0],
        [2, 0, 1, 3]
    ]
    row = int(bin_str[0] + bin_str[3], 2)
    col = int(bin_str[1] + bin_str[2], 2)
    return bin(s1[row][col])[2:].zfill(2)

# function for P4 permutation
def P4(bin_str):
    p4 = [2, 3, 1, 0]
    ans = ""
    for i in p4:
        ans += bin_str[i]
    return ans

# function for XOR operation
def XOR(a, b):
    result = ""
    for i in range(len(a)):
        result += str(int(a[i]) ^ int(b[i]))
    return result

# function for encryption of a single number(8 bits)
def encrypt(key, plaintext):
    
    k1, k2 = key_generation(key)
    plaintext = bin(plaintext)[2:]
    plaintext = plaintext.zfill(8)  

    # IP permutation
    plaintext = IP(plaintext)
    right = plaintext[4:]
    left = plaintext[:4]

    # round 1
    ep = EP(right)
    xor = XOR(ep, k1)
    s0 = xor[:4]
    s1 = xor[4:]
    p4 = P4(S0(s0) + S1(s1))
    temp = XOR(left, p4)

    # swap
    left = right
    right = temp

    # round 2
    ep = EP(right)
    xor = XOR(ep, k2)
    s0 = xor[:4]
    s1 = xor[4:]
    p4 = P4(S0(s0) + S1(s1))
    left = XOR(left, p4)
    plaintext = left + right

    # IP inverse permutation
    plaintext = IP_inv(plaintext)

    return int(plaintext, 2)

# function for decryption of a single number(8 bits)
def decrypt(key, ciphertext):

    k1, k2 = key_generation(key)
    ciphertext = int(ciphertext)
    ciphertext = bin(ciphertext)[2:]
    ciphertext = ciphertext.zfill(8)  

    # IP permutation
    ciphertext = IP(ciphertext)
    right = ciphertext[4:]
    left = ciphertext[:4]

    # round 1
    ep = EP(right)
    xor = XOR(ep, k2)
    s0 = xor[:4]
    s1 = xor[4:]
    p4 = P4(S0(s0) + S1(s1))
    temp = XOR(left, p4)

    # swap
    left = right
    right = temp

    # round 2
    ep = EP(right)
    xor = XOR(ep, k1)
    s0 = xor[:4]
    s1 = xor[4:]
    p4 = P4(S0(s0) + S1(s1))
    left = XOR(left, p4)
    ciphertext = left + right

    # IP inverse permutation
    ciphertext = IP_inv(ciphertext)

    return int(ciphertext, 2)

# function to encrypt a message
def encryptmsg(key, plaintext):
    ciphertext = ""
    for i in range(len(plaintext)):
        ciphertext += str(encrypt(key, ord(plaintext[i])))  + " "
    return ciphertext

# function to decrypt a message
def decryptmsg(key, ciphertext):
    plaintext = ""
    ciphertext = ciphertext.split(" ")
    for i in range(len(ciphertext)):
        plaintext += chr(decrypt(key, int(ciphertext[i])))
    return plaintext
