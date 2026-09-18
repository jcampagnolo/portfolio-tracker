"""
src/portfolio/dividends.py
Cálculos e agregações de dividendos para o portfolio.
"""

import pandas as pd
from src.scripts.dividends_store import load_dividends


def monthly_summary(year: int | None = None) -> pd.DataFrame:
    """
    Resumo mensal de dividendos recebidos.

    Returns:
        DataFrame com colunas: year_month, total_received, count
    """
    df = load_dividends()
    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])
    df["year_month"] = df["date"].dt.to_period("M")

    if year:
        df = df[df["date"].dt.year == year]

    summary = df.groupby("year_month").agg(
        total_received=("total_received", "sum"),
        count=("id", "count"),
    ).reset_index()

    summary["year_month"] = summary["year_month"].astype(str)
    return summary


def annual_summary() -> pd.DataFrame:
    """Resumo anual de dividendos recebidos."""
    df = load_dividends()
    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    summary = df.groupby("year").agg(
        total_received=("total_received", "sum"),
        count=("id", "count"),
    ).reset_index()

    return summary


def by_ticker() -> pd.DataFrame:
    """Ranking de dividendos por ativo (do que mais pagou ao que menos pagou)."""
    df = load_dividends()
    if df.empty:
        return pd.DataFrame()

    summary = df.groupby("ticker").agg(
        total_received=("total_received", "sum"),
        count=("id", "count"),
        last_payment=("date", "max"),
    ).reset_index()

    return summary.sort_values("total_received", ascending=False)


def by_category() -> pd.DataFrame:
    """Dividendos agrupados por tipo de ativo."""
    df = load_dividends()
    if df.empty:
        return pd.DataFrame()

    summary = df.groupby("type").agg(
        total_received=("total_received", "sum"),
        count=("id", "count"),
    ).reset_index()

    # Traduz os tipos para leitura acessível
    type_labels = {
        "DIVIDENDO": "Ações - Dividendos",
        "JCP": "Ações - JCP",
        "RENDIMENTO_FII": "FIIs - Rendimentos",
        "DISTRIBUICAO_ETF": "ETFs - Distribuições",
    }
    summary["category_label"] = summary["type"].map(type_labels).fillna(summary["type"])

    return summary.sort_values("total_received", ascending=False)


def yield_on_cost(cost_map: dict[str, float]) -> pd.DataFrame:
    """
    Calcula Yield on Cost por ativo.

    Args:
        cost_map: dict {ticker: custo_total_de_aquisicao}

    Returns:
        DataFrame com ticker, total_dividends, cost, yoc_percent
    """
    dividends_by_ticker = by_ticker()
    if dividends_by_ticker.empty:
        return pd.DataFrame()

    records = []
    for _, row in dividends_by_ticker.iterrows():
        ticker = row["ticker"]
        total_div = row["total_received"] or 0
        cost = cost_map.get(ticker, 0)

        yoc = (total_div / cost * 100) if cost > 0 else 0

        records.append({
            "ticker": ticker,
            "total_dividends": total_div,
            "acquisition_cost": cost,
            "yoc_percent": round(yoc, 2),
        })

    return pd.DataFrame(records).sort_values("yoc_percent", ascending=False)


def monthly_evolution(months: int = 12) -> pd.DataFrame:
    """Evolução mensal dos últimos N meses (para ver crescimento da renda passiva)."""
    df = load_dividends()
    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])

    cutoff = pd.Timestamp.now() - pd.DateOffset(months=months)
    df = df[df["date"] >= cutoff]

    df["year_month"] = df["date"].dt.to_period("M")

    evolution = df.groupby("year_month").agg(
        total=("total_received", "sum"),
    ).reset_index()

    evolution["year_month"] = evolution["year_month"].astype(str)

    # Média móvel de 3 meses para suavizar
    evolution["moving_avg_3m"] = evolution["total"].rolling(3, min_periods=1).mean()

    return evolution
