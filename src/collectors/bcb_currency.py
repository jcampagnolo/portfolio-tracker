"""
src/collectors/bcb_currency.py
Cotação do dólar (PTAX) e indicadores econômicos direto do Banco Central do Brasil.

Fontes:
    - API OData PTAX: https://olinda.bcb.gov.br/olinda/servico/PTAX/
    - API SGS (séries temporais): https://api.bcb.gov.br/dados/serie/

Ambas são públicas, gratuitas e não exigem autenticação.
"""

from datetime import datetime, timedelta

import pandas as pd
import requests

# ── Endpoints do Banco Central ──
PTAX_ODATA = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
)

# SGS: série 1 = dólar comercial (venda), série 10813 = dólar PTAX venda
SGS_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados"

# Séries úteis do SGS
SERIES_SGS = {
    "dolar_ptax_venda": 1,
    "dolar_ptax_compra": 10813,
    "selic_meta": 432,
    "selic_diaria": 11,
    "ipca_mensal": 433,
    "ipca_acumulado_12m": 13522,
    "cdi_diario": 12,
}


def fetch_dolar_ptax(data: str | None = None) -> dict | None:
    """
    Busca cotação do dólar PTAX de uma data específica (API OData do BCB).

    Se a data for feriado/fim de semana, tenta os últimos 5 dias úteis.

    Parâmetros:
        data: data no formato 'dd-MM-yyyy' ou 'yyyy-MM-dd'.
              Se None, busca a mais recente.

    Retorna:
        dict com: data, compra, venda, hora
    """
    if data is None:
        # Tenta hoje e os últimos 5 dias úteis
        datas_tentativa = [
            (datetime.now() - timedelta(days=i)).strftime("%m-%d-%Y")
            for i in range(6)
        ]
    else:
        # Converte formato se necessário
        try:
            dt = pd.to_datetime(data)
            datas_tentativa = [dt.strftime("%m-%d-%Y")]
        except Exception:
            datas_tentativa = [data]

    for dt_str in datas_tentativa:
        url = (
            f"{PTAX_ODATA}"
            f"CotacaoDolarDia(dataCotacao=@dataCotacao)"
            f"?@dataCotacao='{dt_str}'"
            f"&$top=1&$orderby=dataHoraCotacao%20desc"
            f"&$format=json"
        )

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            dados = resp.json()

            if dados.get("value"):
                item = dados["value"][0]
                resultado = {
                    "data": dt_str,
                    "compra": round(float(item["cotacaoCompra"]), 4),
                    "venda": round(float(item["cotacaoVenda"]), 4),
                    "hora": item.get("dataHoraCotacao", ""),
                }
                print(
                    f"✅ Dólar PTAX ({dt_str}): "
                    f"compra R$ {resultado['compra']:.4f} | "
                    f"venda R$ {resultado['venda']:.4f}"
                )
                return resultado
        except Exception:
            continue

    print("⚠️  Não foi possível obter a cotação PTAX do dólar")
    return None


def fetch_dolar_periodo(
    data_inicio: str,
    data_fim: str | None = None,
) -> pd.DataFrame:
    """
    Busca cotações do dólar PTAX em um período (API OData do BCB).

    Parâmetros:
        data_inicio: formato 'MM-dd-yyyy' ou 'yyyy-MM-dd'
        data_fim: formato 'MM-dd-yyyy' ou 'yyyy-MM-dd' (padrão: hoje)

    Retorna:
        DataFrame com colunas: data, compra, venda
    """
    dt_ini = pd.to_datetime(data_inicio).strftime("%m-%d-%Y")

    if data_fim is None:
        dt_fim = datetime.now().strftime("%m-%d-%Y")
    else:
        dt_fim = pd.to_datetime(data_fim).strftime("%m-%d-%Y")

    url = (
        f"{PTAX_ODATA}"
        f"CotacaoDolarPeriodo(dataInicial=@di,dataFinalCotacao=@df)"
        f"?@di='{dt_ini}'"
        f"&@df='{dt_fim}'"
        f"&$orderby=dataHoraCotacao%20asc"
        f"&$format=json"
    )

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dados = resp.json()

        if not dados.get("value"):
            print(f"⚠️  Sem cotações no período {dt_ini} a {dt_fim}")
            return pd.DataFrame()

        records = []
        for item in dados["value"]:
            records.append({
                "data": item["dataHoraCotacao"][:10],
                "compra": float(item["cotacaoCompra"]),
                "venda": float(item["cotacaoVenda"]),
            })

        df = pd.DataFrame(records)
        df["data"] = pd.to_datetime(df["data"])

        # Remove duplicatas (pode ter mais de uma cotação por dia)
        df = df.sort_values("data").drop_duplicates(subset="data", keep="last")

        print(f"✅ Dólar PTAX: {len(df)} cotações de {dt_ini} a {dt_fim}")
        return df

    except Exception as e:
        print(f"⚠️  Erro ao buscar período: {e}")
        return pd.DataFrame()


