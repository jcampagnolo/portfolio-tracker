# src/config.py

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_key: str              # service_role
    supabase_anon_key: str = ""    # anon (opcional por enquanto)

    # App
    app_name: str = "Portfolio Tracker"
    debug: bool = False
    log_level: str = "INFO"

    # Google Sheets (temporário — só migração)
    google_sheet_id: str = ""
    google_gid_conta_corrente: str = ""
    google_gid_cadastro: str = ""

    model_config = {
        "env_file": Path(__file__).resolve().parent.parent / ".env",
        "env_file_encoding": "utf-8",
    }


# Instância global
settings = Settings()