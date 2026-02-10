#!/usr/bin/env python3
"""Generate secure keys for production deployment"""
import secrets
from cryptography.fernet import Fernet

print("Generating secure keys for production...\n")

# Generate JWT secret key
jwt_secret = secrets.token_urlsafe(64)
print(f"SECRET_KEY={jwt_secret}")

# Generate Fernet encryption key
encryption_key = Fernet.generate_key().decode()
print(f"ENCRYPTION_KEY={encryption_key}")

print("\nAdd these to your .env file!")
print("⚠️  NEVER commit these keys to version control!")
