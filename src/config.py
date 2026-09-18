"""
Configurações globais carregadas do .env
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Sempre carrega o .env da raiz do projeto (não depende do cwd do notebook)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_key: str

    def validate(self):
        if not self.supabase_url or not self.supabase_key:
            raise EnvironmentError(
                "⚠️ SUPABASE_URL e SUPABASE_KEY precisam estar definidos no .env"
            )


def _env(name: str) -> str:
    return (os.getenv(name, "") or "").strip().strip('"').strip("'")


settings = Settings(
    supabase_url=_env("SUPABASE_URL"),
    supabase_key=_env("SUPABASE_KEY"),
)

settings.validate()
