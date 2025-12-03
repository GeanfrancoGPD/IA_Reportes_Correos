# app/utils.py
import os
from itsdangerous import URLSafeSerializer
import hashlib

SECRET = os.getenv("APP_SECRET", "cambia_esta_clave_secreta")

def signer():
    return URLSafeSerializer(SECRET, salt="invoice-action")

def sign_payload(payload: dict) -> str:
    return signer().dumps(payload)

def unsign_payload(token: str) -> dict:
    return signer().loads(token)
