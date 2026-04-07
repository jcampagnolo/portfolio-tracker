"""
src/collectors/supabase_client.py
Cliente Supabase — conexão e queries reutilizáveis.
"""

import pandas as pd
from supabase import create_client, Client
from src.config import settings
import os

_client: Client | None = None

def get_client() -> Client:
    """Retorna instância singleton do cliente Supabase."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def load_transactions() -> pd.DataFrame:
    """
    Carrega todas as transações do Supabase com JOINs em
    assets, asset_categories e currencies.

    Returns:
        DataFrame com colunas flat: ticker, asset_name, categoria, moeda, etc.
    """
    db = get_client()

    response = (
        db.table("transactions")
        .select(
            "id, transaction_type, trade_date, quantity, unit_price, "
            "total_amount, total_amount_brl, exchange_rate_to_brl, "
            "currency_id, conversion_pair_id, "
            "assets!inner(id, ticker, name, "
            "asset_categories(name), currencies(code))"
        )
        .order("trade_date")
        .execute()
    )

    if not response.data:
        raise ValueError("⚠️ Nenhuma transação encontrada no Supabase.")

    records = _flatten_transactions(response.data)
    df = pd.DataFrame(records)
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
    """Achata os objetos aninhados de assets/categories/currencies."""
    records = []
    for row in data:
        asset = row.pop("assets", {}) or {}
        category = asset.pop("asset_categories", {}) or {}
        currency = asset.pop("currencies", {}) or {}

        row["ticker"] = asset.get("ticker")
        row["asset_name"] = asset.get("name")
        row["categoria"] = category.get("name")
        row["moeda"] = currency.get("code")
        records.append(row)
    return records

def get_supabase() -> Client:
    """Retorna uma instância singleton do client Supabase."""
    global _client

    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise EnvironmentError(
                "Variáveis SUPABASE_URL e SUPABASE_KEY não encontradas. "
                "Verifique seu arquivo .env"
            )

        _client = create_client(url, key)

    return _client