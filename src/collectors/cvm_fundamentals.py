"""
src/collectors/cvm_fundamentals.py
Coleta demonstrações financeiras (DFP e ITR) do Portal de Dados Abertos da CVM.

Fonte: https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp
       https://dados.cvm.gov.br/dataset/cia_aberta-doc-itr
       https://dados.cvm.gov.br/dataset/cia_aberta-doc-fca
       https://dados.cvm.gov.br/dataset/cia_aberta-doc-vlmo

Os CSVs são públicos, gratuitos e não exigem autenticação.
"""

import io
import zipfile
from datetime import datetime

import pandas as pd
import requests

# ── URLs base da CVM ──
BASE_DFP = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/"
BASE_ITR = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/"
BASE_FCA = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FCA/DADOS/"
BASE_VLMO = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/VLMO/DADOS/"
BASE_CAD = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/"

# ── Mapeamento ticker → CNPJ raiz (primeiros 8 dígitos) ──
TICKER_CNPJ_MAP = {
    "PETR4": "33000167",
    "PETR3": "33000167",
    "VALE3": "33592510",
    "ITUB4": "60872504",
    "ITUB3": "60872504",
    "BBDC4": "60746948",
    "BBDC3": "60746948",
    "BBAS3": "00000000",
    "ABEV3": "07526557",
    "WEGE3": "84429695",
    "RENT3": "16670085",
    "SUZB3": "16404287",
    "GGBR4": "33611500",
    "GGBR3": "33611500",
    "CSNA3": "33042730",
    "CPLE6": "76483817",
    "CPLE3": "76483817",
    "BBSE3": "01522368",
    "EGIE3": "02328280",
    "TAEE11": "07859971",
    "VIVT3": "02558157",
    "RADL3": "61585865",
    "LREN3": "92754738",
    "MGLU3": "47960950",
    "PRIO3": "10629105",
    "CMIN3": "42323688",
    "KLBN11": "89637490",
    "SBSP3": "43776517",
    "TOTS3": "53113791",
    "FLRY3": "60840055",
    "EMBR3": "07689002",
}

# Cache para evitar downloads repetidos na mesma sessão
_cache_shares: dict[str, int] = {}
_cache_fca: pd.DataFrame | None = None


