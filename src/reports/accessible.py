"""
src/reports/accessible.py
Relatórios acessíveis em texto puro — otimizados para leitores de tela.
"""

import pandas as pd
from src.utils.formatters import (
    format_brl, format_usd, format_qtde,
    format_pct, text_bar,
)
from src.portfolio.allocation import (
    allocation_by_category, allocation_by_currency, top_positions,
)
from src.portfolio.dividends import (
    monthly_summary,
    annual_summary,
    by_ticker,
    by_category,
    yield_on_cost,
    monthly_evolution,
)
from src.collectors.dividends_fetcher import fetch_upcoming_dividends


def portfolio_summary(abertas: pd.DataFrame) -> str:
    """Resumo completo sem cotações de mercado (custo apenas)."""
    total_brl = abertas["custo_total_brl"].sum()
    sections = [
        _section_header(abertas, total_brl),
        _section_positions_by_category(abertas, total_brl),
        _section_allocation_by_category(abertas, total_brl),
        _section_allocation_by_currency(abertas, total_brl),
        _section_top_positions(abertas, total_brl),
    ]
    return "\n".join(sections)


def market_summary(enriched: pd.DataFrame, totals: dict) -> str:
    """
    Resumo completo COM cotações de mercado, lucro/prejuízo e rentabilidade.

    Args:
        enriched: DataFrame enriquecido (output de enrich_with_market_data).
        totals: Dict de totais (output de portfolio_totals).

    Returns:
        String formatada pronta para print().
    """
    sections = [
        _section_market_header(enriched, totals),
        _section_market_positions(enriched, totals),
        _section_market_allocation(enriched, totals),
        _section_allocation_by_currency(enriched, totals["total_mercado_brl"]),
        _section_market_top(enriched, totals),
    ]
    return "\n".join(sections)


def positions_detail(abertas: pd.DataFrame) -> str:
    """Gera lista detalhada de todas as posições abertas."""
    total_brl = abertas["custo_total_brl"].sum()
    return _section_positions_by_category(abertas, total_brl)


def allocation_summary(abertas: pd.DataFrame) -> str:
    """Gera apenas o resumo de alocação (categoria + moeda)."""
    total_brl = abertas["custo_total_brl"].sum()
    parts = [
        _section_allocation_by_category(abertas, total_brl),
        _section_allocation_by_currency(abertas, total_brl),
    ]
    return "\n".join(parts)


# ── Seções SEM cotação ────────────────────────────────────────

def _section_header(abertas: pd.DataFrame, total_brl: float) -> str:
    lines = [
        "=" * 60,
        "📊 RESUMO GERAL DA CARTEIRA",
        "=" * 60,
        "",
        f"Total investido (BRL): {format_brl(total_brl)}",
        f"Posições abertas: {len(abertas)}",
        f"Categorias: {abertas['categoria'].nunique()}",
        "",
    ]
    return "\n".join(lines)


def _section_positions_by_category(abertas: pd.DataFrame, total_brl: float) -> str:
    lines = [
        "=" * 60,
        "📁 POSIÇÕES POR CATEGORIA",
        "=" * 60,
    ]

    for categoria, grupo in abertas.groupby("categoria"):
        subtotal = grupo["custo_total_brl"].sum()
        peso = (subtotal / total_brl * 100) if total_brl > 0 else 0

        lines.append("")
        lines.append(
            f"── {categoria} ({len(grupo)} ativos | "
            f"{peso:.1f}% da carteira | {format_brl(subtotal)}) ──"
        )
        lines.append("")

        for _, row in grupo.sort_values("custo_total_brl", ascending=False).iterrows():
            lines.append(_format_position_line(row, total_brl))

    lines.append("")
    return "\n".join(lines)


def _section_allocation_by_category(abertas: pd.DataFrame, total_brl: float) -> str:
    alocacao = allocation_by_category(abertas)

    lines = [
        "=" * 60,
        "📊 ALOCAÇÃO POR CATEGORIA",
        "=" * 60,
        "",
    ]

    for _, row in alocacao.iterrows():
        barra = text_bar(row["peso_pct"])
        lines.append(
            f"  {row['categoria']:20s} {barra} "
            f"{row['peso_pct']:5.1f}% ({format_brl(row['custo_total_brl'])})"
        )

    lines.append("")
    lines.append(f"  {'TOTAL':20s} {'█' * 50} 100.0% ({format_brl(total_brl)})")
    lines.append("")
    return "\n".join(lines)


def _section_allocation_by_currency(abertas: pd.DataFrame, total_brl: float) -> str:
    alocacao = allocation_by_currency(abertas)

    lines = [
        "=" * 60,
        "💱 ALOCAÇÃO POR MOEDA",
        "=" * 60,
        "",
    ]

    for _, row in alocacao.iterrows():
        peso = (row["custo_total_brl"] / total_brl * 100) if total_brl > 0 else 0
        barra = text_bar(peso)
        lines.append(
            f"  {row['moeda']:20s} {barra} "
            f"{peso:5.1f}% ({format_brl(row['custo_total_brl'])})"
        )

    lines.append("")
    return "\n".join(lines)


def _section_top_positions(abertas: pd.DataFrame, total_brl: float, n: int = 10) -> str:
    top = top_positions(abertas, n)

    lines = [
        "=" * 60,
        f"🏆 TOP {n} MAIORES POSIÇÕES (por custo em BRL)",
        "=" * 60,
        "",
    ]

    for i, (_, row) in enumerate(top.iterrows(), 1):
        peso = (row["custo_total_brl"] / total_brl * 100) if total_brl > 0 else 0
        lines.append(
            f"  {i:2d}. {row['ticker']:12s} | "
            f"{row['categoria']:20s} | "
            f"{format_brl(row['custo_total_brl']):>16s} | "
            f"Peso: {peso:.1f}%"
        )

    lines.append("")
    return "\n".join(lines)


def _format_position_line(row: pd.Series, total_brl: float) -> str:
    peso = (row["custo_total_brl"] / total_brl * 100) if total_brl > 0 else 0

    if row["moeda"] == "USD":
        preco_info = (
            f"PM: {format_usd(row['preco_medio'])} "
            f"(BRL: {format_brl(row['preco_medio_brl'])}) | "
            f"Câmbio: R$ {row['ultimo_cambio']:.4f}"
        )
        custo_info = (
            f"Custo: {format_usd(row['custo_total'])} "
            f"({format_brl(row['custo_total_brl'])})"
        )
    else:
        preco_info = f"PM: {format_brl(row['preco_medio'])}"
        custo_info = f"Custo: {format_brl(row['custo_total_brl'])}"

    return (
        f"  • {row['ticker']:12s} | "
        f"Qtde: {format_qtde(row['qtde_saldo']):>10s} | "
        f"{preco_info} | "
        f"{custo_info} | "
        f"Peso: {peso:.1f}%"
    )


# ── Seções COM cotação de mercado ─────────────────────────────

def _section_market_header(enriched: pd.DataFrame, totals: dict) -> str:
    t = totals
    lucro_emoji = "📈" if t["lucro_total_brl"] >= 0 else "📉"
    rent_str = format_pct(t["rentabilidade_total_pct"])

    lines = [
        "=" * 60,
        f"📊 CARTEIRA — VISÃO DE MERCADO",
        "=" * 60,
        "",
        f"💰 Total investido:    {format_brl(t['total_investido_brl'])}",
        f"🏦 Valor de mercado:   {format_brl(t['total_mercado_brl'])}",
        f"{lucro_emoji} Lucro/Prejuízo:     {format_brl(t['lucro_total_brl'])} ({rent_str})",
        f"💵 Dólar (USD/BRL):    R$ {t['usdbrl']:.4f}",
        f"📂 Posições abertas:   {len(enriched)}",
        "",
    ]
    return "\n".join(lines)


def _section_market_positions(enriched: pd.DataFrame, totals: dict) -> str:
    total_mercado = totals["total_mercado_brl"]

    lines = [
        "=" * 60,
        "📁 POSIÇÕES COM COTAÇÃO ATUAL",
        "=" * 60,
    ]

    for categoria, grupo in enriched.groupby("categoria"):
        sub_mercado = grupo["valor_mercado_brl"].sum()
        sub_lucro = grupo["lucro_prejuizo_brl"].sum()
        peso = (sub_mercado / total_mercado * 100) if total_mercado > 0 else 0
        emoji = "📈" if sub_lucro >= 0 else "📉"

        lines.append("")
        lines.append(
            f"── {categoria} ({len(grupo)} ativos | "
            f"{peso:.1f}% | Mercado: {format_brl(sub_mercado)} | "
            f"{emoji} {format_brl(sub_lucro)}) ──"
        )
        lines.append("")

        for _, row in grupo.sort_values("valor_mercado_brl", ascending=False).iterrows():
            lines.append(_format_market_line(row, total_mercado))

    lines.append("")
    return "\n".join(lines)


def _section_market_allocation(enriched: pd.DataFrame, totals: dict) -> str:
    total_mercado = totals["total_mercado_brl"]

    alocacao = (
        enriched.groupby("categoria")
        .agg(
            valor_mercado_brl=("valor_mercado_brl", "sum"),
            lucro_prejuizo_brl=("lucro_prejuizo_brl", "sum"),
        )
        .sort_values("valor_mercado_brl", ascending=False)
        .reset_index()
    )

    lines = [
        "=" * 60,
        "📊 ALOCAÇÃO POR CATEGORIA (a mercado)",
        "=" * 60,
        "",
    ]

    for _, row in alocacao.iterrows():
        peso = (row["valor_mercado_brl"] / total_mercado * 100) if total_mercado > 0 else 0
        barra = text_bar(peso)
        emoji = "📈" if row["lucro_prejuizo_brl"] >= 0 else "📉"
        lines.append(
            f"  {row['categoria']:20s} {barra} "
            f"{peso:5.1f}% ({format_brl(row['valor_mercado_brl'])}) "
            f"{emoji} {format_brl(row['lucro_prejuizo_brl'])}"
        )

    lines.append("")
    lines.append(
        f"  {'TOTAL':20s} {'█' * 50} 100.0% "
        f"({format_brl(total_mercado)})"
    )
    lines.append("")
    return "\n".join(lines)


def _section_market_top(enriched: pd.DataFrame, totals: dict, n: int = 10) -> str:
    total_mercado = totals["total_mercado_brl"]
    top = enriched.nlargest(n, "valor_mercado_brl").reset_index(drop=True)

    lines = [
        "=" * 60,
        f"🏆 TOP {n} MAIORES POSIÇÕES (valor de mercado)",
        "=" * 60,
        "",
    ]

    for i, (_, row) in enumerate(top.iterrows(), 1):
        peso = (row["valor_mercado_brl"] / total_mercado * 100) if total_mercado > 0 else 0
        emoji = "📈" if row["lucro_prejuizo_brl"] >= 0 else "📉"
        rent = format_pct(row["rentabilidade_pct"])

        lines.append(
            f"  {i:2d}. {row['ticker']:12s} | "
            f"{format_brl(row['valor_mercado_brl']):>16s} | "
            f"{emoji} {format_brl(row['lucro_prejuizo_brl']):>14s} ({rent:>8s}) | "
            f"Peso: {peso:.1f}%"
        )

    lines.append("")
    return "\n".join(lines)


def _format_market_line(row: pd.Series, total_mercado: float) -> str:
    """Formata uma linha com dados de mercado."""
    peso = (row["valor_mercado_brl"] / total_mercado * 100) if total_mercado > 0 else 0
    emoji = "📈" if row["lucro_prejuizo_brl"] >= 0 else "📉"
    rent = format_pct(row["rentabilidade_pct"])

    preco_atual = row.get("preco_atual")
    variacao = row.get("variacao_dia_pct")

    if preco_atual is None or pd.isna(preco_atual):
        cotacao_str = "Cotação indisponível"
    elif row["moeda"] == "USD":
        cotacao_str = (
            f"Atual: {format_usd(preco_atual)} "
            f"(BRL: {format_brl(row['preco_atual_brl'])})"
        )
    else:
        cotacao_str = f"Atual: {format_brl(preco_atual)}"

    var_str = ""
    if variacao is not None and not pd.isna(variacao):
        var_str = f" | Dia: {format_pct(variacao)}"

    return (
        f"  • {row['ticker']:12s} | "
        f"Qtde: {format_qtde(row['qtde_saldo']):>10s} | "
        f"{cotacao_str}{var_str} | "
        f"Mercado: {format_brl(row['valor_mercado_brl'])} | "
        f"{emoji} {format_brl(row['lucro_prejuizo_brl'])} ({rent}) | "
        f"Peso: {peso:.1f}%"
    )

def dividends_report(year: int | None = None, cost_map: dict | None = None) -> str:
    """
    Gera relatório completo e acessível de dividendos.
    Texto puro, otimizado para leitores de tela.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("RELATÓRIO DE DIVIDENDOS RECEBIDOS")
    lines.append("=" * 60)

    # --- Resumo anual ---
    lines.append("\n--- RESUMO ANUAL ---")
    df_annual = annual_summary()
    if df_annual.empty:
        lines.append("Nenhum dividendo registrado.")
    else:
        for _, row in df_annual.iterrows():
            total = row["total_received"] or 0
            lines.append(
                f"Ano {int(row['year'])}: "
                f"R$ {total:,.2f} recebidos em {int(row['count'])} pagamentos."
            )

    # --- Resumo mensal ---
    lines.append("\n--- RESUMO MENSAL ---")
    df_monthly = monthly_summary(year=year)
    if df_monthly.empty:
        lines.append("Sem dados mensais.")
    else:
        for _, row in df_monthly.iterrows():
            total = row["total_received"] or 0
            lines.append(
                f"{row['year_month']}: R$ {total:,.2f} ({int(row['count'])} pagamentos)"
            )

    # --- Ranking por ativo ---
    lines.append("\n--- DIVIDENDOS POR ATIVO (ranking) ---")
    df_ticker = by_ticker()
    if not df_ticker.empty:
        for i, (_, row) in enumerate(df_ticker.iterrows(), 1):
            total = row["total_received"] or 0
            lines.append(
                f"{i}º {row['ticker']}: R$ {total:,.2f} "
                f"({int(row['count'])} pagamentos, último em {row['last_payment']})"
            )

    # --- Por categoria ---
    lines.append("\n--- DIVIDENDOS POR CATEGORIA ---")
    df_cat = by_category()
    if not df_cat.empty:
        for _, row in df_cat.iterrows():
            total = row["total_received"] or 0
            lines.append(
                f"{row['category_label']}: R$ {total:,.2f} ({int(row['count'])} pagamentos)"
            )

    # --- Yield on Cost ---
    if cost_map:
        lines.append("\n--- YIELD ON COST (retorno sobre custo) ---")
        df_yoc = yield_on_cost(cost_map)
        if not df_yoc.empty:
            for _, row in df_yoc.iterrows():
                lines.append(
                    f"{row['ticker']}: {row['yoc_percent']:.2f}% "
                    f"(recebeu R$ {row['total_dividends']:,.2f} "
                    f"sobre custo de R$ {row['acquisition_cost']:,.2f})"
                )

    # --- Evolução mensal ---
    lines.append("\n--- EVOLUÇÃO MENSAL (últimos 12 meses) ---")
    df_evol = monthly_evolution(12)
    if not df_evol.empty:
        for _, row in df_evol.iterrows():
            lines.append(
                f"{row['year_month']}: R$ {row['total']:,.2f} "
                f"(média 3 meses: R$ {row['moving_avg_3m']:,.2f})"
            )

    lines.append("\n" + "=" * 60)
    lines.append("Fim do relatório de dividendos.")
    lines.append("=" * 60)

    return "\n".join(lines)


def upcoming_dividends_report(tickers: list[str]) -> str:
    """
    Relatório acessível de dividendos futuros agendados.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("PRÓXIMOS DIVIDENDOS AGENDADOS")
    lines.append("=" * 60)

    found = False
    for ticker in tickers:
        try:
            info = fetch_upcoming_dividends(ticker)
            if info and (info.get("ex_date") or info.get("dividend_date")):
                found = True
                lines.append(f"\n{info['ticker']}:")
                if info.get("ex_date"):
                    lines.append(f"  Data ex-dividendo: {info['ex_date']}")
                if info.get("dividend_date"):
                    lines.append(f"  Data de pagamento: {info['dividend_date']}")
                if info.get("amount"):
                    lines.append(f"  Valor estimado (anualizado): {info['amount']}")
        except Exception:
            pass

    if not found:
        lines.append("Nenhum dividendo futuro encontrado para os ativos informados.")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)
