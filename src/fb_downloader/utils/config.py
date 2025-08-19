"""
Configuration management utilities
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from ..core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ConfigManager:
    """Configuration manager with environment variable support"""

    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from file and environment variables"""
        # Load from file
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    self._config = yaml.safe_load(f) or {}
                logger.debug(f"Loaded config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
                self._config = {}
        else:
            logger.debug(f"Config file not found: {self.config_path}")
            self._config = {}

        # Override with environment variables
        self._load_env_overrides()

        # Validate configuration
        self._validate_config()

    def _load_env_overrides(self) -> None:
        """Override config with environment variables"""
        env_mappings = {
            "FBDL_CHUNK_SIZE": ("download", "chunk_size", int),
            "FBDL_TIMEOUT": ("download", "timeout", int),
            "FBDL_MAX_RETRIES": ("download", "max_retries", int),
            "FBDL_USER_AGENT": ("headers", "user_agent", str),
            "FBDL_LOG_LEVEL": ("logging", "level", str),
            "FBDL_OUTPUT_DIR": ("output", "directory", str),
        }

        for env_var, (section, key, converter) in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                try:
                    converted_value = converter(value)
                    if section not in self._config:
                        self._config[section] = {}
                    self._config[section][key] = converted_value
                    logger.debug(f"Override {section}.{key} from {env_var}")
                except ValueError as e:
                    logger.warning(f"Invalid value for {env_var}: {e}")

    def _validate_config(self) -> None:
        """Validate configuration values"""
        # Ensure required sections exist
        required_sections = ["download", "headers", "logging", "output"]
        for section in required_sections:
            if section not in self._config:
                self._config[section] = {}

        # Set defaults
        defaults = {
            "download": {
                "chunk_size": 8192,
                "timeout": 30,
                "max_retries": 3,
            },
            "headers": {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "output": {
                "directory": ".",
                "max_filename_length": 100,
            },
        }

        for section, section_defaults in defaults.items():
            for key, default_value in section_defaults.items():
                if key not in self._config[section]:
                    self._config[section][key] = default_value

        # Validate values
        if self._config["download"]["chunk_size"] < 1024:
            raise ValidationError("Chunk size must be at least 1024 bytes")

        if self._config["download"]["timeout"] < 1:
            raise ValidationError("Timeout must be at least 1 second")

        if self._config["download"]["max_retries"] < 0:
            raise ValidationError("Max retries cannot be negative")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key"""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self._config.get(section, {})

    @property
    def config(self) -> Dict[str, Any]:
        """Get full configuration"""
        return self._config
