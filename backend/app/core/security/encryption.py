"""Encryption utilities for sensitive data"""
from cryptography.fernet import Fernet
from app.config import settings
import json

# Initialize Fernet cipher
cipher = Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_credentials(credentials: dict) -> str:
    """Encrypt database credentials"""
    json_data = json.dumps(credentials)
    encrypted = cipher.encrypt(json_data.encode())
    return encrypted.decode()


def decrypt_credentials(encrypted_data: str) -> dict:
    """Decrypt database credentials"""
    decrypted = cipher.decrypt(encrypted_data.encode())
    return json.loads(decrypted.decode())
