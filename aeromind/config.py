from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AEROMIND_", extra="ignore")

    database_url: str = "postgresql+asyncpg://aeromind:aeromind@localhost:5432/aeromind"
    sync_database_url: str = "postgresql+psycopg://aeromind:aeromind@localhost:5432/aeromind"

    gemini_api_key: str = ""
    gemini_model_agents: str = "gemini-2.5-flash"
    gemini_model_judge: str = "gemini-2.5-flash"

    blast_radius_cap: int = 15
    gate_value_usd: float = 500_000.0

    timeout_loadiq_sec: float = 45.0
    timeout_clearpath_sec: float = 60.0
    timeout_cargocomply_sec: float = 90.0


settings = Settings()
