# 📁 Estrutura do Projeto — portfolio-tracker

```
portfolio-tracker/
│
├── 📁 data/                              # Dados de entrada (não versionado)
│   └── lctos_status_invest.json          # Lançamentos exportados do Status Invest
│
├── 📁 src/                               # Código-fonte principal
│   │
│   ├── config.py                         # Configurações globais (Supabase URL/Key)
│   ├── main_cli.py                       # CLI principal — ponto de entrada
│   │
│   ├── 📁 collectors/                    # Coleta de dados externos
│   │   ├── supabase_client.py            # Cliente Supabase (singleton)
│   │   │   ├── get_client()              #   → conexão reutilizável
│   │   │   ├── load_transactions()       #   → carrega transações do banco
│   │   │   └── load_asset_registry()     #   → carrega cadastro de ativos
│   │   │
│   │   └── yahoo_prices.py              # Cotações e fundamentos (Yahoo Finance)
│   │       ├── fetch_current_prices()    #   → cotações atuais (paralelo)
│   │       ├── fetch_fundamentals()      #   → P/L, ROE, DY, etc. (paralelo)
│   │       └── fetch_dollar_rate()       #   → cotação USD/BRL em tempo real
│   │
│   ├── 📁 portfolio/                     # Lógica de carteira
│   │   ├── positions.py                  # Cálculo de posições
│   │   │   ├── calculate_positions()     #   → saldo, preço médio, ciclos
│   │   │   ├── get_open_positions()      #   → posições em aberto
│   │   │   └── get_closed_positions()    #   → posições encerradas
│   │   │
│   │   └── daily.py                      # Acompanhamento diário
│   │       ├── build_daily_report()      #   → relatório completo com cotações
│   │       └── daily_summary_accessible()#   → resumo textual para leitores de tela
│   │
│   ├── 📁 ranking/                       # Ranking e scoring de ativos
│   │   └── (bsd_ranking — scoring 0-100) #   → baseado em payout, ROE, crescimento
│   │
│   ├── 📁 scripts/                       # Scripts utilitários e seeds
│   │   ├── seed_transactions.py          # Seed completo: JSON → Supabase
│   │   │   ├── parse_preco()             #   → converte "1.234,56" → 1234.56
│   │   │   ├── parse_total()             #   → converte "R$ 1.234,56" → 1234.56
│   │   │   ├── parse_quantidade()        #   → converte quantidade string → float
│   │   │   ├── parse_date()              #   → converte "dd/mm/yyyy" → "yyyy-mm-dd"
│   │   │   ├── fetch_exchange_rate_bcb() #   → cotação USD/BRL do dia (API BCB)
│   │   │   ├── fetch_all_exchange_rates()#   → todas as cotações necessárias
│   │   │   └── seed()                    #   → execução principal do seed
│   │   │
│   │   ├── migrate_sheets_to_supabase.py # Migração de planilhas Google → Supabase
│   │   ├── test_connection.py            # Teste de conexão com Supabase
│   │   └── test_env.py                   # Teste de variáveis de ambiente
│   │
│   ├── 📁 utils/                         # Funções utilitárias
│   │   ├── formatters.py                 # Formatação pt-BR
│   │   │   ├── format_brl()             #   → R$ 1.234,56
│   │   │   ├── format_pct()             #   → +12,50%
│   │   │   └── format_number()          #   → 1.234.567
│   │   │
│   │   └── parsers.py                    # Parsing de valores
│   │       ├── parse_brl_number()        #   → "R$ 1.234,56" → 1234.56
│   │       ├── parse_brl_date()          #   → "01/04/2026" → Timestamp
│   │       └── clean_transactions_df()   #   → limpa e padroniza DataFrame
│   │
│   └── 📁 valuation/                     # Análise de valuation
│       └── valuation_acoes.ipynb         # Notebook: Graham, Bazin, DCF
│
├── .env                                  # Variáveis de ambiente (NÃO versionar)
├── .gitignore                            # Arquivos ignorados pelo Git
├── requirements.txt                      # Dependências Python
├── PROJECT_STRUCTURE.md                  # Este arquivo
└── README.md                             # Documentação principal
```

---

## 🗄️ Banco de Dados — Supabase (PostgreSQL)

