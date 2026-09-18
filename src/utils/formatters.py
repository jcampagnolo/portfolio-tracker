"""
src/utils/formatters.py
Formatação de valores para exibição pt-BR.
"""


def format_brl(value: float) -> str:
    """R$ 1.234,56"""
    if value >= 0:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_usd(value: float) -> str:
    """US$ 1,234.56"""
    if value >= 0:
        return f"US$ {value:,.2f}"
    return f"-US$ {abs(value):,.2f}"


def format_pct(value: float, with_sign: bool = True) -> str:
    """+12,50% ou -3,20%"""
    formatted = f"{abs(value):,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
    if with_sign:
        sign = "+" if value >= 0 else "-"
        return f"{sign}{formatted}"
    return formatted


def format_number(value: float) -> str:
    """1.234.567"""
    return f"{value:,.0f}".replace(",", ".")


def format_qtde(value: float) -> str:
    """Inteiro se possível, senão 4 casas."""
    if value == int(value):
        return f"{int(value)}"
    return f"{value:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")


def text_bar(pct: float, width: int = 50) -> str:
    """Barra visual em texto: █░░░░"""
    filled = int(pct / 100 * width)
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)
