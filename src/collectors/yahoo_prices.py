"""
src/collectors/yahoo_prices.py
Coleta de cotações em tempo real via Yahoo Finance.

Tickers BR usam sufixo .SA (ex: PETR4.SA).
Câmbio USD/BRL usa o ticker BRL=X.
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Sufixos por moeda para o Yahoo Finance
_SUFFIX_MAP = {
    "BRL": ".SA",
    "USD": "",
}

# Ticker do câmbio USD → BRL
USDBRL_TICKER = "BRL=X"


def _yahoo_ticker(ticker: str, moeda: str) -> str:
    """Converte ticker local para formato Yahoo Finance."""
    suffix = _SUFFIX_MAP.get(moeda, "")
    # Evita duplicar sufixo
    if suffix and not ticker.endswith(suffix):
        return f"{ticker}{suffix}"
    return ticker


def fetch_current_prices(
    tickers: list[str],
    moedas: list[str],
) -> pd.DataFrame:
    """
    Busca preço atual de uma lista de ativos.

    Args:
        tickers: Lista de tickers locais (ex: ["PETR4", "VALE3", "AAPL"]).
        moedas: Lista paralela de moedas (ex: ["BRL", "BRL", "USD"]).

    Returns:
        DataFrame com: ticker, yahoo_ticker, moeda, preco_atual, variacao_dia_pct, data_cotacao.
    """
    if len(tickers) != len(moedas):
        raise ValueError("tickers e moedas devem ter o mesmo tamanho.")

    yahoo_tickers = [
        _yahoo_ticker(t, m) for t, m in zip(tickers, moedas)
    ]

    # Download em batch (mais rápido)
    symbols_str = " ".join(yahoo_tickers)
    logger.info(f"Buscando cotações: {symbols_str}")

    try:
        data = yf.download(
            symbols_str,
            period="2d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        logger.error(f"Erro ao baixar cotações: {e}")
        return _empty_prices_df()

    results = []
    for original, yahoo, moeda in zip(tickers, yahoo_tickers, moedas):
        try:
            if len(yahoo_tickers) == 1:
                closes = data["Close"]
            else:
                closes = data["Close"][yahoo]

            closes = closes.dropna()

            if len(closes) == 0:
                logger.warning(f"Sem dados para {yahoo}")
                results.append(_no_data_row(original, yahoo, moeda))
                continue

            preco_atual = float(closes.iloc[-1])
            preco_anterior = float(closes.iloc[-2]) if len(closes) >= 2 else preco_atual
            variacao = ((preco_atual / preco_anterior) - 1) * 100 if preco_anterior > 0 else 0
            data_cotacao = closes.index[-1]

            results.append({
                "ticker": original,
                "yahoo_ticker": yahoo,
                "moeda": moeda,
                "preco_atual": preco_atual,
                "variacao_dia_pct": round(variacao, 2),
                "data_cotacao": data_cotacao,
            })

        except Exception as e:
            logger.warning(f"Erro processando {yahoo}: {e}")
            results.append(_no_data_row(original, yahoo, moeda))

    return pd.DataFrame(results)


def fetch_usdbrl() -> float:
    """
    Retorna a cotação atual do USD/BRL.

    Returns:
        Float com o valor (ex: 5.15).
    """
    try:
        data = yf.download(
            USDBRL_TICKER,
            period="1d",
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        if data.empty:
            logger.warning("Sem dados para USD/BRL. Usando fallback 5.20.")
            return 5.20

        close = data["Close"].dropna()
        return float(close.iloc[-1])

    except Exception as e:
        logger.error(f"Erro ao buscar USD/BRL: {e}. Usando fallback 5.20.")
        return 5.20


def _empty_prices_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "ticker", "yahoo_ticker", "moeda",
        "preco_atual", "variacao_dia_pct", "data_cotacao",
    ])


def _no_data_row(ticker: str, yahoo_ticker: str, moeda: str) -> dict:
    return {
        "ticker": ticker,
        "yahoo_ticker": yahoo_ticker,
        "moeda": moeda,
        "preco_atual": None,
        "variacao_dia_pct": None,
        "data_cotacao": None,
    }
