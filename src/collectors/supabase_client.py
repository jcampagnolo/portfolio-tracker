# src/collectors/supabase_client.py

"""
Substitui carrega_dados_csv_google_sheets() por acesso ao Supabase.
"""

from supabase import create_client, Client
from src.config import settings
import pandas as pd
import logging

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client:
    """Singleton do client Supabase."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("Conexão Supabase estabelecida.")
    return _client


def load_transactions() -> pd.DataFrame:
    """
    Carrega transações do Supabase.

    Equivalente ao seu:
        tmp_conta_corrente = carrega_dados_csv_google_sheets(sheet_id, sheet_gid)
    """
    db = get_client()

    response = (
        db.table("transactions")
        .select(
            "*, assets!inner(ticker, name, asset_type, sector)"
        )
        .order("operation_date")
        .execute()
    )

    if not response.data:
        logger.warning("Nenhuma transação encontrada no Supabase.")
        return pd.DataFrame()

    # Flatten a relação com assets
    records = []
    for row in response.data:
        asset = row.pop("assets", {})
        row["ticker"] = asset.get("ticker")
        row["tipo"] = asset.get("asset_type")
        row["setor"] = asset.get("sector")
        records.append(row)

    df = pd.DataFrame(records)
    df["operation_date"] = pd.to_datetime(df["operation_date"])

    logger.info(f"{len(df)} transações carregadas do Supabase.")
    return df


def load_asset_registry() -> pd.DataFrame:
    """
    Carrega cadastro de ativos.

    Equivalente ao seu:
        tmp_cadastro = carrega_dados_csv_google_sheets(sheet_id, sheet_gid_cadastro)
    """
    db = get_client()

    response = (
        db.table("assets")
        .select("*")
        .eq("is_active", True)
        .execute()
    )

    return pd.DataFrame(response.data) if response.data else pd.DataFrame()
