"""
src/valuation/graham.py
Preço Justo de Benjamin Graham.

Fórmula clássica:
    P_graham = sqrt(22.5 × LPA × VPA)

Onde:
    LPA = Lucro por Ação (últimos 12 meses)
    VPA = Valor Patrimonial por Ação
    22.5 = 15 (P/L justo) × 1.5 (P/VP justo)

Fórmula com crescimento (Graham modificada):
    VI = (LPA × (8.5 + 2g) × 4.4) / taxa_selic

Onde:
    g = taxa de crescimento esperada do lucro (% a.a.)
    4.4 = yield dos títulos AAA da época (referência)
    taxa_selic = taxa Selic atual (substitui os 4.4 do original)
"""

import math

import pandas as pd


def preco_justo_graham(lpa: float, vpa: float) -> float | None:
    """
    Fórmula clássica de Graham.

    P = sqrt(22.5 × LPA × VPA)

    Retorna None se LPA ou VPA forem negativos (empresa com prejuízo
    ou patrimônio negativo não se aplica).
    """
    if lpa is None or vpa is None:
        return None
    if lpa <= 0 or vpa <= 0:
        return None

    return round(math.sqrt(22.5 * lpa * vpa), 2)


def preco_graham_modificado(
    lpa: float,
    taxa_crescimento: float,
    taxa_selic: float = 0.1375,
) -> float | None:
    """
    Fórmula modificada de Graham (adaptada para Brasil).

    VI = (LPA × (8.5 + 2g) × 4.4) / (taxa_selic × 100)

    Parâmetros:
        lpa: lucro por ação
        taxa_crescimento: crescimento esperado do lucro (ex: 0.10 = 10%)
        taxa_selic: taxa Selic anual (ex: 0.1375 = 13.75%)

    Retorna:
        Valor intrínseco ou None
    """
    if lpa is None or lpa <= 0:
        return None
    if taxa_selic <= 0:
        return None

    g = taxa_crescimento * 100  # converte 0.10 → 10
    selic_pct = taxa_selic * 100  # converte 0.1375 → 13.75

    vi = (lpa * (8.5 + 2 * g) * 4.4) / selic_pct

    return round(vi, 2) if vi > 0 else None


def avaliar_graham(
    ticker: str,
    preco_atual: float,
    lpa: float,
    vpa: float,
    taxa_crescimento: float | None = None,
    taxa_selic: float = 0.1375,
) -> dict:
    """
    Avaliação completa pelo método Graham.

    Retorna dict com preço justo clássico, modificado, margem e status.
    """
    classico = preco_justo_graham(lpa, vpa)
    modificado = None
    if taxa_crescimento is not None:
        modificado = preco_graham_modificado(lpa, taxa_crescimento, taxa_selic)

    # Usa o clássico como referência principal
    referencia = classico

    if referencia is None:
        return {
            "ticker": ticker,
            "preco_atual": preco_atual,
            "lpa": lpa,
            "vpa": vpa,
            "preco_graham_classico": None,
            "preco_graham_modificado": modificado,
            "margem_seguranca_pct": None,
            "status": "⚠️ LPA ou VPA negativo — Graham não se aplica",
        }

    margem = ((referencia - preco_atual) / preco_atual) * 100
    pl = preco_atual / lpa if lpa > 0 else None
    pvp = preco_atual / vpa if vpa > 0 else None

    if preco_atual <= referencia * 0.8:
        status = "🟢 Grande margem de segurança"
    elif preco_atual <= referencia:
        status = "🟢 Abaixo do preço justo"
    elif margem >= -15:
        status = "🟡 Próximo do justo — observar"
    else:
        status = "🔴 Acima do preço justo — caro"

    return {
        "ticker": ticker,
        "preco_atual": preco_atual,
        "lpa": round(lpa, 4),
        "vpa": round(vpa, 4),
        "p_l": round(pl, 2) if pl else None,
        "p_vp": round(pvp, 2) if pvp else None,
        "preco_graham_classico": classico,
        "preco_graham_modificado": modificado,
        "margem_seguranca_pct": round(margem, 2),
        "status": status,
    }


def graham_batch(
    ativos: list[dict],
    taxa_selic: float = 0.1375,
) -> pd.DataFrame:
    """
    Calcula Graham para uma lista de ativos.

    Parâmetros:
        ativos: lista de dicts com keys: ticker, preco_atual, lpa, vpa,
                taxa_crescimento (opcional)

    Retorna:
        DataFrame com avaliação completa.
    """
    results = []
    for a in ativos:
        r = avaliar_graham(
            ticker=a["ticker"],
            preco_atual=a["preco_atual"],
            lpa=a.get("lpa", 0),
            vpa=a.get("vpa", 0),
            taxa_crescimento=a.get("taxa_crescimento"),
            taxa_selic=taxa_selic,
        )
        results.append(r)

    df = pd.DataFrame(results)

    if not df.empty:
        df = df.sort_values("margem_seguranca_pct", ascending=False, na_position="last")

    return df