def fetch_sgs(
    serie: str | int,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> pd.DataFrame:
    """
    Busca qualquer série do SGS do Banco Central.

    Séries úteis:
        1      → Dólar comercial (venda)
        432    → Selic Meta (% a.a.)
        11     → Selic diária
        433    → IPCA mensal (variação %)
        13522  → IPCA acumulado 12 meses (% a.a.)
        12     → CDI diário

    Parâmetros:
        serie: código numérico ou nome (ex: 'selic_meta' ou 432)
        data_inicio: formato 'dd/MM/yyyy' (padrão: últimos 30 dias)
        data_fim: formato 'dd/MM/yyyy' (padrão: hoje)

    Retorna:
        DataFrame com colunas: data, valor
    """
    # Resolve nome para código
    if isinstance(serie, str):
        codigo = SERIES_SGS.get(serie)
        if codigo is None:
            print(f"⚠️  Série '{serie}' não encontrada. "
                  f"Use um código numérico ou: {list(SERIES_SGS.keys())}")
            return pd.DataFrame()
    else:
        codigo = serie

    url = SGS_BASE.format(codigo)

    params = {"formato": "json"}
    if data_inicio:
        params["dataInicial"] = data_inicio
    if data_fim:
        params["dataFinal"] = data_fim

    # Se não informou datas, busca últimos 30 dias
    if not data_inicio and not data_fim:
        dt_fim = datetime.now()
        dt_ini = dt_fim - timedelta(days=30)
        params["dataInicial"] = dt_ini.strftime("%d/%m/%Y")
        params["dataFinal"] = dt_fim.strftime("%d/%m/%Y")

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        dados = resp.json()

        if not dados:
            print(f"⚠️  Sem dados para série {codigo}")
            return pd.DataFrame()

        df = pd.DataFrame(dados)
        df.rename(columns={"data": "data", "valor": "valor"}, inplace=True)
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

        print(f"✅ SGS série {codigo}: {len(df)} registros")
        return df

    except Exception as e:
        print(f"⚠️  Erro SGS série {codigo}: {e}")
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════
# SELIC
# ══════════════════════════════════════════════════════════════

def fetch_selic_atual() -> float | None:
    """
    Retorna a taxa Selic Meta atual (% a.a.) via SGS do BCB.
    """
    df = fetch_sgs("selic_meta")

    if df.empty:
        print("⚠️  Não foi possível obter a Selic")
        return None

    selic = df.iloc[-1]["valor"]
    print(f"✅ Selic Meta atual: {selic}% a.a.")
    return selic


def fetch_selic_historica(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    anos: int | None = None,
) -> pd.DataFrame:
    """
    Retorna a série histórica da Selic Meta (% a.a.).

    Parâmetros:
        data_inicio: formato 'dd/MM/yyyy'
        data_fim: formato 'dd/MM/yyyy'
        anos: atalho — busca os últimos N anos (ignora data_inicio/data_fim)

    Retorna:
        DataFrame com colunas: data, valor (Selic % a.a.)

    Exemplo:
        >>> df = fetch_selic_historica(anos=10)
        >>> df.tail()
    """
    if anos is not None:
        dt_fim = datetime.now()
        dt_ini = dt_fim - timedelta(days=anos * 365)
        data_inicio = dt_ini.strftime("%d/%m/%Y")
        data_fim = dt_fim.strftime("%d/%m/%Y")

    df = fetch_sgs("selic_meta", data_inicio=data_inicio, data_fim=data_fim)

    if df.empty:
        print("⚠️  Sem dados de Selic histórica")
        return pd.DataFrame()

    df = df.sort_values("data").reset_index(drop=True)
    print(
        f"✅ Selic histórica: {len(df)} registros | "
        f"{df['data'].min().strftime('%d/%m/%Y')} a "
        f"{df['data'].max().strftime('%d/%m/%Y')} | "
        f"Atual: {df['valor'].iloc[-1]}% a.a."
    )
    return df


# ══════════════════════════════════════════════════════════════
# IPCA
# ══════════════════════════════════════════════════════════════

def fetch_ipca_atual() -> dict | None:
    """
    Retorna o IPCA mais recente: variação mensal e acumulado 12 meses.

    Retorna:
        dict com:
            - mes_referencia: data do último dado
            - ipca_mensal: variação % do mês
            - ipca_acumulado_12m: variação % acumulada em 12 meses
    """
    df_mensal = fetch_sgs("ipca_mensal")
    df_acum = fetch_sgs("ipca_acumulado_12m")

    if df_mensal.empty and df_acum.empty:
        print("⚠️  Não foi possível obter o IPCA")
        return None

    resultado = {}

    if not df_mensal.empty:
        ultimo_mensal = df_mensal.sort_values("data").iloc[-1]
        resultado["mes_referencia"] = ultimo_mensal["data"].strftime("%m/%Y")
        resultado["ipca_mensal"] = round(float(ultimo_mensal["valor"]), 2)

    if not df_acum.empty:
        ultimo_acum = df_acum.sort_values("data").iloc[-1]
        resultado["ipca_acumulado_12m"] = round(float(ultimo_acum["valor"]), 2)
        # Se não pegou a data do mensal, usa a do acumulado
        if "mes_referencia" not in resultado:
            resultado["mes_referencia"] = ultimo_acum["data"].strftime("%m/%Y")

    print(
        f"✅ IPCA ({resultado.get('mes_referencia', '?')}): "
        f"mensal {resultado.get('ipca_mensal', '?')}% | "
        f"12 meses {resultado.get('ipca_acumulado_12m', '?')}%"
    )
    return resultado


def fetch_ipca_historico(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    anos: int | None = None,
    acumulado: bool = False,
) -> pd.DataFrame:
    """
    Retorna a série histórica do IPCA.

    Parâmetros:
        data_inicio: formato 'dd/MM/yyyy'
        data_fim: formato 'dd/MM/yyyy'
        anos: atalho — busca os últimos N anos
        acumulado: se True, retorna o IPCA acumulado 12 meses (série 13522).
                   se False, retorna a variação mensal (série 433).

    Retorna:
        DataFrame com colunas: data, valor

    Exemplos:
        >>> df_mensal = fetch_ipca_historico(anos=5)
        >>> df_acum = fetch_ipca_historico(anos=5, acumulado=True)
    """
    if anos is not None:
        dt_fim = datetime.now()
        dt_ini = dt_fim - timedelta(days=anos * 365)
        data_inicio = dt_ini.strftime("%d/%m/%Y")
        data_fim = dt_fim.strftime("%d/%m/%Y")

    serie = "ipca_acumulado_12m" if acumulado else "ipca_mensal"
    label = "IPCA acumulado 12m" if acumulado else "IPCA mensal"

    df = fetch_sgs(serie, data_inicio=data_inicio, data_fim=data_fim)

    if df.empty:
        print(f"⚠️  Sem dados de {label}")
        return pd.DataFrame()

    df = df.sort_values("data").reset_index(drop=True)
    print(
        f"✅ {label}: {len(df)} meses | "
        f"{df['data'].min().strftime('%m/%Y')} a "
        f"{df['data'].max().strftime('%m/%Y')} | "
        f"Último: {df['valor'].iloc[-1]}%"
    )
    return df


# ══════════════════════════════════════════════════════════════
# DÓLAR
# ══════════════════════════════════════════════════════════════

def fetch_dollar_rate() -> float | None:
    """
    Retorna a cotação de venda do dólar PTAX mais recente.
    Substitui a versão anterior que usava Yahoo Finance.
    """
    resultado = fetch_dolar_ptax()

    if resultado:
        return resultado["venda"]

    return None


# ══════════════════════════════════════════════════════════════
# RESUMO MACRO — todos os indicadores de uma vez
# ══════════════════════════════════════════════════════════════

def fetch_resumo_macro() -> dict:
    """
    Retorna um resumo com os principais indicadores macro do BCB.

    Retorna:
        dict com:
            - dolar_ptax_venda: float
            - dolar_ptax_compra: float
            - selic_meta: float (% a.a.)
            - ipca_mensal: float (% do mês)
            - ipca_acumulado_12m: float (% a.a.)

    Exemplo:
        >>> macro = fetch_resumo_macro()
        >>> print(f"Selic: {macro['selic_meta']}%")
        >>> print(f"Dólar: R$ {macro['dolar_ptax_venda']}")
    """
    print("🏦 Buscando indicadores macro do Banco Central...\n")

    resumo = {}

    # Dólar
    dolar = fetch_dolar_ptax()
    if dolar:
        resumo["dolar_ptax_compra"] = dolar["compra"]
        resumo["dolar_ptax_venda"] = dolar["venda"]
        resumo["dolar_data"] = dolar["data"]

    # Selic
    selic = fetch_selic_atual()
    if selic is not None:
        resumo["selic_meta"] = selic

    # IPCA
    ipca = fetch_ipca_atual()
    if ipca:
        resumo["ipca_mensal"] = ipca.get("ipca_mensal")
        resumo["ipca_acumulado_12m"] = ipca.get("ipca_acumulado_12m")
        resumo["ipca_referencia"] = ipca.get("mes_referencia")

    # Resumo formatado
    print("\n" + "=" * 50)
    print("📊 RESUMO MACRO — Banco Central do Brasil")
    print("=" * 50)
    print(f"  💵 Dólar PTAX:  R$ {resumo.get('dolar_ptax_venda', '?')}")
    print(f"  📈 Selic Meta:  {resumo.get('selic_meta', '?')}% a.a.")
    print(f"  📉 IPCA mensal: {resumo.get('ipca_mensal', '?')}%")
    print(f"  📉 IPCA 12m:    {resumo.get('ipca_acumulado_12m', '?')}% a.a.")
    print("=" * 50)

    return resumo
