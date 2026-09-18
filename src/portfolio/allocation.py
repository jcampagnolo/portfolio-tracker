"""
src/portfolio/allocation.py
Cálculo de alocação — peso por categoria e moeda.
"""

import pandas as pd


def allocation_by_category(abertas: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula alocação percentual por categoria.

    Returns:
        DataFrame com: categoria, custo_total_brl, peso_pct
    """
    total = abertas["custo_total_brl"].sum()
    alocacao = (
        abertas.groupby("categoria")["custo_total_brl"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    alocacao["peso_pct"] = (
        (alocacao["custo_total_brl"] / total * 100) if total > 0 else 0
    )
    return alocacao


def allocation_by_currency(abertas: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula alocação percentual por moeda.

    Returns:
        DataFrame com: moeda, custo_total_brl, peso_pct
    """
    total = abertas["custo_total_brl"].sum()
    alocacao = (
        abertas.groupby("moeda")["custo_total_brl"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    alocacao["peso_pct"] = (
        (alocacao["custo_total_brl"] / total * 100) if total > 0 else 0
    )
    return alocacao


def top_positions(abertas: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Retorna as N maiores posições por custo em BRL."""
    return abertas.nlargest(n, "custo_total_brl").reset_index(drop=True)
