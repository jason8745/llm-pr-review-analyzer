"""
Configuration management for the agent, using Pydantic models and YAML loading.
"""

import os
from functools import lru_cache

import yaml
from pydantic import BaseModel, SecretStr, StrictFloat, StrictInt, StrictStr
from pydantic_settings import BaseSettings


class GitHubConfig(BaseModel):
    token: SecretStr
    api_base_url: StrictStr = "https://api.github.com"


class LLMConfig(BaseModel):
    temperature: StrictFloat = 0.1
    max_tokens: StrictInt = 4000
    retry: StrictInt = 3


class AzureOpenAIConfig(BaseModel):
    endpoint: StrictStr
    api_version: StrictStr = "2024-02-15-preview"
    deployment: StrictStr
    api_key: SecretStr


class AppConfig(BaseModel):
    log_level: StrictStr = "INFO"
    max_comments_per_request: StrictInt = 100


class Config(BaseSettings):
    github: GitHubConfig
    llm: LLMConfig
    azure_openai: AzureOpenAIConfig
    app: AppConfig


@lru_cache()
def get_config() -> Config:
    config_path = os.getenv("CONFIG_PATH", "src/config/config.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

    return Config(**raw_config)
