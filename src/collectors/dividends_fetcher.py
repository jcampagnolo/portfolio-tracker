"""
src/collectors/dividends_fetcher.py
Busca histórico de dividendos via yfinance.
Funciona para ativos BR (ex: PETR4.SA, HGLG11.SA) e US (ex: AAPL, MSFT).
"""

import yfinance as yf
import pandas as pd
from datetime import datetime


def fetch_dividends(ticker: str, start: str = "2000-01-01") -> pd.DataFrame:
    """
    Busca histórico de dividendos de um ativo.

    Args:
        ticker: código do ativo (ex: 'PETR4.SA', 'AAPL')
        start: data inicial no formato 'YYYY-MM-DD'

    Returns:
        DataFrame com colunas:
            - date: data de pagamento
            - ticker: código do ativo
            - type: tipo do provento
            - gross_per_share: valor bruto por cota
            - currency: moeda (BRL ou USD)
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

    Returns:
        dict com ex_date, payment_date, amount ou None
    """
    stock = yf.Ticker(ticker)
    cal = stock.calendar

    if cal is None or cal.empty if isinstance(cal, pd.DataFrame) else not cal:
        return None

    result = {"ticker": ticker.upper()}

    if isinstance(cal, dict):
        result["ex_date"] = cal.get("Ex-Dividend Date")
        result["dividend_date"] = cal.get("Dividend Date")
        result["amount"] = cal.get("Dividend Rate")  # anualizado
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

    # Para ações BR, yfinance não diferencia dividendo de JCP
    # (precisaria de outra fonte para isso)
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
