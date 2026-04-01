# src/portfolio/positions.py

"""
Refatoração da lógica de saldos e preço médio do notebook.
Mantém a MESMA lógica, mas organizada e testável.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


def calculate_positions(transactions: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula saldos, preço médio, posições abertas e fechadas.

    Refatoração DIRETA do seu código de saldos no notebook.
    A lógica é idêntica, apenas organizada.

    Args:
        transactions: DataFrame com colunas:
            ticker, data, operacao, qtde_real, custo_unit, tipo, local

    Returns:
        DataFrame com saldos, preço médio, e flags de posição
    """
    saldos = transactions[
        ["ticker", "data", "operacao", "qtde_real", "custo_unit"]
    ].copy()

    # Ordenar para cálculo correto do saldo
    saldos.sort_values(by=["ticker", "data", "operacao"], inplace=True)

    # Saldo acumulado por ticker
    saldos["qtde_saldo"] = saldos.groupby("ticker")["qtde_real"].cumsum()

    # Índice de "ciclos" de operação (abre posição → fecha → abre nova)
    saldos["indice_op"] = (
        (saldos["ticker"] != saldos["ticker"].shift(1))
        | (saldos["qtde_saldo"].shift(1).fillna(0) == 0)
    ).astype(int).cumsum()

    # Custo acumulado (só compras entram no custo)
    saldos["custo_compra"] = saldos.apply(
        lambda row: (
            row["qtde_real"] * row["custo_unit"]
            if row["operacao"] in ["Compra", "Grupamento", "Desdobramento"]
            else 0
        ),
        axis=1,
    )
    saldos["vl_saldo"] = saldos.groupby(["ticker", "indice_op"])[
        "custo_compra"
    ].cumsum()

    # Preço médio
    saldos["preco_medio"] = saldos.apply(
        lambda row: (
            row["vl_saldo"] / row["qtde_saldo"]
            if row["qtde_saldo"] != 0
            else 0
        ),
        axis=1,
    )

    # Flags de posição
    saldos["posicao_aberta"] = (
        (saldos["ticker"] != saldos["ticker"].shift(-1))
        & (saldos["qtde_saldo"].fillna(0) != 0)
    ).astype(int)

    saldos["posicao_encerrada"] = (
        saldos["qtde_saldo"].fillna(0) == 0
    ).astype(int)

    return saldos


def get_open_positions(saldos: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna apenas posições em aberto (o que você tem em carteira hoje).

    Equivalente ao seu:
        saldos_pos_abertas = saldos[saldos['posicao_aberta'] == 1][...]
    """
    abertas = saldos[saldos["posicao_aberta"] == 1].copy()

    result = abertas[
        ["ticker", "tipo", "qtde_saldo", "vl_saldo", "preco_medio"]
    ].reset_index(drop=True)

    # Ticker no formato Yahoo Finance
    result["ticker_yf"] = result.apply(
        lambda row: (
            f"{row['ticker']}.SA"
            if row.get("local", "BR") == "BR"
            else row["ticker"]
        ),
        axis=1,
    )

    logger.info(f"{len(result)} posições abertas encontradas.")
    return result


def get_closed_positions(saldos: pd.DataFrame) -> pd.DataFrame:
    """Retorna posições encerradas (para cálculo de lucro/prejuízo realizado)."""
    return saldos[saldos["posicao_encerrada"] == 1].copy().reset_index(drop=True)
