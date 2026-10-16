from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    azure_storage_account_url: str
    azure_storage_container_name: str
    azure_test_blob_name: str
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    #Azure credential
    azure_credential_mode: Literal[
        "default",
        "azure_cli",
        "managed_identity"
    ] = "default"  # default, azure_cli, environment, managed_identity, interactive_browser, device_code, visual_studio_code, visual_studio, azure_powershell   


settings = Settings()