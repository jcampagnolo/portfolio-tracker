# src/portfolio/daily.py

"""
Completa a seção 'Acompanhamento Diário' que estava cortada no notebook:
    acompanhamento_diario['variacao_hoje_vl'] = ???
"""

import pandas as pd
from src.collectors.yahoo_prices import fetch_current_prices, fetch_fundamentals, fetch_dollar_rate
from src.utils.formatters import format_brl, format_pct
import logging

logger = logging.getLogger(__name__)


def build_daily_report(open_positions: pd.DataFrame) -> pd.DataFrame:
    """
    Monta o acompanhamento diário completo.

    Completa o que faltava no seu notebook e adiciona campos extras.
    """
    tickers = open_positions["ticker_yf"].unique().tolist()

    # Buscar dados em paralelo
    cotacoes = fetch_current_prices(tickers)
    fundamentos = fetch_fundamentals(tickers)
    dolar = fetch_dollar_rate()

    # Merge cotações
    report = pd.merge(open_positions, cotacoes, how="left", on="ticker_yf")

    # Merge fundamentos
    report = pd.merge(report, fundamentos, how="left", on="ticker_yf")

    # =============================================
    # CAMPOS QUE ESTAVAM FALTANDO NO SEU NOTEBOOK
    # =============================================

    # Valor de mercado atual da posição
    report["vl_mercado"] = report["qtde_saldo"] * report["cotacao_atual"]

    # Variação do dia (em R$) — era o campo incompleto!
    report["variacao_hoje_vl"] = (
        report["cotacao_atual"] - report["cotacao_abertura"]
    ) * report["qtde_saldo"]

    # Variação do dia (em %)
    report["variacao_hoje_pct"] = (
        (report["cotacao_atual"] - report["cotacao_abertura"])
        / report["cotacao_abertura"]
        * 100
    ).round(2)

    # Lucro/Prejuízo total (em R$)
    report["lucro_prejuizo_vl"] = report["vl_mercado"] - report["vl_saldo"]

    # Rentabilidade total (em %)
    report["rentabilidade_pct"] = (
        (report["vl_mercado"] - report["vl_saldo"]) / report["vl_saldo"] * 100
    ).round(2)

    # Peso no portfólio (%)
    total_mercado = report["vl_mercado"].sum()
    report["peso_portfolio_pct"] = (
        (report["vl_mercado"] / total_mercado * 100).round(2)
        if total_mercado > 0
        else 0
    )

    # Distância do preço médio (%)
    report["dist_preco_medio_pct"] = (
        (report["cotacao_atual"] - report["preco_medio"])
        / report["preco_medio"]
        * 100
    ).round(2)

    # Posição relativa nas 52 semanas (0% = mínima, 100% = máxima)
    report["posicao_52s_pct"] = (
        (report["cotacao_atual"] - report["cotacao_52s_min"])
        / (report["cotacao_52s_max"] - report["cotacao_52s_min"])
        * 100
    ).round(1)

    # Cotação do dólar para ativos internacionais
    report["cotacao_dolar"] = dolar

    # Ordenar por peso no portfólio (maior primeiro)
    report.sort_values("peso_portfolio_pct", ascending=False, inplace=True)
    report.reset_index(drop=True, inplace=True)

    logger.info(f"Relatório diário gerado: {len(report)} posições.")
    return report


def daily_summary_accessible(report: pd.DataFrame) -> str:
    """
    Gera resumo textual acessível para leitores de tela.

    Ideal para Juliana acompanhar rapidamente.
    """
    total_investido = report["vl_saldo"].sum()
    total_mercado = report["vl_mercado"].sum()
    lucro_total = total_mercado - total_investido
    rent_total = (lucro_total / total_investido * 100) if total_investido > 0 else 0
    variacao_dia = report["variacao_hoje_vl"].sum()

    lines = [
        f"📊 RESUMO DO DIA",
        f"",
        f"Total investido: {format_brl(total_investido)}",
        f"Valor de mercado: {format_brl(total_mercado)}",
        f"Resultado total: {format_brl(lucro_total)} ({rent_total:+.1f}%)",
        f"Variação hoje: {format_brl(variacao_dia)}",
        f"",
        f"🏆 DESTAQUES:",
    ]

    # Top 3 maiores altas do dia
    altas = report.nlargest(3, "variacao_hoje_pct")
    for _, row in altas.iterrows():
        lines.append(
            f"  📈 {row['ticker']}: {row['variacao_hoje_pct']:+.2f}% "
            f"({format_brl(row['variacao_hoje_vl'])})"
        )

    # Top 3 maiores quedas do dia
    baixas = report.nsmallest(3, "variacao_hoje_pct")
    for _, row in baixas.iterrows():
        lines.append(
            f"  📉 {row['ticker']}: {row['variacao_hoje_pct']:+.2f}% "
            f"({format_brl(row['variacao_hoje_vl'])})"
        )

    return "\n".join(lines)
