from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    default_cli_prompt: str = "$"

@lru_cache()
def get_settings(**kwargs: dict) -> Settings:
    return Settings(**kwargs)