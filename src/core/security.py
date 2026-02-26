"""Credential encryption utilities."""

from __future__ import annotations

import json
from typing import Any, Dict

from cryptography.fernet import Fernet

from ..config import RECON_ENCRYPTION_KEY


class CredentialManager:
    """Encrypt and decrypt connection configs."""

    sensitive_fields = {
        "password",
        "connection_string",
        "api_key",
        "token",
        "secret",
    }

    def __init__(self) -> None:
        if not RECON_ENCRYPTION_KEY:
            raise RuntimeError(
                "RECON_ENCRYPTION_KEY is not set. "
                'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        self.cipher = Fernet(RECON_ENCRYPTION_KEY.encode())

    def encrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in configuration."""
        encrypted_config = dict(config)
        for field in list(encrypted_config.keys()):
            if (
                field in self.sensitive_fields
                and encrypted_config.get(field) is not None
            ):
                value = str(encrypted_config[field])
                encrypted_value = self.cipher.encrypt(value.encode()).decode()
                encrypted_config[f"{field}_encrypted"] = encrypted_value
                del encrypted_config[field]
        return encrypted_config

    def decrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in configuration."""
        decrypted_config: Dict[str, Any] = {}
        for key, value in config.items():
            if key.endswith("_encrypted"):
                original_key = key.replace("_encrypted", "")
                decrypted_value = self.cipher.decrypt(str(value).encode()).decode()
                decrypted_config[original_key] = decrypted_value
            else:
                decrypted_config[key] = value
        return decrypted_config

    def serialize(self, config: Dict[str, Any]) -> str:
        """Serialize encrypted config as JSON."""
        return json.dumps(self.encrypt_config(config))

    def deserialize(self, payload: str) -> Dict[str, Any]:
        """Deserialize and decrypt config from JSON."""
        return self.decrypt_config(json.loads(payload))
