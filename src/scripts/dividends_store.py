"""
src/scripts/dividends_store.py
Armazena e consulta histórico de dividendos no Supabase (PostgreSQL).
"""

import pandas as pd
from src.collectors.supabase_client import get_supabase


def save_dividends(df: pd.DataFrame, shares_map: dict[str, float] | None = None):
    """
    Salva dividendos no Supabase via upsert (ignora duplicatas).

    Args:
        df: DataFrame vindo do fetcher
        shares_map: dict {ticker: quantidade_de_cotas}
    """
    if df.empty:
        return

    sb = get_supabase()
    records = []

    for _, row in df.iterrows():
        ticker = row["ticker"]
        gross = float(row["gross_per_share"])
        div_type = row["type"]

        # JCP tem 15% IR retido na fonte
        net = gross * 0.85 if div_type == "JCP" else gross

        shares = shares_map.get(ticker, 0) if shares_map else 0
        total = round(net * shares, 2) if shares else None

        records.append({
            "date": str(row["date"]),
            "ticker": ticker,
            "type": div_type,
            "gross_per_share": gross,
            "net_per_share": round(net, 6),
            "shares_held": shares if shares else None,
            "total_received": total,
            "currency": row["currency"],
        })

    # Upsert em lotes de 500 (limite seguro)
    BATCH_SIZE = 500
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        sb.table("dividends").upsert(
            batch,
            on_conflict="date,ticker,gross_per_share"
        ).execute()

    print(f"✅ {len(records)} dividendos salvos no Supabase.")


def load_dividends(
    ticker: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """
    Carrega dividendos do Supabase com filtros opcionais.

    Args:
        ticker: filtrar por ativo específico
        start: data inicial 'YYYY-MM-DD'
        end: data final 'YYYY-MM-DD'

    Returns:
        DataFrame com os dividendos
    """
    sb = get_supabase()
    query = sb.table("dividends").select("*")

    if ticker:
        query = query.eq("ticker", ticker.upper())
    if start:
        query = query.gte("date", start)
    if end:
        query = query.lte("date", end)

    query = query.order("date", desc=True)

    # Pagina automaticamente para buscar todos os registros
    all_data = []
    page_size = 1000
    offset = 0

    while True:
        response = query.range(offset, offset + page_size - 1).execute()
        rows = response.data

        if not rows:
            break

        all_data.extend(rows)

        if len(rows) < page_size:
            break

        offset += page_size

    if not all_data:
        return pd.DataFrame()

    return pd.DataFrame(all_data)


def delete_dividends(ticker: str | None = None, before: str | None = None):
    """
    Remove dividendos do Supabase (útil para reprocessar).

    Args:
        ticker: remover apenas de um ativo
        before: remover apenas antes de uma data
    """
    sb = get_supabase()
    query = sb.table("dividends").delete()

    if ticker:
        query = query.eq("ticker", ticker.upper())
    if before:
        query = query.lt("date", before)

    if not ticker and not before:
        raise ValueError(
            "Passe pelo menos ticker ou before para evitar deletar tudo. "
            "Se realmente quer limpar tudo, use o SQL Editor do Supabase."
        )

    response = query.execute()
    count = len(response.data) if response.data else 0
    print(f"🗑️  {count} registros removidos.")


def get_dividend_stats() -> dict:
    """Retorna estatísticas rápidas dos dividendos armazenados."""
    sb = get_supabase()

    # Total de registros
    response = sb.table("dividends").select("id", count="exact").execute()
    total_records = response.count or 0

    # Tickers únicos
    response = sb.table("dividends").select("ticker").execute()
    unique_tickers = list({r["ticker"] for r in response.data}) if response.data else []

    # Período coberto
    oldest = (
        sb.table("dividends")
        .select("date")
        .order("date", desc=False)
        .limit(1)
        .execute()
    )
    newest = (
        sb.table("dividends")
        .select("date")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )

    return {
        "total_records": total_records,
        "unique_tickers": unique_tickers,
        "ticker_count": len(unique_tickers),
        "oldest_date": oldest.data[0]["date"] if oldest.data else None,
        "newest_date": newest.data[0]["date"] if newest.data else None,
    }
