"""
Configurações globais carregadas do .env
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_key: str

    def validate(self):
        if not self.supabase_url or not self.supabase_key:
            raise EnvironmentError(
                "⚠️ SUPABASE_URL e SUPABASE_KEY precisam estar definidos no .env"
            )


settings = Settings(
    supabase_url=os.getenv("SUPABASE_URL", ""),
    supabase_key=os.getenv("SUPABASE_KEY", ""),
)

settings.validate()
