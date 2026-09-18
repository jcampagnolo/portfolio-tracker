# 💰 Portfolio Tracker — Agregador de Investimentos Acessível

Agregador de investimentos pessoal desenvolvido com foco em **acessibilidade para baixa visão**.
Consolida ações, FIIs, ETFs, Stocks, BDRs, Criptomoedas e Tesouro em um único lugar,
com cotações em tempo real, valuation automático e relatórios acessíveis para leitores de tela.

---

## 🎯 Objetivo

Substituir planilhas do Google Sheets e exports do Status Invest por uma solução:

- **Acessível** — resumos em texto puro otimizados para leitores de tela (NVDA, JAWS)
- **Automatizada** — cotações via Yahoo Finance + câmbio via API do Banco Central
- **Consolidada** — todos os ativos (BR + EUA + Cripto + Renda Fixa) em um só lugar
- **Inteligente** — valuation por Graham, Bazin e ranking BSD integrados

---

## ⚡ Funcionalidades

| Funcionalidade                   | Status |
|----------------------------------|--------|
| Importação de transações (JSON)  | ✅      |
| Cotação USD/BRL automática (BCB) | ✅      |
| Cálculo de posições e preço médio| ✅      |
| Cotações em tempo real (Yahoo)   | ✅      |
| Busca de fundamentos em paralelo | ✅      |
| Relatório diário acessível       | ✅      |
| Valuation Graham                 | ✅      |
| Valuation Bazin                  | ✅      |
| Ranking BSD (scoring de ações)   | ✅      |
| Suporte multi-moeda (BRL/USD)    | ✅      |
| Conversões de ativos (E/S)       | ✅      |
| Suporte a múltiplas corretoras   | ✅      |

---

## 🗂️ Categorias de Ativos Suportadas

| Categoria    | Moeda | Exemplos            |
|--------------|-------|---------------------|
| Ações        | BRL   | VALE3, WEGE3, ITSA4 |
| FIIs         | BRL   | HGLG11, XPML11      |
| FIAGRO       | BRL   | KNCA11               |
| ETF (BR)     | BRL   | BOVA11, IVVB11       |
| ETF Exterior | USD   | VT, QQQ, SCHD        |
| Stocks       | USD   | AAPL, MSFT, GOOGL    |
| BDR          | BRL   | AAPL34, MSFT34       |
| REITs        | USD   | O, VNQ               |
| Criptomoedas | BRL   | BTC, ETH             |
| Tesouro      | BRL   | Tesouro Selic, IPCA+ |
| CDB/LCA/LCI  | BRL  | Renda fixa bancária  |

---

## 🛠️ Tecnologias

| Tecnologia         | Uso                                  |
|--------------------|--------------------------------------|
| Python 3.12+       | Linguagem principal                  |
| Supabase           | Banco de dados PostgreSQL gerenciado |
| Yahoo Finance      | Cotações e fundamentos em tempo real |
| API BCB (PTAX)     | Cotação oficial USD/BRL              |
| Pandas             | Manipulação de dados                 |
| yfinance           | Wrapper do Yahoo Finance             |
| Jupyter Notebook   | Análises exploratórias de valuation  |
| ThreadPoolExecutor | Paralelização de requisições         |

---

## 🚀 Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/portfolio-tracker.git
cd portfolio-tracker
```

### 2. Criar ambiente virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-anon-key-aqui
```

### 5. Testar conexão

```bash
python -m src.scripts.test_connection
```

---

## 📦 Uso

### Seed de transações (importar dados do Status Invest)

```bash
python -m src.scripts.seed_transactions
```

Importa o arquivo `data/lctos_status_invest.json` para o Supabase:
- Cria wallet, brokers, broker_accounts
- Busca cotações USD/BRL no BCB automaticamente
- Insere assets e transactions
- Vincula pares de conversão (E) ↔ (S)

### Relatório diário

```bash
python -m src.main_cli
```

Gera:
- Cotações atualizadas de todos os ativos
- Variação do dia (R$ e %)
- Lucro/prejuízo total por posição
- Peso de cada ativo no portfólio
- Valuation Graham para ações elegíveis
- **Resumo textual acessível** para leitores de tela

### Testar variáveis de ambiente

```bash
python -m src.scripts.test_env
```

---

## ♿ Acessibilidade

Este projeto foi desenvolvido com foco em **baixa visão**:

- **Resumos em texto puro** — `daily_summary_accessible()` gera relatórios otimizados para leitores de tela (NVDA, JAWS, VoiceOver)
- **Emojis como marcadores** — 📈 alta, 📉 queda, 🟢 barato, 🔴 caro facilitam identificação rápida
- **Formatação pt-BR** — valores em `R$ 1.234,56` e percentuais com `+12,50%`
- **CLI como interface principal** — terminal é naturalmente acessível
- **Sem dependência visual** — nenhum gráfico é obrigatório para operar

---

## 🗄️ Banco de Dados (Supabase)

### Tabelas

| Tabela             | Descrição                                |
|--------------------|------------------------------------------|
| `currencies`       | Moedas (BRL, USD)                        |
| `asset_categories` | Categorias (Ações, FIIs, Stocks...)      |
| `assets`           | Cadastro de ativos (ticker, nome, moeda) |
| `brokers`          | Corretoras                               |
| `wallets`          | Carteiras (por pessoa)                   |
| `broker_accounts`  | Vínculo carteira ↔ corretora             |
| `exchange_rates`   | Cotações USD/BRL históricas (BCB)        |
| `transactions`     | Todas as movimentações                   |

### Views

| View                    | Descrição                             |
|-------------------------|---------------------------------------|
| `portfolio_positions`   | Posição atual + preço médio por ativo |
| `portfolio_by_category` | Posição agrupada por categoria        |

---

## 📊 Valuation

### Graham (Valor Intrínseco)

Fórmula clássica de Benjamin Graham:

**V = √(22,5 × LPA × VPA)**

- **LPA** = Lucro por Ação
- **VPA** = Valor Patrimonial por Ação
- **22,5** = teto de Graham (P/L 15 × P/VP 1,5)

### Bazin (Preço Justo por Dividendos)

**V = DPA / 0,06**

- **DPA** = Dividendo por Ação (últimos 12 meses)
- **6%** = yield mínimo aceitável (critério Bazin)

### Ranking BSD

Score composto (0–100) baseado em:
- Payout ratio, cobertura de juros, fluxo de caixa
- ROE, crescimento de dividendos/lucro/receita
- Price strength, beta

---

## 📁 Estrutura do Projeto

Veja o arquivo [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) para a árvore completa.

---

## 🔮 Roadmap

- [ ] Dashboard web acessível (alto contraste + leitor de tela)
- [ ] Alertas por Telegram/WhatsApp (preço-alvo, dividendos)
- [ ] Cálculo de IR automático (swing trade + day trade)
- [ ] Importação automática de notas de corretagem
- [ ] Backtest de estratégias
- [ ] API REST para consulta de posições

---

## 📝 Licença

Uso pessoal. Projeto privado.
