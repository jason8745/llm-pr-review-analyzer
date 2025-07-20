"""Configuration package."""

from .config import Config, get_config


# Lazy loading to avoid initialization issues
def get_default_config():
    return get_config()


__all__ = ["Config", "get_config", "get_default_config"]
