"""
Infisical Client for Secrets Management

Securely manages environment variables and secrets using Infisical API.
Supports both direct environment variable loading and secure runtime access.

Features:
- Secure secret retrieval from Infisical
- Automatic environment variable population
- Fallback to .env file if API unavailable
- Secret caching to reduce API calls
"""

import os
import sys
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SecretType(Enum):
    \"\"\"Types of secrets managed by the system.\"\"\"
    API_KEY = \"api_key\"
    TOKEN = \"token\"
    CREDENTIAL = \"credential\"
    CONFIGURATION = \"configuration\"


@dataclass
class Secret:
    \"\"\"Represents a secret with metadata.\"\"\"
    key: str
    value: str
    secret_type: SecretType
    description: str = \"\"\n\n

class InfisicalClient:
    \"\"\"
    Client for managing secrets through Infisical API.
    
    Strategy:
    1. Try to load from environment (highest priority)
    2. Load from Infisical API if available
    3. Fallback to .env file if API unavailable
    
    Usage:
        client = InfisicalClient()
        api_key = client.get_secret(\"LM_STUDIO_API_KEY\")
    \"\"\"
    
    def __init__(self, env: str = \"development\", project_id: Optional[str] = None):
        \"\"\"Initialize the Infisical client.\"\"\"
        self.env = os.getenv(\"INFISICAL_ENVIRONMENT\", env)
        self.project_id = os.getenv(\"INFISICAL_PROJECT_ID\", project_id)
        self.api_key = os.getenv(\"INFISICAL_API_KEY\")
        
        # Cache for secrets to reduce API calls
        self._secret_cache: Dict[str, str] = {}
        self._cache_ttl = 300  # 5 minutes\n
        
    def _load_from_environment(self, key: str) -> Optional[str]:
        \"\"\"Load secret from environment variables (highest priority).\"\"\"
        value = os.getenv(key)
        if value:
            return value
        return None
    
    def _load_from_dotenv(self, key: str) -> Optional[str]:
        \"\"\"Load secret from .env file.\"\"\"
        dotenv_path = os.path.join(os.getcwd(), \".env\")
        if os.path.exists(dotenv_path):
            try:
                with open(dotenv_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            k = k.strip()
                            v = v.strip().strip('\"').strip(\"'\")
                            if k == key:
                                return v
            except Exception as e:
                print(f\"Warning: Failed to read .env file: {e}\", file=sys.stderr)
        return None
    
    def _load_from_infisical(self, key: str) -> Optional[str]:
        \"\"\"Load secret from Infisical API.\"\"\"
        if not self.api_key or not self.project_id:
            print(\"Warning: INFISICAL_API_KEY or INFISICAL_PROJECT_ID not set\", file=sys.stderr)
            return None\n        
        try:
            # TODO: Implement actual Infisical API call
            # This would use requests to call the Infisical REST API
            # Example: GET /api/v1/secrets/:project_id?secretKey=:key
            print(f\"Info: Fetching secret '{key}' from Infisical (API call not yet implemented)\", file=sys.stderr)
            
            # For now, return None - actual implementation would make API request
            return None\n        except Exception as e:
            print(f\"Warning: Failed to fetch secret '{key}' from Infisical: {e}\", file=sys.stderr)
            return None
    
    def get_secret(self, key: str, required: bool = True) -> Optional[str]:
        \"\"\"\nGet a secret value by key.\n\n        Args:
            key: The secret key name
            required: If True, raise error if secret not found\n            \n        Returns:
            The secret value or None if not found and not required\n            \n        Raises:\n            ValueError: If secret is required but not found\n        \"\"\"\n        # Check cache first
        if key in self._secret_cache:
            return self._secret_cache[key]\n        \n        # 1. Try environment (highest priority)
        value = self._load_from_environment(key)\n        if value:
            self._secret_cache[key] = value\n            return value\n        \n        # 2. Try .env file\n        value = self._load_from_dotenv(key)\n        if value:\n            self._secret_cache[key] = value\n            return value\n        \n        # 3. Try Infisical API\n        if self.api_key and self.project_id:\n            value = self._load_from_infisical(key)\n            if value:\n                self._secret_cache[key] = value\n                return value\n        \n        # Not found\n        if required:\n            raise ValueError(\n                f\"Required secret '{key}' not found. \"\n                f\"Set it as environment variable or in .env file.\"\n            )\n        return None\n    \n    def get_optional_secret(self, key: str) -> Optional[str]:\n        \"\"\"Get an optional secret (returns None if not found).\"\"\"\n        return self.get_secret(key, required=False)\n    \n    def require_secret(self, key: str) -> str:\n        \"\"\"Get a required secret or raise error.\"\"\"\n        value = self.get_secret(key, required=True)\n        if value is None:\n            raise ValueError(f\"Required secret '{key}' not found\")\n        return value\n    \n    def get_all_secrets(self) -> Dict[str, str]:\n        \"\"\"Get all secrets from environment and .env file.\"\"\"\n        # This would fetch all secrets from Infisical in production\n        # For now, return what's available locally\n        secrets = {}\n        \n        # Add environment variables starting with specific prefixes\n        prefixes = [\"LM_STUDIO\", \"OPENROUTER\", \"QDRANT\", \"INFISICAL\", \"GIT\"]\n        for key, value in os.environ.items():\n            if any(key.startswith(prefix) for prefix in prefixes):\n                secrets[key] = value\n        \n        # Add .env file values (overrides environment)\n        dotenv_secrets = {}\n        dotenv_path = os.path.join(os.getcwd(), \".env\")\n        if os.path.exists(dotenv_path):\n            try:\n                with open(dotenv_path, 'r') as f:\n                    for line in f:\n                        line = line.strip()\n                        if line and not line.startswith('#') and '=' in line:\n                            k, v = line.split('=', 1)\n                            dotenv_secrets[k.strip()] = v.strip().strip('\"').strip(\"'\")\n            except Exception:\n                pass\n        \n        secrets.update(dotenv_secrets)\n        return secrets\n    \n    def refresh_cache(self) -> None:\n        \"\"\"Clear the secret cache.\"\"\"\n        self._secret_cache.clear()\n\n\n# Global client instance\n_infisical_client: Optional[InfisicalClient] = None\n\n\ndef get_infisical_client(env: str = \"development\", project_id: Optional[str] = None) -> InfisicalClient:\n    \"\"\"Get or create the global Infisical client.\"\"\"\n    global _infisical_client\n    if _infisical_client is None:\n        _infisical_client = InfisicalClient(env, project_id)\n    return _infisical_client\n\n\ndef load_env_from_infisical(client: Optional[InfisicalClient] = None) -> Dict[str, str]:\n    \"\"\"\n    Load environment variables from Infisical and set them.\n    \n    Args:\n        client: Optional InfisicalClient instance\n        \n    Returns:\n        Dictionary of loaded secrets\n    \"\"\"\n    if client is None:\n        client = get_infisical_client()\n    \n    # Get all secrets and set as environment variables\n    secrets = client.get_all_secrets()\n    os.environ.update(secrets)\n    return secrets\n\n\n# Convenience functions for common secrets\ndef get_lm_studio_api_key(client: Optional[InfisicalClient] = None) -> str:\n    \"\"\"Get LM Studio API key.\"\"\"\n    if client is None:\n        client = get_infisical_client()\n    return client.require_secret(\"LM_STUDIO_API_KEY\")\n\n\ndef get_openrouter_api_key(client: Optional[InfisicalClient] = None) -> str:\n    \"\"\"Get OpenRouter API key.\"\"\"\n    if client is None:\n        client = get_infisical_client()\n    return client.require_secret(\"OPENROUTER_API_KEY\")\n\n\ndef get_qdrant_api_key(client: Optional[InfisicalClient] = None) -> str:\n    \"\"\"Get Qdrant API key (if authentication is enabled).\"\"\"\n    if client is None:\n        client = get_infisical_client()\n    # Qdrant auth is optional, so this is not required\n    return client.get_optional_secret(\"QDRANT_API_KEY\") or \"\"\n", "content": "\"\"\"\nInfisical Client for Secrets Management\n\nSecurely manages environment variables and secrets using Infisical API.\nSupports both direct environment variable loading and secure runtime access.\n\nFeatures:\n- Secure secret retrieval from Infisical\n- Automatic environment variable population\n- Fallback to .env file if API unavailable\n- Secret caching to reduce API calls\n\"\"\"\n\nimport os\nimport sys\nfrom typing import Optional, Dict, Any\nfrom dataclasses import dataclass\nfrom enum import Enum\n\n\nclass SecretType(Enum):\n    \"\"\"Types of secrets managed by the system.\"\"\"\n    API_KEY = \"api_key\"\n    TOKEN = \"token\"\n    CREDENTIAL = \"credential\"\n    CONFIGURATION = \"configuration\"\n\n\n@dataclass\nclass Secret:\n    \"\"\"Represents a secret with metadata.\"\"\"\n    key: str\n    value: str\n    secret_type: SecretType\n    description: str = \"\"\n\n\nclass InfisicalClient:\n    \"\"\"\n    Client for managing secrets through Infisical API.\n    \n    Strategy:\n    1. Try to load from environment (highest priority)\n    2. Load from Infisical API if available\n    3. Fallback to .env file if API unavailable\n    \n    Usage:\n        client = InfisicalClient()\n        api_key = client.get_secret(\"LM_STUDIO_API_KEY\")\n    \"\"\"\n    \n    def __init__(self, env: str = \"development\", project_id: Optional[str] = None):\n        \"\"\"Initialize the Infisical client.\"\"\"\n        self.env = os.getenv(\"INFISICAL_ENVIRONMENT\", env)\n        self.project_id = os.getenv(\"INFISICAL_PROJECT_ID\", project_id)\n        self.api_key = os.getenv(\"INFISICAL_API_KEY\")\n        \n        # Cache for secrets to reduce API calls\n        self._secret_cache: Dict[str, str] = {}\n        self._cache_ttl = 300  # 5 minutes\n        \n    def _load_from_environment(self, key: str) -> Optional[str]:\n        \"\"\"Load secret from environment variables (highest priority).\"\"\"\n        value = os.getenv(key)\n        if value:\n            return value\n        return None\n    \n    def _load_from_dotenv(self, key: str) -> Optional[str]:\n        \"\"\"Load secret from .env file.\"\"\"\n        dotenv_path = os.path.join(os.getcwd(), \".env\")\n        if os.path.exists(dotenv_path):\n            try:\n                with open(dotenv_path, 'r') as f:\n                    for line in f:\n                        line = line.strip()\n                        if line and not line.startswith('#') and '=' in line:\n                            k, v = line.split('=', 1)\n                            k = k.strip()\n                            v = v.strip().strip('\"').strip(\"'\")\n                            if k == key:\n                                return v\n            except Exception as e:\n                print(f\"Warning: Failed to read .env file: {e}\", file=sys.stderr)\n        return None\n    \n    def _load_from_infisical(self, key: str) -> Optional[str]:\n        \"\"\"Load secret from Infisical API.\"\"\"\n        if not self.api_key or not self.project_id:\n            print(\"Warning: INFISICAL_API_KEY or INFISICAL_PROJECT_ID not set\", file=sys.stderr)\n            return None\n        \n        try:\n            # TODO: Implement actual Infisical API call\n            # This would use requests to call the Infisical REST API\n            # Example: GET /api/v1/secrets/:project_id?secretKey=:key\n            print(f\"Info: Fetching secret '{key}' from Infisical (API call not yet implemented)\", file=sys.stderr)\n            \n            # For now, return None - actual implementation would make API request\n            return None\n        except Exception as e:\n            print(f\"Warning: Failed to fetch secret '{key}' from Infisical: {e}\", file=sys.stderr)\n            return None\n    \n    def get_secret(self, key: str, required: bool = True) -> Optional[str]:\n        \"\"\"\n        Get a secret value by key.\n        \n        Args:\n            key: The secret key name\n            required: If True, raise error if secret not found\n            \n        Returns:\n            The secret value or None if not found and not required\n            \n        Raises:\n            ValueError: If secret is required but not found\n        \"\"\"\n        # Check cache first\n        if key in self._secret_cache:\n            return self._secret_cache[key]\n        \n        # 1. Try environment (highest priority)\n        value = self._load_from_environment(key)\n        if value:\n            self._secret_cache[key] = value\n            return value\n        \n        # 2. Try .env file\n        value = self._load_from_dotenv(key)\n        if value:\n            self._secret_cache[key] = value\n            return value\n        \n        # 3. Try Infisical API\n        if self.api_key and self.project_id:\n            value = self._load_from_infisical(key)\n            if value:\n                self._secret_cache[key] = value\n                return value\n        \n        # Not found\n        if required:\n            raise ValueError(\n                f\"Required secret '{key}' not found. \"\n                f\"Set it as environment variable or in .env file.\"\n            )\n        return None\n    \n    def get_optional_secret(self, key: str) -> Optional[str]:\n        \"\"\"Get an optional secret (returns None if not found).\"\"\"\n        return self.get_secret(key, required=False)\n    \n    def require_secret(self, key: str) -> str:\n        \"\"\"Get a required secret or raise error.\"\"\"\n        value = self.get_secret(key, required=True)\n        if value is None:\n            raise ValueError(f\"Required secret '{key}' not found\")\n        return value\n    \n    def get_all_secrets(self) -> Dict[str, str]:\n        \"\"\"Get all secrets from environment and .env file.\"\"\"\n        # This would fetch all secrets from Infisical in production\n        # For now, return what's available locally\n        secrets = {}\n        \n        # Add environment variables starting with specific prefixes\n        prefixes = [\"LM_STUDIO\", \"OPENROUTER\", \"QDRANT\", \"INFISICAL\", \"GIT\"]\n        for key, value in os.environ.items():\n            if any(key.startswith(prefix) for prefix in prefixes):\n                secrets[key] = value\n        \n        # Add .env file values (overrides environment)\n        dotenv_secrets = {}\n        dotenv_path = os.path.join(os.getcwd(), \".env\")\n        if os.path.exists(dotenv_path):\n            try:\n                with open(dotenv_path, 'r') as f:\n                    for line in f:\n                        line = line.strip()\n                        if line and not line.startswith('#') and '=' in line:\n                            k, v = line.split('=', 1)\n                            dotenv_secrets[k.strip()] = v.strip().strip('\"').strip(\"'\")\n            except Exception:\n                pass\n        \n        secrets.update(dotenv_secrets)\n        return secrets\n    \n    def refresh_cache(self) -> None:\n        \"\"\"Clear the secret cache.\"\"\"\n        self._secret_cache.clear()\n\n\n# Global client instance\n_infisical_client: Optional[InfisicalClient] = None\n\n\ndef get_infisical_client(env: str = \"development\", project_id: Optional[str] = None) -> InfisicalClient:\n    \"\"\"Get or create the global Infisical client.\"\"\"\n    global _infisical_client\n    if _infisical_client is None:\n        _infisical_client = InfisicalClient(env, project_id)\n    return _infisical_client\n\n\ndef load_env_from_infisical(client: Optional[InfisicalClient] = None) -> Dict[str, str]:\n    \"\"\"\n    Load environment variables from Infisical and set them.\n    \n    Args:\n        client: Optional InfisicalClient instance\n        \n    Returns:\n        Dictionary of loaded secrets\n    \"\"\"\n    if client is None:\n        client = get_infisical_client()\n    \n    # Get all secrets and set as environment variables\n    secrets = client.get_all_secrets()\n    os.environ.update(secrets)\n    return secrets\n\n\n# Convenience functions for common secrets\ndef get_lm_studio_api_key(client: Optional[InfisicalClient] = None) -> str:\n    \"\"\"Get LM Studio API key.\"\"\"\n    if client is None:\n        client = get_infisical_client()\n    return client.require_secret(\"LM_STUDIO_API_KEY\")\n\n\ndef get_openrouter_api_key(client: Optional[InfisicalClient] = None) -> str:\n    \"\"\"Get OpenRouter API key.\"\"\"\n    if client is None:\n        client = get_infisical_client()\n    return client.require_secret(\"OPENROUTER_API_KEY\")\n\n\ndef get_qdrant_api_key(client: Optional[InfisicalClient] = None) -> str:\n    \"\"\"Get Qdrant API key (if authentication is enabled).\"\"\"\n    if client is None:\n        client = get_infisical_client()\n    # Qdrant auth is optional, so this is not required\n    return client.get_optional_secret(\"QDRANT_API_KEY\") or \"\"\n")]