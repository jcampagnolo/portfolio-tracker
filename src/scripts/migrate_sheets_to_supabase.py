# src/scripts/seed_transactions.py

"""
Seed do banco de dados a partir do arquivo data/lctos_status_invest.json
─────────────────────────────────────────────────────────────────────────
• Limpa as tabelas antes de inserir
• Importa TODOS os ativos (BR, USD, Cripto, Tesouro)
• Busca cotação do dólar no BCB para operações em USD
• Vincula conversões (E) ↔ (S)
"""

import json
import re
import time
from pathlib import Path
from datetime import datetime, timedelta

import requests
from src.config import settings
from supabase import create_client

# ============================================================
# CONFIGURAÇÕES
# ============================================================

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "lctos_status_invest.json"

WALLET_NAME = "Alisson"
WALLET_OWNER = "Alisson"

# Categorias que operam em USD
CATEGORIAS_USD = {"ETF Exterior", "Stocks", "REITs"}

# Mapeamento: categoria do JSON → nome na tabela asset_categories
CATEGORY_MAP = {
    "Ações": "Ações",
    "FIIs": "FIIs",
    "FIAGRO": "FIAGRO",
    "ETF BR": "ETF",
    "ETF Exterior": "ETF Exterior",
    "Stocks": "Stocks",
    "BDR": "BDR",
    "REITs": "REITs",
    "Criptomoedas": "Criptomoedas",
    "Tesouro": "Tesouro",
}

# Mapeamento: ordem do JSON → transaction_type (enum no banco)
ORDER_MAP = {
    "Compra": "compra",
    "Venda": "venda",
    "Bonificação": "bonificacao",
    "Desdobramento": "desdobramento",
    "Conversão (E)": "conversao_entrada",
    "Conversão (S)": "conversao_saida",
}

# Cache de cotações do dólar (date_str → rate)
_exchange_cache: dict[str, float] = {}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def parse_preco(valor: str) -> float:
    """
    Converte preço BR para float.
    '1.234,56' → 1234.56
    '463.080,39000000' → 463080.39
    """
    valor = valor.strip()
    valor = re.sub(r"[R$\s]", "", valor)
    # Formato BR: ponto = milhar, vírgula = decimal
    valor = valor.replace(".", "").replace(",", ".")
    return float(valor)


def parse_total(valor: str) -> float:
    """
    Converte total que pode ter prefixo 'R$' ou '$'.
    'R$ 1.234,56' → 1234.56
    '$ 112,91' → 112.91
    """
    valor = valor.strip()
    valor = re.sub(r"[R$\s]", "", valor)
    valor = valor.replace(".", "").replace(",", ".")
    return float(valor)


def parse_quantidade(valor: str) -> float:
    """Converte quantidade string para float."""
    valor = valor.strip().replace(".", "").replace(",", ".")
    return float(valor)


def parse_date(data_str: str) -> str:
    """Converte 'dd/mm/yyyy' para 'yyyy-mm-dd'."""
    dt = datetime.strptime(data_str.strip(), "%d/%m/%Y")
    return dt.strftime("%Y-%m-%d")


