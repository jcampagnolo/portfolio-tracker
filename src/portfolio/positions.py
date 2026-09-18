"""
src/portfolio/positions.py
Cálculo de posições — saldo acumulado e preço médio por ticker.
"""

import pandas as pd

TIPOS_ENTRADA = {"compra", "desdobramento", "bonificacao", "conversao_entrada"}
TIPOS_SAIDA = {"venda", "conversao_saida"}


def calculate_positions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula saldo e preço médio ponderado para cada ticker.

    Args:
        df: DataFrame de transações (output de load_transactions).

    Returns:
        DataFrame com uma linha por ticker: qtde_saldo, preco_medio, custo_total, etc.
    """
    posicoes: dict[str, dict] = {}

    for _, row in df.sort_values("trade_date").iterrows():
        ticker = row["ticker"]
        tipo = row["transaction_type"]
        qtde = abs(row["quantity"])
        preco = abs(row["unit_price"]) if row["unit_price"] else 0
        moeda = row["moeda"]
        categoria = row["categoria"]
        nome = row["asset_name"]
        cambio = row.get("exchange_rate_to_brl") or 0
        total_brl = row.get("total_amount_brl") or 0

        if ticker not in posicoes:
            posicoes[ticker] = _empty_position(ticker, nome, categoria, moeda, cambio)

        pos = posicoes[ticker]

        if tipo in TIPOS_ENTRADA:
            _apply_entry(pos, qtde, preco, moeda, total_brl, cambio)
        elif tipo in TIPOS_SAIDA:
            _apply_exit(pos, qtde)

    return pd.DataFrame(posicoes.values())


def get_open_positions(df_positions: pd.DataFrame) -> pd.DataFrame:
    """Filtra posições com saldo > 0 (em carteira hoje)."""
    abertas = df_positions[df_positions["qtde_saldo"] > 0].copy()
    abertas.sort_values("categoria", inplace=True)
    abertas.reset_index(drop=True, inplace=True)
    return abertas


def get_closed_positions(df_positions: pd.DataFrame) -> pd.DataFrame:
    """Filtra posições com saldo = 0 (já encerradas)."""
    return df_positions[df_positions["qtde_saldo"] == 0].copy()


# ── Helpers privados ──────────────────────────────────────────


def _empty_position(
    ticker: str, nome: str, categoria: str, moeda: str, cambio: float
) -> dict:
    return {
        "ticker": ticker,
        "nome": nome,
        "categoria": categoria,
        "moeda": moeda,
        "qtde_saldo": 0.0,
        "custo_total": 0.0,
        "preco_medio": 0.0,
        "custo_total_brl": 0.0,
        "preco_medio_brl": 0.0,
        "ultimo_cambio": cambio,
    }


def _apply_entry(
    pos: dict, qtde: float, preco: float, moeda: str, total_brl: float, cambio: float
) -> None:
    custo_operacao = qtde * preco
    pos["custo_total"] += custo_operacao
    pos["qtde_saldo"] += qtde

    if moeda == "USD" and total_brl > 0:
        pos["custo_total_brl"] += abs(total_brl)
    elif moeda == "BRL":
        pos["custo_total_brl"] += custo_operacao

    if pos["qtde_saldo"] > 0:
        pos["preco_medio"] = pos["custo_total"] / pos["qtde_saldo"]
        pos["preco_medio_brl"] = pos["custo_total_brl"] / pos["qtde_saldo"]

    if cambio > 0:
        pos["ultimo_cambio"] = cambio


def _apply_exit(pos: dict, qtde: float) -> None:
    if pos["qtde_saldo"] > 0:
        pos["custo_total"] -= pos["preco_medio"] * qtde
        pos["custo_total_brl"] -= pos["preco_medio_brl"] * qtde

    pos["qtde_saldo"] -= qtde

    if pos["qtde_saldo"] <= 0:
        pos["qtde_saldo"] = 0
        pos["custo_total"] = 0
        pos["custo_total_brl"] = 0
        pos["preco_medio"] = 0
        pos["preco_medio_brl"] = 0
