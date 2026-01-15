import base64
import hashlib
from cryptography.fernet import Fernet
from app.infra.config.settings import settings

class EncryptionService:
    def __init__(self, secret_key: str):
        # Generate a 32-byte key from the secret_key using SHA-256
        key_hash = hashlib.sha256(secret_key.encode()).digest()
        # Fernet requires base64 encoded 32-byte key
        self.fernet = Fernet(base64.urlsafe_b64encode(key_hash))

    def encrypt(self, text: str) -> str:
        if not text:
            return ""
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text:
            return ""
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except Exception:
            # If decryption fails (e.g. wrong key or not encrypted), return as is or handle appropriately
            return encrypted_text

# Singleton instance using ADMIN_SECRET_KEY
encryption_service = EncryptionService(settings.ADMIN_SECRET_KEY.get_secret_value())