def load_json(filepath: Path) -> list[dict]:
    """Carrega o JSON de lançamentos."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"📂 Arquivo carregado: {len(data)} registros totais")
    return data


# ============================================================
# COTAÇÃO DO DÓLAR (BCB)
# ============================================================

def fetch_exchange_rate_bcb(date_str: str) -> float | None:
    """
    Busca cotação de fechamento USD/BRL no BCB para uma data.
    Se não houver cotação (feriado/fds), tenta os 5 dias anteriores.
    Retorna o rate ou None.
    """
    if date_str in _exchange_cache:
        return _exchange_cache[date_str]

    dt = datetime.strptime(date_str, "%Y-%m-%d")

    # Tenta a data e até 5 dias antes (para feriados/fins de semana)
    for i in range(6):
        target = dt - timedelta(days=i)
        formatted = target.strftime("%m-%d-%Y")

        url = (
            "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            "CotacaoMoedaDia(moeda=@moeda,dataCotacao=@data)"
            f"?@moeda='USD'&@data='{formatted}'"
            "&$top=100&$format=json"
            "&$select=cotacaoVenda,tipoBoletim"
        )

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("value", [])

            # Pega cotação de fechamento (ou a última disponível)
            for item in reversed(data):
                if item.get("tipoBoletim") == "Fechamento":
                    rate = float(item["cotacaoVenda"])
                    _exchange_cache[date_str] = rate
                    return rate

            # Se não tem "Fechamento", pega a última
            if data:
                rate = float(data[-1]["cotacaoVenda"])
                _exchange_cache[date_str] = rate
                return rate

        except Exception:
            pass

        time.sleep(0.3)  # Respeita rate limit do BCB

    print(f"   ⚠️  Cotação não encontrada para {date_str}")
    return None


def fetch_all_exchange_rates(records: list[dict]) -> dict[str, float]:
    """
    Busca cotações para todas as datas únicas de operações em USD.
    Retorna dict: 'yyyy-mm-dd' → rate
    """
    usd_dates = set()
    for r in records:
        if r["categoria"] in CATEGORIAS_USD:
            usd_dates.add(parse_date(r["negociacao"]))

    if not usd_dates:
        return {}

    sorted_dates = sorted(usd_dates)
    print(f"💱 Buscando cotações USD/BRL para {len(sorted_dates)} datas...")

    rates = {}
    for i, d in enumerate(sorted_dates, 1):
        rate = fetch_exchange_rate_bcb(d)
        if rate:
            rates[d] = rate
        # Pequeno delay pra não estourar rate limit
        if i % 5 == 0:
            time.sleep(0.5)

    print(f"   ✅ {len(rates)} cotações obtidas\n")
    return rates


# ============================================================
# SEED PRINCIPAL
# ============================================================

def seed():
    # ── Conexão ──────────────────────────────────────────────
    print("=" * 60)
    print("🚀 SEED DE TRANSAÇÕES")
    print("=" * 60)
    print(f"\n🔗 Conectando ao Supabase...")
    db = create_client(settings.supabase_url, settings.supabase_key)
    print("✅ Conectado!\n")

    # ── Carregar dados ───────────────────────────────────────
    raw = load_json(DATA_FILE)

    # Filtrar categorias que temos no banco (excluir o que não mapeamos)
    records = [r for r in raw if r["categoria"] in CATEGORY_MAP]
    ignored = [r for r in raw if r["categoria"] not in CATEGORY_MAP]

    if ignored:
        cats_ignored = set(r["categoria"] for r in ignored)
        print(f"⏭️  Categorias ignoradas (sem mapeamento): {cats_ignored}")

    print(f"📋 Registros a importar: {len(records)}\n")

    if not records:
        print("❌ Nenhum registro para importar.")
        return

    # ── Resumo ───────────────────────────────────────────────
    categorias = {}
    ordens = set()
    for r in records:
        cat = r["categoria"]
        categorias[cat] = categorias.get(cat, 0) + 1
        ordens.add(r["ordem"])

    print("📊 Resumo por categoria:")
    for cat, qtd in sorted(categorias.items()):
        moeda = "USD" if cat in CATEGORIAS_USD else "BRL"
        print(f"   {cat} ({moeda}): {qtd}")
    print(f"\n📊 Tipos de ordem encontrados: {', '.join(sorted(ordens))}\n")

    # ── Buscar cotações USD/BRL ──────────────────────────────
    exchange_rates = fetch_all_exchange_rates(records)

    # ── 1. Limpar tabelas (ordem por FK) ─────────────────────
    print("🧹 Limpando tabelas...")
    tables_to_clean = [
        "transactions",
        "exchange_rates",
        "broker_accounts",
        "assets",
        "brokers",
        "wallets",
    ]
    for table in tables_to_clean:
        try:
            db.table(table).delete().neq("id", 0).execute()
            print(f"   ✅ {table}")
        except Exception as e:
            print(f"   ⚠️  {table}: {e}")
    print()

    # ── 2. Buscar dados de referência ────────────────────────
    print("📁 Buscando dados de referência...")

    # Moedas
    currencies = db.table("currencies").select("*").execute()
    currency_map = {c["code"]: c["id"] for c in currencies.data}
    print(f"   Moedas: {currency_map}")

    # Categorias
    categories = db.table("asset_categories").select("*").execute()
    cat_db_map = {c["name"]: c["id"] for c in categories.data}
    print(f"   Categorias: {list(cat_db_map.keys())}")
    print()

    # Verificar se REITs existe no banco, se não, verificar se precisa
    missing_cats = set()
    for r in records:
        mapped = CATEGORY_MAP.get(r["categoria"])
        if mapped and mapped not in cat_db_map:
            missing_cats.add(mapped)

    if missing_cats:
        print(f"⚠️  Categorias faltando no banco: {missing_cats}")
        print("   Inserindo categorias faltantes...")
        for cat_name in missing_cats:
            is_variable = cat_name not in ("Tesouro", "CDB", "LCA", "LCI")
            default_curr = currency_map.get("USD") if cat_name in ("ETF Exterior", "Stocks", "REITs") else currency_map.get("BRL")
            result = db.table("asset_categories").insert({
                "name": cat_name,
                "description": f"Categoria: {cat_name}",
                "is_variable_income": is_variable,
                "default_currency_id": default_curr,
            }).execute()
            cat_db_map[cat_name] = result.data[0]["id"]
            print(f"   ✅ {cat_name} → id={cat_db_map[cat_name]}")
        print()

    # ── 3. Inserir wallet ────────────────────────────────────
    print(f"👤 Inserindo wallet '{WALLET_NAME}'...")
    wallet = db.table("wallets").insert({
        "name": WALLET_NAME,
        "owner_name": WALLET_OWNER,
    }).execute()
    wallet_id = wallet.data[0]["id"]
    print(f"   ✅ wallet_id = {wallet_id}\n")

    # ── 4. Inserir brokers ───────────────────────────────────
    print("🏦 Inserindo brokers...")
    broker_names = sorted(set(r["broker"] for r in records))
    broker_map = {}

    for name in broker_names:
        result = db.table("brokers").insert({"name": name}).execute()
        broker_id = result.data[0]["id"]
        broker_map[name] = broker_id
        print(f"   ✅ {name} → id={broker_id}")
    print()

    # ── 5. Inserir broker_accounts ───────────────────────────
    print("🔗 Inserindo broker_accounts...")
    account_map = {}

    for name, broker_id in broker_map.items():
        result = db.table("broker_accounts").insert({
            "wallet_id": wallet_id,
            "broker_id": broker_id,
        }).execute()
        account_map[name] = result.data[0]["id"]
        print(f"   ✅ {name} → account_id={account_map[name]}")
    print()

    # ── 6. Inserir exchange_rates ────────────────────────────
    if exchange_rates:
        print("💱 Inserindo cotações USD/BRL...")
        usd_id = currency_map["USD"]
        brl_id = currency_map["BRL"]

        for rate_date, rate in sorted(exchange_rates.items()):
            db.table("exchange_rates").insert({
                "from_currency_id": usd_id,
                "to_currency_id": brl_id,
                "rate_date": rate_date,
                "rate": rate,
                "source": "BCB",
            }).execute()

        print(f"   ✅ {len(exchange_rates)} cotações inseridas\n")

    # ── 7. Inserir assets (únicos) ───────────────────────────
    print("📈 Inserindo assets...")
    ticker_info = {}
    for r in records:
        ticker = r["ticker"].strip().upper()
        if ticker not in ticker_info:
            ticker_info[ticker] = r["categoria"]

    asset_map = {}  # ticker → id
    for ticker, categoria in sorted(ticker_info.items()):
        cat_name = CATEGORY_MAP.get(categoria)
        if not cat_name or cat_name not in cat_db_map:
            print(f"   ⚠️  Sem categoria para {ticker} ({categoria})")
            continue

        category_id = cat_db_map[cat_name]
        currency_id = currency_map["USD"] if categoria in CATEGORIAS_USD else currency_map["BRL"]

        result = db.table("assets").insert({
            "ticker": ticker,
            "name": ticker,
            "category_id": category_id,
            "currency_id": currency_id,
        }).execute()

        asset_map[ticker] = result.data[0]["id"]

    print(f"   ✅ {len(asset_map)} ativos inseridos\n")

    # ── 8. Inserir transactions ──────────────────────────────
    print("💰 Inserindo transactions...")
    tx_count = 0
    tx_errors = 0
    conversion_pairs = []  # para vincular depois

    for idx, r in enumerate(records):
        ticker = r["ticker"].strip().upper()
        asset_id = asset_map.get(ticker)

        if not asset_id:
            tx_errors += 1
            continue

        broker_name = r["broker"]
        broker_id = broker_map.get(broker_name)

        if not broker_id:
            tx_errors += 1
            continue

        transaction_type = ORDER_MAP.get(r["ordem"])
        if not transaction_type:
            print(f"   ⚠️  Ordem desconhecida: '{r['ordem']}' ({ticker})")
            tx_errors += 1
            continue

        try:
            trade_date = parse_date(r["negociacao"])
            quantity = parse_quantidade(r["quantidade"])
            unit_price = parse_preco(r["preco"])
            total_amount = parse_total(r["total"])
        except (ValueError, KeyError) as e:
            print(f"   ⚠️  Erro ao parsear {ticker} idx={idx}: {e}")
            tx_errors += 1
            continue

        is_usd = r["categoria"] in CATEGORIAS_USD
        currency_id = currency_map["USD"] if is_usd else currency_map["BRL"]

        # Câmbio
        exchange_rate = None
        total_brl = None
        if is_usd:
            exchange_rate = exchange_rates.get(trade_date)
            if exchange_rate:
                total_brl = round(total_amount * exchange_rate, 2)

        tx_data = {
            "wallet_id": wallet_id,
            "asset_id": asset_id,
            "broker_id": broker_id,
            "transaction_type": transaction_type,
            "trade_date": trade_date,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_amount": total_amount,
            "currency_id": currency_id,
            "exchange_rate_to_brl": exchange_rate,
            "total_amount_brl": total_brl,
            "source": "status_invest",
        }

        result = db.table("transactions").insert(tx_data).execute()
        tx_id = result.data[0]["id"]
        tx_count += 1

        # Guardar conversões pra vincular depois
        if transaction_type in ("conversao_entrada", "conversao_saida"):
            conversion_pairs.append({
                "id": tx_id,
                "type": transaction_type,
                "ticker": ticker,
                "broker": broker_name,
                "date": trade_date,
                "quantity": quantity,
                "total": total_amount,
            })

    print(f"   ✅ {tx_count} transações inseridas")
    if tx_errors:
        print(f"   ⚠️  {tx_errors} registros com erro/ignorados")
    print()

    # ── 9. Vincular conversões ───────────────────────────────
    if conversion_pairs:
        print("🔄 Vinculando pares de conversão...")
        entradas = [c for c in conversion_pairs if c["type"] == "conversao_entrada"]
        saidas = [c for c in conversion_pairs if c["type"] == "conversao_saida"]

        linked = 0
        used_saidas = set()

        for entrada in entradas:
            # Procura a saída correspondente: mesma data, mesmo broker, mesmo total
            for saida in saidas:
                if saida["id"] in used_saidas:
                    continue
                if (
                    saida["date"] == entrada["date"]
                    and saida["broker"] == entrada["broker"]
                    and abs(saida["total"] - entrada["total"]) < 0.02
                ):
                    # Vincular
                    db.table("transactions").update(
                        {"conversion_pair_id": saida["id"]}
                    ).eq("id", entrada["id"]).execute()

                    db.table("transactions").update(
                        {"conversion_pair_id": entrada["id"]}
                    ).eq("id", saida["id"]).execute()

                    used_saidas.add(saida["id"])
                    linked += 1
                    print(f"   🔗 {saida['ticker']} → {entrada['ticker']} ({entrada['date']})")
                    break

        print(f"   ✅ {linked} pares vinculados\n")

    # ── Resumo final ─────────────────────────────────────────
    print("=" * 60)
    print("🎉 SEED CONCLUÍDO!")
    print("=" * 60)

    # Verificação
    total_tx = db.table("transactions").select("id", count="exact").execute()
    total_assets = db.table("assets").select("id", count="exact").execute()

    print(f"📋 Transações no banco: {total_tx.count}")
    print(f"📈 Ativos no banco:     {total_assets.count}")
    print(f"🏦 Brokers:             {len(broker_map)}")
    print(f"💱 Cotações USD/BRL:    {len(exchange_rates)}")
    print(f"👤 Wallet:              {WALLET_NAME} (id={wallet_id})")

    # Testar view
    try:
        positions = db.table("portfolio_positions").select("*").execute()
        print(f"\n📊 Posições com saldo > 0: {len(positions.data)}")
    except Exception:
        print("\n⚠️  View portfolio_positions não encontrada (criar depois)")

    print()


if __name__ == "__main__":
    seed()
