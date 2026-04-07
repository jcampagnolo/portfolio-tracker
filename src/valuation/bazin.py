"""
src/valuation/bazin.py
Preço Teto de Bazin.

Fórmula:
    P_bazin = DPA / yield_minimo

Onde:
    DPA = Dividendo por Ação (últimos 12 meses)
    yield_minimo = 6% (padrão Bazin)

Critérios complementares de Bazin:
    - Não teve prejuízo nos últimos 5 anos
    - Paga dividendos consistentes
    - Dívida bruta / PL < 1
"""

import pandas as pd


def preco_teto_bazin(
    dpa_12m: float,
    yield_minimo: float = 0.06,
) -> float | None:
    """
    Calcula o preço teto de Bazin.

    Parâmetros:
        dpa_12m: dividendo por ação nos últimos 12 meses
        yield_minimo: yield mínimo aceitável (padrão: 6%)

    Retorna:
        Preço teto (float) ou None se DPA <= 0
    """
    if dpa_12m is None or dpa_12m <= 0:
        return None
    if yield_minimo <= 0:
        return None

    return round(dpa_12m / yield_minimo, 2)


def avaliar_bazin(
    ticker: str,
    preco_atual: float,
    dpa_12m: float,
    yield_minimo: float = 0.06,
) -> dict:
    """
    Avaliação completa pelo método Bazin.

    Retorna:
        dict com preço teto, margem de segurança e recomendação.
    """
    teto = preco_teto_bazin(dpa_12m, yield_minimo)

    if teto is None:
        return {
            "ticker": ticker,
            "preco_atual": preco_atual,
            "dpa_12m": dpa_12m,
            "yield_minimo_pct": yield_minimo * 100,
            "preco_teto_bazin": None,
            "margem_seguranca_pct": None,
            "status": "⚠️ Sem dividendos suficientes",
        }

    margem = ((teto - preco_atual) / preco_atual) * 100
    dy_atual = (dpa_12m / preco_atual) * 100 if preco_atual > 0 else 0

    if preco_atual <= teto:
        status = "🟢 Abaixo do teto — bom para compra"
    elif margem >= -10:
        status = "🟡 Próximo do teto — observar"
    else:
        status = "🔴 Acima do teto — caro"

    return {
        "ticker": ticker,
        "preco_atual": preco_atual,
        "dpa_12m": round(dpa_12m, 4),
        "dy_atual_pct": round(dy_atual, 2),
        "yield_minimo_pct": yield_minimo * 100,
        "preco_teto_bazin": teto,
        "margem_seguranca_pct": round(margem, 2),
        "status": status,
    }


def bazin_batch(
    ativos: list[dict],
    yield_minimo: float = 0.06,
) -> pd.DataFrame:
    """
    Calcula Bazin para uma lista de ativos.

    Parâmetros:
        ativos: lista de dicts com keys: ticker, preco_atual, dpa_12m
        yield_minimo: yield mínimo (padrão 6%)

    Retorna:
        DataFrame com avaliação completa de todos os ativos.
    """
    results = []
    for a in ativos:
        r = avaliar_bazin(
            ticker=a["ticker"],
            preco_atual=a["preco_atual"],
            dpa_12m=a.get("dpa_12m", 0),
            yield_minimo=yield_minimo,
        )
        results.append(r)

    df = pd.DataFrame(results)

    if not df.empty:
        df = df.sort_values("margem_seguranca_pct", ascending=False, na_position="last")

    return df
