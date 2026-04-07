"""
src/valuation/projetivo.py
Preço Projetivo baseado no crescimento histórico do lucro (dados CVM).

Fórmula:
    P_projetivo = (LPA_atual × (1 + g)^n × PL_justo) / (1 + d)^n

Onde:
    LPA_atual   = Lucro por Ação atual
    g           = CAGR do lucro líquido (calculado via balanços CVM)
    n           = anos de projeção (padrão: 5)
    PL_justo    = P/L justo de referência (padrão: 10)
    d           = taxa de desconto (Selic + prêmio de risco)

O CAGR é calculado automaticamente a partir dos lucros líquidos
extraídos dos balanços da CVM.
"""

import math

import pandas as pd

from src.collectors.cvm_fundamentals import extract_indicators


def calcular_cagr(valores: list[float]) -> float | None:
    """
    Calcula o CAGR (Compound Annual Growth Rate) de uma série de valores.

    Parâmetros:
        valores: lista ordenada cronologicamente (do mais antigo ao mais recente)

    Retorna:
        CAGR como decimal (ex: 0.12 = 12% a.a.) ou None se não calculável
    """
    # Remove zeros e negativos do início
    valores_validos = [v for v in valores if v and v > 0]

    if len(valores_validos) < 2:
        return None

    primeiro = valores_validos[0]
    ultimo = valores_validos[-1]
    n_anos = len(valores_validos) - 1

    if primeiro <= 0 or ultimo <= 0 or n_anos == 0:
        return None

    cagr = (ultimo / primeiro) ** (1 / n_anos) - 1
    return round(cagr, 4)


def preco_projetivo(
    lpa_atual: float,
    cagr_lucro: float,
    anos_projecao: int = 5,
    pl_justo: float = 10.0,
    taxa_desconto: float = 0.14,
) -> float | None:
    """
    Calcula o preço projetivo de uma ação.

    Parâmetros:
        lpa_atual: LPA atual (últimos 12 meses)
        cagr_lucro: CAGR do lucro líquido (ex: 0.12 = 12%)
        anos_projecao: anos para projetar (padrão: 5)
        pl_justo: P/L justo de referência (padrão: 10)
        taxa_desconto: taxa para trazer a valor presente (padrão: 14%)

    Retorna:
        Preço projetivo trazido a valor presente
    """
    if lpa_atual is None or lpa_atual <= 0:
        return None
    if cagr_lucro is None:
        return None

    # LPA projetado no futuro
    lpa_futuro = lpa_atual * ((1 + cagr_lucro) ** anos_projecao)

    # Preço futuro = LPA futuro × P/L justo
    preco_futuro = lpa_futuro * pl_justo

    # Traz a valor presente
    preco_presente = preco_futuro / ((1 + taxa_desconto) ** anos_projecao)

    return round(preco_presente, 2)


def avaliar_projetivo(
    ticker: str,
    preco_atual: float,
    lpa_atual: float,
    num_acoes: float,
    anos_projecao: int = 5,
    pl_justo: float = 10.0,
    taxa_desconto: float = 0.14,
    years_cvm: list[int] | None = None,
) -> dict:
    """
    Avaliação completa pelo método projetivo usando dados CVM.

    1. Busca lucros históricos na CVM
    2. Calcula CAGR do lucro
    3. Projeta LPA futuro
    4. Traz a valor presente

    Parâmetros:
        ticker: código da ação (ex: PETR4)
        preco_atual: cotação atual
        lpa_atual: LPA dos últimos 12 meses
        num_acoes: número de ações em circulação
        anos_projecao: anos a projetar
        pl_justo: P/L justo de referência
        taxa_desconto: taxa de desconto anual
        years_cvm: anos para buscar na CVM (padrão: últimos 5)

    Retorna:
        dict com CAGR, preço projetivo, margem e status
    """
    # Busca indicadores na CVM
    indicadores = extract_indicators(ticker, years_cvm)

    cagr = None
    lucros_historicos = {}

    if not indicadores.empty and "lucro_liquido" in indicadores.columns:
        lucros = indicadores.sort_values("ano")
        lucros_historicos = dict(zip(lucros["ano"].astype(int), lucros["lucro_liquido"]))
        valores_lucro = lucros["lucro_liquido"].dropna().tolist()
        cagr = calcular_cagr(valores_lucro)

    # Calcula preço projetivo
    proj = None
    if cagr is not None:
        proj = preco_projetivo(
            lpa_atual=lpa_atual,
            cagr_lucro=cagr,
            anos_projecao=anos_projecao,
            pl_justo=pl_justo,
            taxa_desconto=taxa_desconto,
        )

    if proj is None:
        return {
            "ticker": ticker,
            "preco_atual": preco_atual,
            "lpa_atual": lpa_atual,
            "cagr_lucro_pct": round(cagr * 100, 2) if cagr else None,
            "lucros_historicos": lucros_historicos,
            "preco_projetivo": None,
            "margem_seguranca_pct": None,
            "status": "⚠️ Dados insuficientes para projeção (lucro negativo ou sem histórico CVM)",
        }

    margem = ((proj - preco_atual) / preco_atual) * 100

    if preco_atual <= proj * 0.7:
        status = "🟢 Muito barato — grande margem"
    elif preco_atual <= proj:
        status = "🟢 Abaixo do projetivo"
    elif margem >= -15:
        status = "🟡 Próximo — acompanhar"
    else:
        status = "🔴 Acima do projetivo — caro"

    return {
        "ticker": ticker,
        "preco_atual": preco_atual,
        "lpa_atual": round(lpa_atual, 4),
        "cagr_lucro_pct": round(cagr * 100, 2),
        "anos_projecao": anos_projecao,
        "pl_justo": pl_justo,
        "taxa_desconto_pct": taxa_desconto * 100,
        "lucros_historicos": lucros_historicos,
        "preco_projetivo": proj,
        "margem_seguranca_pct": round(margem, 2),
        "status": status,
    }


def projetivo_batch(
    ativos: list[dict],
    anos_projecao: int = 5,
    pl_justo: float = 10.0,
    taxa_desconto: float = 0.14,
) -> pd.DataFrame:
    """
    Calcula preço projetivo para uma lista de ações brasileiras.

    Parâmetros:
        ativos: lista de dicts com keys:
                ticker, preco_atual, lpa_atual, num_acoes
        anos_projecao: anos a projetar (padrão: 5)
        pl_justo: P/L justo (padrão: 10)
        taxa_desconto: taxa de desconto (padrão: 14%)

    Retorna:
        DataFrame com avaliação completa.
    """
    results = []

    for a in ativos:
        print(f"\n{'='*50}")
        print(f"📊 Analisando {a['ticker']}...")
        print(f"{'='*50}")

        r = avaliar_projetivo(
            ticker=a["ticker"],
            preco_atual=a["preco_atual"],
            lpa_atual=a.get("lpa_atual", 0),
            num_acoes=a.get("num_acoes", 0),
            anos_projecao=anos_projecao,
            pl_justo=pl_justo,
            taxa_desconto=taxa_desconto,
        )
        results.append(r)

    df = pd.DataFrame(results)

    if not df.empty and "margem_seguranca_pct" in df.columns:
        df = df.sort_values("margem_seguranca_pct", ascending=False, na_position="last")

    return df
