from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()