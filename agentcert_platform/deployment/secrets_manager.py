"""
Secrets Manager - Secure API key storage and management

This module handles secure storage and retrieval of customer API keys.
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Secure secrets manager for storing and retrieving API keys.
    
    Uses encryption at rest. In production, consider using:
    - AWS Secrets Manager
    - HashiCorp Vault
    - Google Secret Manager
    - Azure Key Vault
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize secrets manager.
        
        Args:
            encryption_key: Optional encryption key (if None, uses env var or generates)
        """
        # Get or generate encryption key
        if encryption_key:
            self.encryption_key = encryption_key.encode()
        else:
            # Try to get from environment
            key = os.getenv("SECRETS_ENCRYPTION_KEY")
            if key:
                self.encryption_key = key.encode()
            else:
                # Generate a key (WARNING: This is not persistent!)
                # In production, always use a persistent key from secure storage
                logger.warning("No encryption key found. Generating temporary key.")
                logger.warning("⚠️  WARNING: Generated keys are not persistent. Use SECRETS_ENCRYPTION_KEY env var.")
                self.encryption_key = Fernet.generate_key()
        
        # Ensure key is 32 bytes (Fernet requirement)
        if len(self.encryption_key) != 44:  # Fernet keys are base64-encoded, 44 chars
            # Derive key from password if needed
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'agentcert_secrets_salt',  # In production, use random salt per secret
                iterations=100000,
            )
            self.encryption_key = base64.urlsafe_b64encode(
                kdf.derive(self.encryption_key[:32] if len(self.encryption_key) >= 32 else self.encryption_key)
            )
        
        self.cipher = Fernet(self.encryption_key)
        
        # In-memory storage (in production, use encrypted database)
        self._secrets: Dict[str, bytes] = {}
    
    def store_secret(self, agent_id: str, secret_name: str, secret_value: str) -> bool:
        """
        Store an encrypted secret.
        
        Args:
            agent_id: Agent identifier
            secret_name: Name of secret (e.g., "OPENAI_API_KEY")
            secret_value: Secret value to encrypt
        
        Returns:
            True if successful
        """
        try:
            # Encrypt the secret
            encrypted = self.cipher.encrypt(secret_value.encode())
            
            # Store with composite key
            key = f"{agent_id}:{secret_name}"
            self._secrets[key] = encrypted
            
            logger.info(f"Stored secret {secret_name} for agent {agent_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to store secret: {e}")
            return False
    
    def retrieve_secret(self, agent_id: str, secret_name: str) -> Optional[str]:
        """
        Retrieve and decrypt a secret.
        
        Args:
            agent_id: Agent identifier
            secret_name: Name of secret
        
        Returns:
            Decrypted secret value or None if not found
        """
        try:
            key = f"{agent_id}:{secret_name}"
            encrypted = self._secrets.get(key)
            
            if not encrypted:
                return None
            
            # Decrypt
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        
        except Exception as e:
            logger.error(f"Failed to retrieve secret: {e}")
            return None
    
    def delete_secret(self, agent_id: str, secret_name: str) -> bool:
        """Delete a stored secret"""
        key = f"{agent_id}:{secret_name}"
        if key in self._secrets:
            del self._secrets[key]
            logger.info(f"Deleted secret {secret_name} for agent {agent_id}")
            return True
        return False
    
    def list_secrets(self, agent_id: str) -> list:
        """List all secret names for an agent"""
        prefix = f"{agent_id}:"
        return [
            key.split(":", 1)[1] 
            for key in self._secrets.keys() 
            if key.startswith(prefix)
        ]


# Global instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create global secrets manager instance"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager

