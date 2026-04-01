# src/main_cli.py

"""
Ponto de entrada para uso via terminal ou notebook.
Substitui a execução sequencial do notebook.
"""

from src.collectors.supabase_client import load_transactions, load_asset_registry
from src.utils.parsers import clean_transactions_df
from src.portfolio.positions import calculate_positions, get_open_positions
from src.portfolio.daily import build_daily_report, daily_summary_accessible
from src.valuation.graham import graham_fair_price
from src.valuation.bazin import bazin_fair_price


def run_daily_report():
    """Executa o relatório diário completo."""

    print("🔄 Carregando transações do Supabase...")
    transactions = load_transactions()
    registry = load_asset_registry()

    print("📊 Calculando posições...")
    saldos = calculate_positions(transactions)
    abertas = get_open_positions(saldos)

    print("💹 Montando relatório diário...")
    report = build_daily_report(abertas)

    # Resumo acessível
    resumo = daily_summary_accessible(report)
    print("\n" + resumo)

    # Valuation rápido das posições
    print("\n\n🎯 VALUATION RÁPIDO (Graham):")
    for _, row in report.iterrows():
        if row.get("lpa") and row.get("vpa") and row["lpa"] > 0 and row["vpa"] > 0:
            fair = graham_fair_price(row["lpa"], row["vpa"])
            margin = ((fair - row["cotacao_atual"]) / fair) * 100
            status = "🟢 BARATO" if margin > 20 else "🟡 JUSTO" if margin > -10 else "🔴 CARO"
            print(f"  {row['ticker']}: Justo R$ {fair:.2f} | Atual R$ {row['cotacao_atual']:.2f} | {status}")

    return report


if __name__ == "__main__":
    run_daily_report()
