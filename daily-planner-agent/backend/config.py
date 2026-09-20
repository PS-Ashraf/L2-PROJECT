import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    MAX_ITERATIONS: int = 15

    class Config:
        env_file = ".env"

settings = Settings()