```
📦 Tabelas de Referência (dados estáticos)
├── currencies                    # BRL, USD
│   ├── id (PK)
│   ├── code                      # "BRL", "USD"
│   ├── name                      # "Real Brasileiro", "Dólar Americano"
│   └── symbol                    # "R$", "$"
│
└── asset_categories              # Categorias de ativos
    ├── id (PK)
    ├── name                      # "Ações", "FIIs", "ETF Exterior"...
    ├── description
    ├── is_variable_income        # true/false
    └── default_currency_id (FK)  # → currencies

📦 Tabelas de Cadastro
├── assets                        # Cadastro de ativos
│   ├── id (PK)
│   ├── ticker                    # "VALE3", "VT", "BTC"
│   ├── name
│   ├── category_id (FK)          # → asset_categories
│   └── currency_id (FK)          # → currencies
│
├── brokers                       # Corretoras
│   ├── id (PK)
│   └── name                      # "Inter", "Avenue", "Binance"
│
├── wallets                       # Carteiras (por pessoa)
│   ├── id (PK)
│   ├── name                      # "Alisson"
│   ├── owner_name
│   └── owner_cpf
│
└── broker_accounts               # Vínculo carteira ↔ corretora
    ├── id (PK)
    ├── wallet_id (FK)            # → wallets
    └── broker_id (FK)            # → brokers

📦 Tabelas de Movimentação
├── exchange_rates                # Cotações históricas USD/BRL
│   ├── id (PK)
│   ├── from_currency_id (FK)     # → currencies (USD)
│   ├── to_currency_id (FK)       # → currencies (BRL)
│   ├── rate_date                 # "2025-03-15"
│   ├── rate                      # 5.7832
│   └── source                    # "BCB"
│
└── transactions                  # Todas as movimentações
    ├── id (PK)
    ├── wallet_id (FK)            # → wallets
    ├── asset_id (FK)             # → assets
    ├── broker_id (FK)            # → brokers
    ├── transaction_type          # compra, venda, bonificacao, desdobramento,
    │                             # conversao_entrada, conversao_saida
    ├── trade_date                # Data da operação
    ├── quantity                  # Quantidade
    ├── unit_price                # Preço unitário
    ├── total_amount              # Valor total na moeda do ativo
    ├── currency_id (FK)          # → currencies
    ├── exchange_rate_to_brl      # Câmbio do dia (se USD)
    ├── total_amount_brl          # Valor total convertido em BRL
    ├── conversion_pair_id (FK)   # → transactions (vincula E↔S)
    └── source                    # "status_invest"

📦 Views (calculadas)
├── portfolio_positions           # Posição atual + preço médio por ativo
└── portfolio_by_category         # Posição agrupada por categoria
```

---

## 🔄 Fluxo de Dados

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Status Invest  │────▶│  JSON local  │────▶│   Supabase   │
│  (export manual)│     │  (data/)     │     │  (PostgreSQL)│
└─────────────────┘     └──────────────┘     └──────┬───────┘
                                                     │
        ┌────────────────────────────────────────────┤
        │                                            │
        ▼                                            ▼
┌──────────────┐                           ┌─────────────────┐
│  API BCB     │                           │  Yahoo Finance  │
│  (USD/BRL)   │                           │  (cotações +    │
│              │                           │   fundamentos)  │
└──────┬───────┘                           └────────┬────────┘
       │                                            │
       └──────────────┐    ┌────────────────────────┘
                      │    │
                      ▼    ▼
              ┌──────────────────┐
              │   main_cli.py    │
              │                  │
              │  • Posições      │
              │  • Preço médio   │
              │  • Variação dia  │
              │  • Valuation     │
              │  • Ranking BSD   │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  Resumo Acessível│
              │  (texto puro)    │
              │                  │
              │  📊 Investido    │
              │  📈 Altas do dia │
              │  📉 Quedas       │
              │  🟢 Baratos      │
              │  🔴 Caros        │
              └──────────────────┘
```

---

## 📊 Módulos — Resumo de Responsabilidades

| Módulo                               | Responsabilidade                              |
|--------------------------------------|-----------------------------------------------|
| `config.py`                          | Carrega `.env`, expõe `settings`              |
| `collectors/supabase_client.py`      | Conexão e queries ao Supabase                 |
| `collectors/yahoo_prices.py`         | Cotações e fundamentos (paralelo)             |
| `portfolio/positions.py`             | Saldo, preço médio, posições abertas/fechadas |
| `portfolio/daily.py`                 | Relatório diário + resumo acessível           |
| `ranking/`                           | Scoring BSD (payout, ROE, crescimento)        |
| `valuation/`                         | Graham, Bazin, análise de ações               |
| `utils/formatters.py`               | `R$ 1.234,56`, `+12,50%`                     |
| `utils/parsers.py`                   | Parsing de valores BR, limpeza de DataFrames  |
| `scripts/seed_transactions.py`       | Importa JSON → Supabase com câmbio BCB        |
| `scripts/migrate_sheets_to_supabase.py` | Migração de planilhas Google → Supabase    |
| `scripts/test_connection.py`         | Valida conexão com Supabase                   |
| `scripts/test_env.py`               | Valida variáveis de ambiente                  |
| `main_cli.py`                        | Orquestra tudo e gera relatório final         |
