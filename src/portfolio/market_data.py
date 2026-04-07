"""
src/portfolio/market_data.py
Valuation — combina posições com cotações atuais para calcular
valor de mercado, lucro/prejuízo e rentabilidade.
"""

import pandas as pd
from src.collectors.yahoo_prices import fetch_current_prices
from src.collectors.bcb_currency import fetch_dollar_rate


def enrich_with_market_data(abertas: pd.DataFrame) -> pd.DataFrame:
    """
    Enriquece as posições abertas com cotações de mercado.

    Adiciona colunas:
        - preco_atual: preço de mercado na moeda original
        - preco_atual_brl: preço de mercado convertido para BRL
        - valor_mercado_brl: qtde * preco_atual_brl
        - lucro_prejuizo_brl: valor_mercado_brl - custo_total_brl
        - rentabilidade_pct: (lucro / custo) * 100
        - variacao_dia_pct: variação % no dia
        - usdbrl: cotação PTAX do dólar (Banco Central)

    Args:
        abertas: DataFrame de posições abertas (output de get_open_positions).

    Returns:
        DataFrame enriquecido com dados de mercado.
    """
    if abertas.empty:
        return abertas.copy()

    df = abertas.copy()

    # 1. Buscar câmbio — agora via Banco Central (PTAX)
    usdbrl = fetch_dollar_rate()
    if usdbrl is None:
        print("⚠️  Fallback: usando dólar = 5.00 (BCB indisponível)")
        usdbrl = 5.00

    # 2. Buscar cotações
    cotacoes = fetch_current_prices(
        tickers=df["ticker"].tolist(),
        moedas=df["moeda"].tolist(),
    )

    # 3. Merge
    df = df.merge(
        cotacoes[["ticker", "preco_atual", "variacao_dia_pct", "data_cotacao"]],
        on="ticker",
        how="left",
    )

    # 4. Calcular valor de mercado em BRL
    df["usdbrl"] = usdbrl

    df["preco_atual_brl"] = df.apply(
        lambda r: r["preco_atual"] * usdbrl if r["moeda"] == "USD" else r["preco_atual"],
        axis=1,
    )

    df["valor_mercado_brl"] = df["qtde_saldo"] * df["preco_atual_brl"]

    # 5. Lucro / Prejuízo
    df["lucro_prejuizo_brl"] = df["valor_mercado_brl"] - df["custo_total_brl"]

    df["rentabilidade_pct"] = df.apply(
        lambda r: (
            (r["lucro_prejuizo_brl"] / r["custo_total_brl"]) * 100
            if r["custo_total_brl"] > 0
            else 0
        ),
        axis=1,
    )

    return df


def portfolio_totals(enriched: pd.DataFrame) -> dict:
    """
    Calcula totais consolidados da carteira.

    Returns:
        Dict com: total_investido, total_mercado, lucro_total,
                  rentabilidade_total, usdbrl.
    """
    total_investido = enriched["custo_total_brl"].sum()
    total_mercado = enriched["valor_mercado_brl"].sum()
    lucro_total = total_mercado - total_investido
    rent_total = (lucro_total / total_investido * 100) if total_investido > 0 else 0
    usdbrl = enriched["usdbrl"].iloc[0] if not enriched.empty else 0

    return {
        "total_investido_brl": total_investido,
        "total_mercado_brl": total_mercado,
        "lucro_total_brl": lucro_total,
        "rentabilidade_total_pct": rent_total,
        "usdbrl": usdbrl,
    }
