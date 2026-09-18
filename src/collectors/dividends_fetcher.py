"""
src/collectors/dividends_fetcher.py
Busca histórico de dividendos via yfinance.
Funciona para ativos BR (ex: PETR4.SA, HGLG11.SA) e US (ex: AAPL, MSFT).
"""

import os
import yfinance as yf
import pandas as pd
from datetime import datetime


def fetch_dividends(ticker: str, start: str = "2000-01-01") -> pd.DataFrame:
    """
    Busca histórico de dividendos de um ativo.
    """
    stock = yf.Ticker(ticker)

    # Dividendos históricos
    divs = stock.dividends
    if divs.empty:
        return pd.DataFrame()

    divs = divs.loc[start:]

    df = pd.DataFrame({
        "date": divs.index.date,
        "ticker": ticker.upper(),
        "type": _classify_type(ticker, stock),
        "gross_per_share": divs.values,
        "currency": "BRL" if ticker.upper().endswith(".SA") else "USD",
    })

    return df


def fetch_upcoming_dividends(ticker: str) -> dict | None:
    """
    Busca próximo dividendo agendado (se disponível).
    """
    stock = yf.Ticker(ticker)
    cal = stock.calendar

    if cal is None or (cal.empty if isinstance(cal, pd.DataFrame) else not cal):
        return None

    result = {"ticker": ticker.upper()}

    if isinstance(cal, dict):
        result["ex_date"] = cal.get("Ex-Dividend Date")
        result["dividend_date"] = cal.get("Dividend Date")
        result["amount"] = cal.get("Dividend Rate")
    elif isinstance(cal, pd.DataFrame):
        if "Ex-Dividend Date" in cal.index:
            result["ex_date"] = cal.loc["Ex-Dividend Date"].values[0]
        if "Dividend Date" in cal.index:
            result["dividend_date"] = cal.loc["Dividend Date"].values[0]

    return result if len(result) > 1 else None


def _classify_type(ticker: str, stock: yf.Ticker) -> str:
    """Classifica o tipo de provento com base no ativo."""
    ticker_upper = ticker.upper()

    # FIIs brasileiros (ex: HGLG11.SA)
    if ticker_upper.endswith(".SA"):
        code = ticker_upper.replace(".SA", "")
        if len(code) == 6 and code[-2:].isdigit() and int(code[-2:]) == 11:
            return "RENDIMENTO_FII"

    info = stock.info or {}
    quote_type = info.get("quoteType", "")

    if quote_type == "ETF":
        return "DISTRIBUICAO_ETF"

    return "DIVIDENDO"


def fetch_dividends_batch(tickers: list[str], start: str = "2000-01-01") -> pd.DataFrame:
    """Busca dividendos de vários ativos de uma vez."""
    frames = []
    for ticker in tickers:
        try:
            df = fetch_dividends(ticker, start)
            if not df.empty:
                frames.append(df)
        except Exception as e:
            print(f"⚠️  Erro ao buscar dividendos de {ticker}: {e}")

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


# =====================================================================
# RODA NO GITHUB ACTIONS / TERMINAL
# =====================================================================
def run_sync():
    """
    Sincroniza os dividendos dos ativos ativos cadastrados no Supabase.
    Identifica a moeda via relacionamento com a tabela currencies.
    """
    try:
        from supabase import create_client
    except ImportError:
        print("❌ Biblioteca 'supabase' não instalada no ambiente.")
        return

    try:
        from dotenv import load_dotenv
        from pathlib import Path

        root_dir = Path(__file__).resolve().parent.parent.parent
        env_path = root_dir / ".env"
        env_local_path = root_dir / ".env.local"

        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        if env_local_path.exists():
            load_dotenv(dotenv_path=env_local_path)
    except ImportError:
        pass

    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    if not url or not key:
        print("⚠️ Variáveis SUPABASE_URL e SUPABASE_KEY não encontradas.")
        return

    supabase = create_client(url, key)

    # 1. Busca os ativos ativos relacionando com a tabela currencies para pegar o código da moeda (ex: BRL, USD)
    res = supabase.table("assets") \
        .select("ticker, is_active, currencies(symbol, code)") \
        .eq("is_active", True) \
        .execute()
    
    assets = res.data if res.data else []

    if not assets:
        print("Nenhum ativo ativo encontrado para sincronizar.")
        return

    yf_tickers = []
    ticker_map = {}

    crypto_list = {"AAVE", "BTC", "ETH", "SOL", "USDT", "ADA", "XRP", "DOT", "LINK"}

    for item in assets:
        t_clean = item["ticker"].strip().upper()
        
        # Extrai o código da moeda do relacionamento
        currency_info = item.get("currencies") or {}
        currency_code = (currency_info.get("code") or currency_info.get("symbol") or "").upper()

        # A) Criptomoedas
        if t_clean in crypto_list or currency_code in ["CRYPTO", "CRIPTO"]:
            formatted = f"{t_clean}-USD" if not t_clean.endswith("-USD") else t_clean

        # B) Ativos em USD (EUA/Internacionais: AAPL, BIL, IVV)
        elif currency_code == "USD" or t_clean.endswith(".US"):
            formatted = t_clean.replace(".US", "")

        # C) Ativos em BRL (Brasil/B3: BBAS3, TRXF11, VALE3) -> Adiciona .SA se não tiver
        elif currency_code == "BRL" or t_clean[-1].isdigit():
            formatted = f"{t_clean}.SA" if not t_clean.endswith(".SA") else t_clean

        # D) Caso padrão
        else:
            formatted = t_clean

        yf_tickers.append(formatted)
        ticker_map[formatted] = t_clean

    print(f"🔄 Buscando dividendos no yfinance para {len(yf_tickers)} ativos:")
    print(yf_tickers)

    df_divs = fetch_dividends_batch(yf_tickers)

    if not df_divs.empty:
        # Restaura o ticker original cadastrado no banco Supabase
        df_divs['ticker'] = df_divs['ticker'].map(lambda x: ticker_map.get(x, x.replace(".SA", "")))
        df_divs['date'] = df_divs['date'].astype(str)

        records = df_divs.to_dict(orient="records")

        supabase.table("dividends").upsert(
            records, 
            on_conflict="date, ticker, gross_per_share"
        ).execute()
        
        print(f"✅ {len(records)} registros de dividendos sincronizados com sucesso!")
    else:
        print("ℹ️ Nenhum dividendo encontrado para os ativos informados.")

if __name__ == "__main__":
    run_sync()