def _download_cvm_zip(url: str) -> dict[str, pd.DataFrame]:
    """
    Baixa um ZIP da CVM e retorna dict com nome_arquivo → DataFrame.
    """
    print(f"⬇️  Baixando: {url.split('/')[-1]}...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    dfs = {}
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in zf.namelist():
            if name.endswith(".csv"):
                with zf.open(name) as f:
                    df = pd.read_csv(
                        f,
                        sep=";",
                        encoding="latin-1",
                        dtype=str,
                    )
                    dfs[name] = df

    return dfs


def _filter_by_cnpj(df: pd.DataFrame, cnpj_raiz: str) -> pd.DataFrame:
    """Filtra DataFrame CVM pelo CNPJ raiz (8 primeiros dígitos)."""
    if "CNPJ_CIA" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["_cnpj_clean"] = df["CNPJ_CIA"].str.replace(r"[.\-/]", "", regex=True)
    filtered = df[df["_cnpj_clean"].str[:8] == cnpj_raiz].copy()
    filtered.drop(columns=["_cnpj_clean"], inplace=True)
    return filtered


def _filter_consolidated(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra apenas demonstrações CONSOLIDADAS e com a ÚLTIMA versão.
    """
    if "GRUPO_DFP" in df.columns:
        df = df[df["GRUPO_DFP"].str.contains("Consolidado", case=False, na=False)]

    if "VERSAO" in df.columns:
        df["VERSAO"] = pd.to_numeric(df["VERSAO"], errors="coerce")
        idx = df.groupby(["DT_REFER"])["VERSAO"].idxmax()
        df = df.loc[idx]

    return df


# ══════════════════════════════════════════════════════════════
# NÚMERO DE AÇÕES — via FCA / VLMO da CVM
# ══════════════════════════════════════════════════════════════

def fetch_shares_outstanding(
    ticker: str,
    year: int | None = None,
) -> int | None:
    """
    Busca o número total de ações de uma empresa direto da CVM.

    Tenta na ordem:
        1. FCA (fca_cia_aberta_valor_mobiliario) — campo Quantidade
        2. VLMO (vlmo_cia_aberta) — Valores Mobiliários Negociados

    Parâmetros:
        ticker: código da ação (ex: PETR4)
        year: ano do formulário (padrão: ano atual, depois anterior)

    Retorna:
        int com o número total de ações, ou None se não encontrar.
    """
    global _cache_fca

    ticker_upper = ticker.upper()

    # Verifica cache
    cache_key = f"{ticker_upper}_{year or 'latest'}"
    if cache_key in _cache_shares:
        return _cache_shares[cache_key]

    cnpj = TICKER_CNPJ_MAP.get(ticker_upper)
    if not cnpj:
        print(f"❌ CNPJ não encontrado para {ticker_upper}.")
        return None

    if year is None:
        years_try = [datetime.now().year, datetime.now().year - 1]
    else:
        years_try = [year]

    # ── Tentativa 1: FCA — valor_mobiliario ──
    for yr in years_try:
        try:
            url = f"{BASE_FCA}fca_cia_aberta_{yr}.zip"
            dfs = _download_cvm_zip(url)

            for name, df in dfs.items():
                if "valor_mobiliario" in name.lower():
                    filtered = _filter_by_cnpj(df, cnpj)

                    if filtered.empty:
                        continue

                    # Filtra por ações (ON, PN, UNIT)
                    col_especie = None
                    for c in ["Especie", "Descricao_Tipo_Valor_Mobiliario",
                              "Tipo_Valor_Mobiliario", "DS_ESPECIE"]:
                        if c in filtered.columns:
                            col_especie = c
                            break

                    col_qtd = None
                    for c in ["Quantidade", "Qtde_Valores_Mobiliarios",
                              "QT_VALOR_MOBILIARIO", "Quantidade_Total"]:
                        if c in filtered.columns:
                            col_qtd = c
                            break

                    if col_qtd is None:
                        print(f"⚠️  Coluna de quantidade não encontrada. "
                              f"Colunas: {list(filtered.columns)}")
                        continue

                    # Converte quantidade
                    filtered[col_qtd] = pd.to_numeric(
                        filtered[col_qtd].str.replace(",", "."),
                        errors="coerce"
                    )

                    # Soma todas as espécies de ações (ON + PN)
                    if col_especie:
                        acoes = filtered[
                            filtered[col_especie].str.contains(
                                r"(?:Ordin|Preferen|ON|PN|Unit|A[çc][õo]es)",
                                case=False, na=False
                            )
                        ]
                    else:
                        acoes = filtered

                    total = int(acoes[col_qtd].sum())

                    if total > 0:
                        _cache_shares[cache_key] = total
                        print(
                            f"✅ Ações {ticker_upper} (FCA {yr}): "
                            f"{total:,.0f} ({total / 1_000_000:,.0f} mi)"
                        )
                        return total

        except requests.exceptions.HTTPError:
            continue
        except Exception as e:
            print(f"⚠️  Erro FCA {yr}: {e}")
            continue

    # ── Tentativa 2: VLMO — Valores Mobiliários ──
    for yr in years_try:
        try:
            url = f"{BASE_VLMO}vlmo_cia_aberta_{yr}.zip"
            dfs = _download_cvm_zip(url)

            for name, df in dfs.items():
                filtered = _filter_by_cnpj(df, cnpj)

                if filtered.empty:
                    continue

                # Procura coluna de quantidade
                col_qtd = None
                for c in ["Quantidade", "Qtde_Valores_Mobiliarios",
                           "Qtde_Total", "QT_VALOR_MOBILIARIO"]:
                    if c in filtered.columns:
                        col_qtd = c
                        break

                if col_qtd is None:
                    continue

                filtered[col_qtd] = pd.to_numeric(
                    filtered[col_qtd].str.replace(",", "."),
                    errors="coerce"
                )

                total = int(filtered[col_qtd].sum())

                if total > 0:
                    _cache_shares[cache_key] = total
                    print(
                        f"✅ Ações {ticker_upper} (VLMO {yr}): "
                        f"{total:,.0f} ({total / 1_000_000:,.0f} mi)"
                    )
                    return total

        except requests.exceptions.HTTPError:
            continue
        except Exception as e:
            print(f"⚠️  Erro VLMO {yr}: {e}")
            continue

    print(f"⚠️  Não foi possível obter nº de ações de {ticker_upper} via CVM")
    return None


# ══════════════════════════════════════════════════════════════
# DRE / BALANÇO (funções existentes)
# ══════════════════════════════════════════════════════════════

def fetch_dre(ticker: str, years: list[int] | None = None) -> pd.DataFrame:
    """
    Busca a DRE (Demonstração do Resultado do Exercício) de um ticker.
    Usa DFP (anual) — dados do 4º trimestre / exercício completo.

    Parâmetros:
        ticker: código da ação (ex: PETR4)
        years: lista de anos (ex: [2021, 2022, 2023, 2024, 2025])
               Se None, busca últimos 5 anos.

    Retorna:
        DataFrame com colunas: DT_REFER, DS_CONTA, CD_CONTA, VL_CONTA
    """
    cnpj = TICKER_CNPJ_MAP.get(ticker.upper())
    if not cnpj:
        print(f"❌ CNPJ não encontrado para {ticker}. Adicione em TICKER_CNPJ_MAP.")
        return pd.DataFrame()

    if years is None:
        current_year = datetime.now().year
        years = list(range(current_year - 4, current_year + 1))

    frames = []

    for year in years:
        url = f"{BASE_DFP}dfp_cia_aberta_DRE_con_{year}.zip"
        try:
            dfs = _download_cvm_zip(url)
            for name, df in dfs.items():
                if "DRE" in name.upper():
                    filtered = _filter_by_cnpj(df, cnpj)
                    filtered = _filter_consolidated(filtered)
                    if not filtered.empty:
                        filtered["ANO"] = year
                        frames.append(filtered)
        except requests.exceptions.HTTPError:
            print(f"⚠️  DFP {year} não disponível (ainda não publicado?)")
        except Exception as e:
            print(f"⚠️  Erro ao baixar DFP {year}: {e}")

    if not frames:
        print(f"⚠️  Nenhuma DRE encontrada para {ticker}")
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    result["VL_CONTA"] = pd.to_numeric(result["VL_CONTA"], errors="coerce")
    result["DT_REFER"] = pd.to_datetime(result["DT_REFER"])

    print(f"✅ DRE {ticker}: {len(result)} linhas, {result['DT_REFER'].dt.year.nunique()} anos")
    return result


def fetch_bpa_bpp(ticker: str, years: list[int] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Busca BPA (Balanço Patrimonial Ativo) e BPP (Passivo) de um ticker.

    Retorna:
        (df_bpa, df_bpp) — DataFrames com as contas patrimoniais
    """
    cnpj = TICKER_CNPJ_MAP.get(ticker.upper())
    if not cnpj:
        print(f"❌ CNPJ não encontrado para {ticker}.")
        return pd.DataFrame(), pd.DataFrame()

    if years is None:
        current_year = datetime.now().year
        years = list(range(current_year - 4, current_year + 1))

    frames_bpa = []
    frames_bpp = []

    for year in years:
        for doc_type, prefix, frames in [
            ("BPA", "BPA", frames_bpa),
            ("BPP", "BPP", frames_bpp),
        ]:
            url = f"{BASE_DFP}dfp_cia_aberta_{prefix}_con_{year}.zip"
            try:
                dfs = _download_cvm_zip(url)
                for name, df in dfs.items():
                    if prefix in name.upper():
                        filtered = _filter_by_cnpj(df, cnpj)
                        filtered = _filter_consolidated(filtered)
                        if not filtered.empty:
                            filtered["ANO"] = year
                            frames.append(filtered)
            except requests.exceptions.HTTPError:
                pass
            except Exception as e:
                print(f"⚠️  Erro {doc_type} {year}: {e}")

    bpa = pd.concat(frames_bpa, ignore_index=True) if frames_bpa else pd.DataFrame()
    bpp = pd.concat(frames_bpp, ignore_index=True) if frames_bpp else pd.DataFrame()

    for df in [bpa, bpp]:
        if not df.empty:
            df["VL_CONTA"] = pd.to_numeric(df["VL_CONTA"], errors="coerce")
            df["DT_REFER"] = pd.to_datetime(df["DT_REFER"])

    print(f"✅ Balanço {ticker}: BPA={len(bpa)} linhas, BPP={len(bpp)} linhas")
    return bpa, bpp


def extract_indicators(ticker: str, years: list[int] | None = None) -> pd.DataFrame:
    """
    Extrai indicadores-chave dos balanços CVM para valuation:
    - Lucro Líquido
    - Patrimônio Líquido
    - Receita Líquida
    - EBIT

    Retorna:
        DataFrame com colunas: ano, lucro_liquido, patrimonio_liquido,
                               receita_liquida, ebit
    """
    dre = fetch_dre(ticker, years)
    bpa, bpp = fetch_bpa_bpp(ticker, years)

    if dre.empty:
        return pd.DataFrame()

    CONTAS_DRE = {
        "3.11": "lucro_liquido",
        "3.01": "receita_liquida",
        "3.05": "ebit",
    }

    CONTAS_BPP = {
        "2.03": "patrimonio_liquido",
    }

    records = []

    for ano in sorted(dre["DT_REFER"].dt.year.unique()):
        row = {"ano": ano}

        dre_ano = dre[dre["DT_REFER"].dt.year == ano]
        for cd_conta, field_name in CONTAS_DRE.items():
            match = dre_ano[dre_ano["CD_CONTA"] == cd_conta]
            if not match.empty:
                row[field_name] = match["VL_CONTA"].iloc[0]

        if not bpp.empty:
            bpp_ano = bpp[bpp["DT_REFER"].dt.year == ano]
            for cd_conta, field_name in CONTAS_BPP.items():
                match = bpp_ano[bpp_ano["CD_CONTA"] == cd_conta]
                if not match.empty:
                    row[field_name] = match["VL_CONTA"].iloc[0]

        records.append(row)

    df = pd.DataFrame(records)

    if df.empty:
        print(f"⚠️  Nenhum indicador extraído para {ticker}")
        return df

    for col in ["lucro_liquido", "patrimonio_liquido", "receita_liquida", "ebit"]:
        if col in df.columns:
            df[f"{col}_mi"] = (df[col] / 1_000_000).round(2)

    print(f"✅ Indicadores {ticker}: {len(df)} anos extraídos")
    return df


# ══════════════════════════════════════════════════════════════
# LPA / VPA — 100% dados CVM (sem dicionário hardcoded)
# ══════════════════════════════════════════════════════════════

def calcular_lpa_vpa(
    ticker: str,
    years: list[int] | None = None,
    shares_override: int | None = None,
) -> pd.DataFrame:
    """
    Calcula LPA (Lucro por Ação) e VPA (Valor Patrimonial por Ação)
    usando APENAS dados da CVM (demonstrações + nº de ações via FCA/VLMO).

    Fórmulas:
        LPA = Lucro Líquido / Número de Ações
        VPA = Patrimônio Líquido / Número de Ações
        ROE = Lucro Líquido / Patrimônio Líquido × 100

    Parâmetros:
        ticker: código da ação (ex: PETR4)
        years: lista de anos (padrão: últimos 5)
        shares_override: nº de ações total (sobrescreve busca CVM)

    Retorna:
        DataFrame com colunas:
            ano, lucro_liquido, patrimonio_liquido, shares,
            lpa, vpa, roe_pct
    """
    ticker_upper = ticker.upper()

    # 1. Buscar número de ações — agora direto da CVM
    if shares_override:
        shares = shares_override
        print(f"📌 Usando nº de ações informado: {shares:,.0f}")
    else:
        shares = fetch_shares_outstanding(ticker_upper)

    if shares is None or shares == 0:
        print(
            f"❌ Impossível calcular LPA/VPA sem nº de ações para {ticker_upper}.\n"
            f"   Dica: passe shares_override=<total_acoes> manualmente."
        )
        return pd.DataFrame()

    # 2. Buscar indicadores da CVM (DRE + Balanço)
    df = extract_indicators(ticker_upper, years)

    if df.empty:
        return pd.DataFrame()

    # 3. Verificar colunas necessárias
    has_ll = "lucro_liquido" in df.columns
    has_pl = "patrimonio_liquido" in df.columns

    if not has_ll and not has_pl:
        print(f"⚠️  Sem Lucro Líquido nem PL para {ticker_upper}")
        return pd.DataFrame()

    # 4. Calcular LPA e VPA
    df["shares"] = shares

    if has_ll:
        df["lpa"] = (df["lucro_liquido"] / shares).round(2)
    else:
        df["lpa"] = None
        print(f"⚠️  Lucro Líquido ausente — LPA não calculado")

    if has_pl:
        df["vpa"] = (df["patrimonio_liquido"] / shares).round(2)
    else:
        df["vpa"] = None
        print(f"⚠️  Patrimônio Líquido ausente — VPA não calculado")

    # 5. ROE
    if has_ll and has_pl:
        df["roe_pct"] = (
            (df["lucro_liquido"] / df["patrimonio_liquido"]) * 100
        ).round(2)
    else:
        df["roe_pct"] = None

    # 6. Resumo acessível
    ultimo = df.iloc[-1]
    shares_mi = shares / 1_000_000
    print(f"\n📊 LPA / VPA — {ticker_upper}")
    print(f"   Ações: {shares:,.0f} ({shares_mi:,.0f} milhões) — fonte: CVM")
    print(f"   Último ano ({int(ultimo['ano'])}):")
    if ultimo.get("lpa") is not None:
        print(f"   LPA: R$ {ultimo['lpa']:.2f}")
    if ultimo.get("vpa") is not None:
        print(f"   VPA: R$ {ultimo['vpa']:.2f}")
    if ultimo.get("roe_pct") is not None:
        print(f"   ROE: {ultimo['roe_pct']:.1f}%")

    return df
