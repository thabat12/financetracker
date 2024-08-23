from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import hmac
import hashlib
import struct

load_dotenv()

class Settings(BaseSettings):
    db_secret_key: str
settings: Settings = Settings()

key_bytes: bytearray = bytearray('a', encoding='utf-8')

if len(key_bytes) > 32:
    key_bytes = key_bytes[:32]
else:
    cur_len = len(key_bytes)
    needed_len = 32 - cur_len
    
    for _ in range(needed_len):
        key_bytes.append(needed_len)

db_key_bytes: bytes = bytes(key_bytes)

def encrypt_data(plaintext: bytes, key: bytes):
    # Generate a random 16-byte IV (Initialization Vector)
    iv = os.urandom(16)
    
    # Create an AES cipher object with the given key and IV
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # Pad the plaintext to be a multiple of 16 bytes
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(plaintext) + padder.finalize()
    
    # Encrypt the padded data
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    return iv + ciphertext  # Return IV + ciphertext for decryption purposes

# ciphertext = encrypt_data(plaintext, key)
# print(ciphertext)

def decrypt_data(ciphertext, key):
    # Extract the IV from the beginning of the ciphertext
    iv = ciphertext[:16]
    actual_ciphertext = ciphertext[16:]
    
    # Create a cipher object with the key and IV
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    # Decrypt the ciphertext
    padded_plaintext = decryptor.update(actual_ciphertext) + decryptor.finalize()
    
    # Unpad the plaintext
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
    
    return plaintext

def encrypt_integer(integer: int, key: bytearray):
    b = struct.pack('!i', integer)
    return encrypt_data(b, key)

def decrypt_integer(encrypted_bytes: bytearray, key: bytearray):
    d = decrypt_data(encrypted_bytes, key)
    return struct.unpack('!i', d)[0]

def encrypt_float(float: float | None, key: bytearray):
    if float == None:
        return None
    
    b = struct.pack('!f', float)
    return encrypt_data(b, key)

def decrypt_float(encrypted_bytes: bytearray | None, key: bytearray):
    if encrypted_bytes == None:
        return None
    
    d = decrypt_data(encrypted_bytes, key)
    return round(struct.unpack('!f', d)[0], 2)