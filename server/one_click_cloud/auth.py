import random
import string
import time
import jwt

from base64 import b64decode, b64encode
from cryptography.fernet import Fernet
from typing import Dict, Tuple


# SECRET_ENCRYPT_KEY = Fernet.generate_key()
SECRET_ENCRYPT_KEY = b"UqKWLVlkY7AsvkrxoywvxA1ueBQ1sL172ggoHsg3b3o="
# 30 days
JWT_EXPIRE_TIME = 60 * 60 * 24 * 30
JWT_SECRET = "Zm8HqvUJKcG89xA1u"
JWT_ALGORITHM = "HS256"

def encryptSecret(secret: str) -> str:
    return Fernet(SECRET_ENCRYPT_KEY).encrypt(secret.encode("utf-8")).decode("utf-8")

def decryptSecret(encrypted_secret: str) -> str:
    try:
        return Fernet(SECRET_ENCRYPT_KEY).decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")
    except Exception as e:
        raise ValueError("Failed to decrypt key secret.")

def deEnSecret(key_secret: str) -> (str, str):
    '''
    return decrypted and encrypted secret
    @param: key_secret
    @return: decrypted_secret, encrypted_secret
    '''
    if len(key_secret) > 70:
        # already encrypted
        return (decryptSecret(key_secret), key_secret)
    else:
        return (key_secret, encryptSecret(key_secret))

def generateToken(key_id: str, key_secret: str) -> str:
    '''
    generate token
    @param: key_id, key_secret
    @return: token
    '''
    nowint = int(time.time())
    playload = {
        "key_id": key_id,
        "key_secret": encryptSecret(key_secret),
        "exp": nowint + JWT_EXPIRE_TIME,
        "ref": nowint + JWT_EXPIRE_TIME / 2,
    }
    return jwt.encode(playload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def varifyToken(token: str) -> Dict:
    '''
    varify token
    @param: token
    @return: key_id, key_secret and new token if necessary
    '''
    try:
        playload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {
            "expired": True,
        }

    refresh_tm = playload.get("ref")
    key_id = playload.get("key_id")
    key_secret = decryptSecret(playload.get("key_secret"))

    if time.time() > refresh_tm:
        return {
            "key_id": key_id,
            "key_secret": key_secret,
            "new_token": generateToken(key_id, key_secret),
        }
    else:
        return {
            "key_id": key_id,
            "key_secret": key_secret,
        }

def splitSecret(varified: Dict) -> Tuple:
    '''
    split and get key info
    @param: varified
    @return: key_id, key_secret
    '''
    return (varified.get("key_id"), varified.get("key_secret"))

def generatePwd(len: int = 8) -> str:
    '''
    generate password
    '''
    special_chars = "()`~!@#$%^&*-_+=|{}[]:;'<>,.?/"
    chars = string.ascii_letters + string.digits + special_chars
    return ''.join(random.choice(chars) for _ in range(len))

def isVisitor(key_id: str) -> bool:
    '''
    be visitor(as demo) or not
    @param: key_id
    @return: true if user is visitor
    '''
    return key_id == "LTAI5t7LSJCM1dCUszcqCHH4"

def unistrToBase64(unistr: str) -> str:
    '''
    unistr to base64
    @param: unistr
    @return: base64
    '''
    return b64encode(unistr.encode("utf-8")).decode("utf-8")

def base64ToUnistr(base64: str) -> str:
    '''
    base64 to unistr
    @param: base64
    @return: unistr
    '''
    return b64decode(base64).decode('utf-8')

if __name__ == "__main__":
    pass
