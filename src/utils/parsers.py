# src/utils/parsers.py

"""
Conversão de formato BR fica centralizada aqui.
"""

import pandas as pd
from datetime import datetime


def parse_brl_number(value) -> float:
    """
    Converte número em formato BR para float.

    'R$ 1.234,56' → 1234.56
    '1.234,56'    → 1234.56
    '1234'        → 1234.0
    None/NaN      → 0.0
    """
    if pd.isna(value) or value is None:
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    cleaned = (
        str(value)
        .replace(" ", "")
        .replace("R", "")
        .replace("$", "")
        .replace("US", "")
    )

    # Formato BR: 1.234,56 → remove pontos de milhar, vírgula vira ponto
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")

    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def parse_brl_date(value, fmt: str = "%d/%m/%Y") -> pd.Timestamp | None:
    """Converte data em formato BR para Timestamp."""
    if pd.isna(value) or value is None:
        return None
    try:
        return pd.Timestamp(datetime.strptime(str(value).strip(), fmt))
    except ValueError:
        return None


def clean_transactions_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa e padroniza o DataFrame de transações.

    Substitui TODAS aquelas ~40 linhas de conversão do notebook
    por uma única chamada.

    Espera colunas: data, ticker, operacao, qtde, moeda,
                    valor_unitario, corretagem, outros_custos,
                    premio_opcoes, corretora
    """
    result = df.copy()

    # Padronizar nomes de colunas
    col_map = {
        "Data": "data",
        "Ação/FII": "ticker",
        "Compra/Venda": "operacao",
        "Qtde": "qtde",
        "Moeda": "moeda",
        "Valor": "vl_unit",
        "Corretagem": "vl_corretagem",
        "Outros Custos": "vl_outros_custos",
        "Prêmio Opções": "vl_premio",
        "Corretora": "corretora",
    }

    # Renomeia apenas colunas que existem
    result.rename(
        columns={k: v for k, v in col_map.items() if k in result.columns},
        inplace=True,
    )

    # Conversões de tipo — UMA LINHA CADA em vez de ~8 linhas cada
    result["data"] = result["data"].apply(parse_brl_date)
    result["qtde"] = result["qtde"].apply(parse_brl_number)
    result["vl_unit"] = result["vl_unit"].apply(parse_brl_number)
    result["vl_corretagem"] = result["vl_corretagem"].apply(parse_brl_number)
    result["vl_outros_custos"] = result["vl_outros_custos"].apply(parse_brl_number)
    result["vl_premio"] = result["vl_premio"].apply(parse_brl_number)

    # Campos calculados (idênticos ao seu notebook)
    result["qtde_real"] = result.apply(
        lambda row: (
            row["qtde"] if row["operacao"] in ["Compra", "Desdobramento"] else -row["qtde"]
        ),
        axis=1,
    )

    result["custo_total"] = (
        result["qtde_real"] * result["vl_unit"]
        + result["vl_corretagem"]
        + result["vl_outros_custos"]
        - result["vl_premio"]
    )

    result["custo_unit"] = result.apply(
        lambda row: row["custo_total"] / row["qtde"] if row["qtde"] != 0 else 0,
        axis=1,
    )

    return result
