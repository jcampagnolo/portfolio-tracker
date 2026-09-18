"""
src/collectors/supabase_client.py
Cliente Supabase — conexão e queries reutilizáveis.
"""

import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from supabase import Client, create_client

# Configuração de caminhos do projeto
ROOT = Path.cwd().resolve()
if ROOT.name == "valuation":
    ROOT = ROOT.parent.parent
elif ROOT.name in ("src", "notebooks"):
    ROOT = ROOT.parent

load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

_client: Client | None = None


def get_client() -> Client:
    """Retorna instância singleton do cliente Supabase."""
    global _client
    if _client is None:
        # Tenta carregar do settings ou diretamente do ambiente
        try:
            from src.config import settings
            url = settings.supabase_url
            key = settings.supabase_key
        except Exception:
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise EnvironmentError(
                "Variáveis SUPABASE_URL e SUPABASE_KEY não encontradas. "
                "Verifique seu arquivo .env"
            )

        _client = create_client(url, key)

    return _client


# Alias para manter compatibilidade caso use get_supabase() em outros arquivos
get_supabase = get_client


def load_transactions() -> pd.DataFrame:
    """
    Carrega todas as transações do Supabase com JOINs em
    assets, asset_categories, currencies, wallets e brokers.

    Returns:
        DataFrame com colunas achatadas (flat).
    """
    db = get_client()

    response = (
        db.table("transactions")
        .select(
            "id, transaction_type, trade_date, quantity, unit_price, "
            "total_amount, total_amount_brl, exchange_rate_to_brl, "
            "currency_id, conversion_pair_id, "
            "wallets(name), brokers(name), "
            "assets!inner(id, ticker, name, "
            "asset_categories(name), currencies(code))"
        )
        .order("trade_date")
        .execute()
    )

    if not response.data:
        return pd.DataFrame()

    records = _flatten_transactions(response.data)
    df = pd.DataFrame(records)
    if not df.empty and "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def load_asset_registry() -> pd.DataFrame:
    """
    Carrega cadastro de ativos (assets + categoria + moeda).

    Returns:
        DataFrame com ticker, name, categoria, moeda.
    """
    db = get_client()

    response = (
        db.table("assets")
        .select("id, ticker, name, asset_categories(name), currencies(code)")
        .execute()
    )

    if not response.data:
        return pd.DataFrame()

    records = []
    for row in response.data:
        category = row.pop("asset_categories", {}) or {}
        currency = row.pop("currencies", {}) or {}
        row["categoria"] = category.get("name")
        row["moeda"] = currency.get("code")
        records.append(row)

    return pd.DataFrame(records)


def _flatten_transactions(data: list[dict]) -> list[dict]:
    """Achata os objetos aninhados de assets, categories, currencies, wallets e brokers."""
    records = []
    for row in data:
        asset = row.pop("assets", {}) or {}
        category = asset.pop("asset_categories", {}) or {}
        currency = asset.pop("currencies", {}) or {}
        wallet = row.pop("wallets", {}) or {}
        broker = row.pop("brokers", {}) or {}

        row["ticker"] = asset.get("ticker")
        row["asset_name"] = asset.get("name")
        row["categoria"] = category.get("name")
        row["moeda"] = currency.get("code")
        row["carteira"] = wallet.get("name") if isinstance(wallet, dict) else None
        row["corretora"] = broker.get("name") if isinstance(broker, dict) else None

        records.append(row)
    return records