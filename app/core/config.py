import os
import json
from typing import Optional
from pydantic_settings import BaseSettings
from loguru import logger

class Settings(BaseSettings):
    # Default values can be overridden by environment variables
    # or loaded from /data/options.json
    
    # Git Configuration
    git_repo_url: str = ""
    
    # MinIO Configuration
    minio_endpoint: str = ""
    minio_access_key: str = ""
    minio_secret_key: str = ""
    
    # Internal Paths
    data_path: str = "/data"
    vault_path: str = "/data/vault"
    
    class Config:
        env_prefix = "EXOCORTEX_"

def load_settings() -> Settings:
    """
    Loads settings from Home Assistant options.json if available,
    otherwise falls back to environment variables.
    """
    options_path = "/data/options.json"
    
    settings_dict = {}
    
    # Try loading from HA options
    if os.path.exists(options_path):
        try:
            with open(options_path, "r") as f:
                options = json.load(f)
                logger.info(f"Loading configuration from {options_path}")
                # Map HA options to Settings fields
                # HA options are usually lowercase keys
                settings_dict.update(options)
        except Exception as e:
            logger.error(f"Failed to load {options_path}: {e}")
    else:
        logger.warning(f"{options_path} not found. Using environment variables/defaults.")

    return Settings(**settings_dict)

settings = load_settings()
