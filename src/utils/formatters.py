# src/utils/formatters.py

"""Formatação de valores em pt-BR com acessibilidade."""


def format_brl(value: float) -> str:
    """R$ 1.234,56 ou -R$ 1.234,56"""
    if value >= 0:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_pct(value: float, decimals: int = 2) -> str:
    """12,50% com sinal"""
    formatted = f"{value:+,.{decimals}f}%".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def format_number(value: float, decimals: int = 0) -> str:
    """1.234.567"""
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
